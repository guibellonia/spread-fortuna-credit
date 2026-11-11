// Edge Function `bureau`: consulta o bureau ao vivo para um pedido, a pedido do painel de revisão.
//
// - O token do bureau fica só aqui, como segredo da função (supabase secrets set BUREAU_TOKEN=...).
// - Só membro logado do painel consegue: o id_cliente sai de painel.decisoes lido COM o token do usuário,
//   então o RLS decide quem vê o quê.
// - Retry em 503, timeout e erro de rede (até 5 tentativas, espera crescente com jitter); 401 para na hora.
// - A resposta de um cliente não muda: fica guardada em painel.bureau_consultas e as próximas vêm do cache.
import { createClient } from "npm:@supabase/supabase-js@2.118.0";

const BUREAU_URL = (Deno.env.get("BUREAU_URL") ?? "https://gowlab-fortuna-bureau.azurewebsites.net").replace(/\/+$/, "");
const BUREAU_TOKEN = Deno.env.get("BUREAU_TOKEN") ?? "";
const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const ORIGENS = (Deno.env.get("ORIGENS_PERMITIDAS") ?? "https://guibellonia.github.io,http://localhost:3000")
  .split(",").map((s) => s.trim()).filter(Boolean);

const CAMPOS = ["score", "restricoes_ativas", "parcelas_outras_instituicoes", "consultas_90_dias", "meses_historico_bureau"];
const TIMEOUT_MS = 10_000;
const TENTATIVAS = 5;
const ESPERA_MS = 500;

class ErroHttp extends Error {
  constructor(readonly status: number, mensagem: string) {
    super(mensagem);
  }
}

function cabecalhos(origem: string | null): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": origem && ORIGENS.includes(origem) ? origem : ORIGENS[0],
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Vary": "Origin",
  };
}

function resposta(corpo: unknown, status: number, origem: string | null): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { ...cabecalhos(origem), "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

async function consultarBureau(idCliente: string) {
  const inicio = Date.now();
  let ultimo = "";
  for (let n = 0; n < TENTATIVAS; n++) {
    try {
      const r = await fetch(`${BUREAU_URL}/v1/bureau/${encodeURIComponent(idCliente)}`, {
        headers: { Authorization: `Bearer ${BUREAU_TOKEN}` },
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      if (r.status === 200) {
        const d = await r.json();
        if (d?.id_cliente !== idCliente || CAMPOS.some((c) => typeof d?.[c] !== "number")) {
          throw new ErroHttp(502, "resposta inesperada do bureau");
        }
        const dados = Object.fromEntries(["id_cliente", ...CAMPOS].map((c) => [c, d[c]]));
        return { dados, tentativas: n + 1, ms: Date.now() - inicio };
      }
      await r.body?.cancel();
      if (r.status === 401) throw new ErroHttp(502, "token do bureau inválido ou ausente na função");
      if (r.status !== 503) throw new ErroHttp(502, `bureau respondeu ${r.status}`);
      ultimo = "503";
    } catch (e) {
      if (e instanceof ErroHttp) throw e;
      ultimo = e instanceof DOMException && e.name === "TimeoutError" ? "timeout" : "erro de rede";
    }
    if (n < TENTATIVAS - 1) {
      await new Promise((ok) => setTimeout(ok, ESPERA_MS * 2 ** n * (0.75 + Math.random() * 0.5)));
    }
  }
  throw new ErroHttp(503, `bureau sem resposta após ${TENTATIVAS} tentativas (${ultimo})`);
}

Deno.serve(async (req) => {
  const origem = req.headers.get("Origin");
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cabecalhos(origem) });
  if (req.method !== "POST") return resposta({ erro: "use POST" }, 405, origem);
  if (!BUREAU_TOKEN || !SUPABASE_URL || !ANON_KEY || !SERVICE_KEY) {
    return resposta({ erro: "função sem configuração (BUREAU_TOKEN e chaves do Supabase)" }, 500, origem);
  }
  const auth = req.headers.get("Authorization") ?? "";
  if (!auth.startsWith("Bearer ")) return resposta({ erro: "faça login" }, 401, origem);

  let idPedido: unknown;
  try {
    ({ id_pedido: idPedido } = await req.json());
  } catch {
    return resposta({ erro: "corpo JSON inválido" }, 400, origem);
  }
  if (typeof idPedido !== "string" || !/^P-\d{5}$/.test(idPedido)) {
    return resposta({ erro: "id_pedido no formato P-00000" }, 400, origem);
  }

  // lido com o token de quem chamou: o RLS só entrega a linha para membro do painel
  const usuario = createClient(SUPABASE_URL, ANON_KEY, {
    global: { headers: { Authorization: auth } },
    db: { schema: "painel" },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  // a chave anon também é um JWT válido: exige um usuário de verdade por trás do token
  const { data: quem } = await usuario.auth.getUser(auth.slice("Bearer ".length));
  if (!quem?.user) return resposta({ erro: "faça login" }, 401, origem);
  const { data: dec, error } = await usuario.from("decisoes").select("id_cliente").eq("id_pedido", idPedido).maybeSingle();
  if (error?.code === "42501") return resposta({ erro: "sem acesso ao painel" }, 403, origem);
  if (error) return resposta({ erro: "não consegui ler o pedido" }, 500, origem);
  if (!dec) return resposta({ erro: "pedido não encontrado ou sem acesso" }, 404, origem);

  const servico = createClient(SUPABASE_URL, SERVICE_KEY, {
    db: { schema: "painel" },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: cache } = await servico.from("bureau_consultas")
    .select("dados, tentativas, ms, consultado_em").eq("id_cliente", dec.id_cliente).maybeSingle();
  if (cache) return resposta({ id_pedido: idPedido, ...cache, fonte: "cache" }, 200, origem);

  try {
    const r = await consultarBureau(dec.id_cliente);
    const consultado_em = new Date().toISOString();
    await servico.from("bureau_consultas").upsert({ id_cliente: dec.id_cliente, ...r, consultado_em });
    return resposta({ id_pedido: idPedido, ...r, consultado_em, fonte: "api" }, 200, origem);
  } catch (e) {
    const erro = e instanceof ErroHttp ? e : new ErroHttp(500, "erro inesperado");
    return resposta({ erro: erro.message }, erro.status, origem);
  }
});
