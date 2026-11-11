"use client";

import type { Session } from "@supabase/supabase-js";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { int, moeda, pct, quando } from "@/lib/format";
import type { Entrada, Motor } from "@/lib/motor";
import { supabase, supabaseConfigurado, type Bureau, type Decisao, type Revisao as Rev } from "@/lib/supabase";
import { PorQue } from "./PorQue";
import { TopBar } from "./TopBar";
import { IconCheck } from "./ui";

type Filtro = "pendentes" | "divergentes" | "laranja" | "revisadas" | "todas";
const FILTROS: [Filtro, string][] = [
  ["pendentes", "Sem revisão"],
  ["divergentes", "Diferente da atual"],
  ["laranja", "Faixa laranja"],
  ["revisadas", "Revisadas"],
  ["todas", "Todas"],
];
const FAIXA_TEXTO: Record<string, string> = {
  verde: "Verde", amarela: "Amarela", laranja: "Laranja", barreira: "Barreira",
};
const ACOES: [Rev["acao"], string][] = [["confirmar", "Confirmar IA"], ["aprovar", "Aprovar com valor"], ["negar", "Negar"]];
const ACAO_TEXTO: Record<Rev["acao"], string> = { confirmar: "confirmou a IA", aprovar: "aprovou", negar: "negou" };
const BUREAU_CAMPOS: [string, string, (v: number) => string][] = [
  ["score", "Score", (v) => int(v)],
  ["restricoes_ativas", "Restrições ativas", (v) => int(v)],
  ["consultas_90_dias", "Consultas em 90 dias", (v) => int(v)],
  ["parcelas_outras_instituicoes", "Parcelas em outras instituições", (v) => moeda(v)],
  ["meses_historico_bureau", "Meses de histórico", (v) => int(v)],
];
const POR_PAGINA = 50;
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function Revisao() {
  if (!supabaseConfigurado) {
    return (
      <Pagina>
        <section className="card estreito">
          <h2 className="card-title">Revisão ainda não conectada</h2>
          <p className="muted">
            A revisão usa o banco no Supabase. Depois de criar o projeto, preencha <code>supabaseUrl</code> e{" "}
            <code>supabaseAnonKey</code> em <code>site/site.config.json</code>. Passo a passo em <code>supabase/README.md</code>.
          </p>
        </section>
      </Pagina>
    );
  }
  return <Conectado />;
}

function Pagina({ fim, extra, children }: { fim?: ReactNode; extra?: ReactNode; children: ReactNode }) {
  return (
    <>
      <TopBar ativo="revisao" fim={fim} />
      <main className="page">
        <div className="page-head">
          <h1 className="display">Revisão</h1>
          {extra}
        </div>
        {children}
      </main>
    </>
  );
}

function Conectado() {
  const sb = supabase()!;
  const [sessao, setSessao] = useState<Session | null>(null);
  const [pronto, setPronto] = useState(false);
  const [resumo, setResumo] = useState<string | null>(null);

  useEffect(() => {
    sb.auth.getSession().then(({ data }) => {
      setSessao(data.session);
      setPronto(true);
    });
    const { data } = sb.auth.onAuthStateChange((_evento, s) => setSessao(s));
    return () => data.subscription.unsubscribe();
  }, [sb]);

  const fim = sessao ? (
    <span className="usuario">
      {sessao.user.email}
      <button type="button" className="link-btn" onClick={() => sb.auth.signOut()}>Sair</button>
    </span>
  ) : null;

  return (
    <Pagina fim={fim} extra={resumo && <span className="chip">{resumo}</span>}>
      {!pronto ? <p className="muted">Carregando…</p> : sessao ? <Area onResumo={setResumo} /> : <Login />}
    </Pagina>
  );
}

export function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function entrar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    const { error } = await supabase()!.auth.signInWithPassword({ email: email.trim(), password: senha });
    setEnviando(false);
    if (error) setErro("E-mail ou senha inválidos.");
  }

  return (
    <section className="card estreito">
      <h2 className="card-title">Entrar</h2>
      <p className="muted">Só para membros do time. A IA sugere, o analista decide e cada revisão fica registrada.</p>
      <form className="form" onSubmit={entrar}>
        <label className="field">
          <span>E-mail</span>
          <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          <span>Senha</span>
          <input type="password" autoComplete="current-password" required value={senha} onChange={(e) => setSenha(e.target.value)} />
        </label>
        {erro && <p className="erro" role="alert">{erro}</p>}
        <button type="submit" className="btn sl" disabled={enviando}>{enviando ? "Entrando…" : "Entrar"}</button>
      </form>
    </section>
  );
}

function Area({ onResumo }: { onResumo: (s: string) => void }) {
  const sb = supabase()!;
  const [membro, setMembro] = useState<boolean | null>(null);
  const [filtro, setFiltro] = useState<Filtro>("pendentes");
  const [busca, setBusca] = useState("");
  const [lista, setLista] = useState<Decisao[] | null>(null);
  const [total, setTotal] = useState(0);
  const [sel, setSel] = useState<string | null>(null);
  const [historico, setHistorico] = useState<Rev[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [versao, setVersao] = useState(0);
  const [motor, setMotor] = useState<Motor | null>(null);
  const termo = busca.toUpperCase().replace(/[^A-Z0-9-]/g, "");

  useEffect(() => {
    sb.rpc("eh_membro").then(({ data, error }) => setMembro(!error && data === true));
  }, [sb]);

  useEffect(() => {
    if (!membro) return;
    sb.from("modelo").select("conteudo").eq("id", "proposta").maybeSingle()
      .then(({ data }) => setMotor(data ? (data.conteudo as Motor) : null));
  }, [sb, membro]);

  useEffect(() => {
    if (!membro) return;
    let q = sb.from("decisoes_revisadas").select("*", { count: "exact" }).order("id_pedido").limit(POR_PAGINA);
    if (filtro === "pendentes") q = q.is("revisao_acao", null);
    if (filtro === "revisadas") q = q.not("revisao_acao", "is", null);
    if (filtro === "divergentes") q = q.eq("diverge_atual", true);
    if (filtro === "laranja") q = q.eq("faixa", "laranja");
    if (termo) q = q.ilike("id_pedido", `%${termo}%`);
    q.then(({ data, count, error }) => {
      if (error) return setErro("Não consegui carregar a fila.");
      setErro(null);
      setLista((data ?? []) as Decisao[]);
      setTotal(count ?? 0);
    });
  }, [sb, membro, filtro, termo, versao]);

  useEffect(() => {
    if (!membro) return;
    Promise.all([
      sb.from("decisoes").select("id_pedido", { count: "exact", head: true }),
      sb.from("decisoes_revisadas").select("id_pedido", { count: "exact", head: true }).not("revisao_acao", "is", null),
      sb.from("revisoes").select("*").order("criado_em", { ascending: false }).limit(15),
    ]).then(([todas, revisadas, hist]) => {
      if (todas.count) onResumo(`${int(revisadas.count ?? 0)} de ${int(todas.count)} revisados`);
      setHistorico((hist.data ?? []) as Rev[]);
    });
  }, [sb, membro, versao, onResumo]);

  if (membro === null) return <p className="muted">Carregando…</p>;
  if (!membro) {
    return (
      <section className="card estreito">
        <h2 className="card-title">Sem acesso ao painel</h2>
        <p className="muted">
          Seu e-mail ainda não está na lista de membros. Peça a quem administra o Supabase para rodar{" "}
          <code>supabase/aplicar_migracoes.py --membro &lt;seu e-mail&gt;</code>.
        </p>
      </section>
    );
  }

  return (
    <div className="rev-grid">
      <section className="card" aria-label="Fila de pedidos">
        <header className="card-head">
          <h2 className="card-title">Fila</h2>
          <span className="muted card-actions">{int(total)} pedidos</span>
        </header>
        <div className="chips" role="group" aria-label="Filtro">
          {FILTROS.map(([id, nome]) => (
            <button key={id} type="button" className="chip-btn sl" aria-pressed={filtro === id} onClick={() => setFiltro(id)}>
              {filtro === id && <IconCheck />}
              {nome}
            </button>
          ))}
        </div>
        <label className="field">
          <span>Buscar pedido</span>
          <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="número do pedido" inputMode="text" />
        </label>
        {erro && <p className="erro" role="alert">{erro}</p>}
        {lista && lista.length === 0 && <p className="muted">Nenhum pedido neste filtro.</p>}
        <ul className="fila">
          {(lista ?? []).map((d) => (
            <li key={d.id_pedido}>
              <button type="button" className={`fila-item sl${sel === d.id_pedido ? " is-sel" : ""}`} onClick={() => setSel(d.id_pedido)}>
                <span className="fila-id">{d.id_pedido}</span>
                <span className="fila-motivo">{d.motivo ?? moeda(d.valor_solicitado)}</span>
                <Selo d={d} />
              </button>
            </li>
          ))}
        </ul>
        {total > POR_PAGINA && <p className="foot">Mostrando {POR_PAGINA} de {int(total)}. Use a busca para achar um pedido.</p>}
      </section>

      {sel ? (
        <Detalhe key={sel} id={sel} motor={motor} onSalvo={() => setVersao((v) => v + 1)} />
      ) : (
        <section className="card vazio">
          <p className="muted">Escolha um pedido na fila para ver a decisão da IA, consultar o bureau e registrar a revisão.</p>
        </section>
      )}

      <ArquivoEntrega />

      <section className="card rev-hist" aria-label="Revisões recentes">
        <header className="card-head"><h2 className="card-title">Revisões recentes</h2></header>
        {historico.length === 0 ? (
          <p className="muted">Nenhuma revisão ainda.</p>
        ) : (
          <div className="table-wrap">
            <table className="dtable">
              <thead><tr><th>Quando</th><th>Pedido</th><th>Ação</th><th>IA</th><th>Analista</th><th>Justificativa</th></tr></thead>
              <tbody>
                {historico.map((r) => (
                  <tr key={r.id}>
                    <th scope="row">{quando(r.criado_em)}</th>
                    <td>{r.id_pedido}</td>
                    <td>{ACAO_TEXTO[r.acao]}{r.valor != null ? ` ${moeda(r.valor)}` : ""}</td>
                    <td>{r.decisao_ia === "APROVADO" ? moeda(r.valor_ia) : "negado"}</td>
                    <td>{r.analista_email}</td>
                    <td className="just">{r.justificativa}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Selo({ d }: { d: Decisao }) {
  const aprovado = d.decisao_final === "APROVADO";
  return (
    <span className={`selo ${aprovado ? "is-ok" : "is-no"}`}>
      {aprovado ? moeda(d.valor_final) : "Negado"}
      {d.revisao_acao ? " · revisado" : ""}
    </span>
  );
}

function Detalhe({ id, motor, onSalvo }: { id: string; motor: Motor | null; onSalvo: () => void }) {
  const sb = supabase()!;
  const [d, setD] = useState<Decisao | null>(null);
  const [entrada, setEntrada] = useState<Entrada | null>(null);
  const [recarga, setRecarga] = useState(0);
  const [bureau, setBureau] = useState<Bureau | null>(null);
  const [bErro, setBErro] = useState<string | null>(null);
  const [bAndando, setBAndando] = useState(false);
  const [acao, setAcao] = useState<Rev["acao"]>("confirmar");
  const [valor, setValor] = useState("");
  const [just, setJust] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; texto: string } | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    sb.from("decisoes_revisadas").select("*").eq("id_pedido", id).maybeSingle()
      .then(({ data }) => setD(data as Decisao | null));
  }, [sb, id, recarga]);

  useEffect(() => {
    sb.from("decisoes").select("entrada").eq("id_pedido", id).maybeSingle()
      .then(({ data }) => setEntrada((data?.entrada as Entrada | null) ?? null));
  }, [sb, id]);

  async function consultarBureau() {
    setBAndando(true);
    setBErro(null);
    const { data, error } = await sb.functions.invoke("bureau", { body: { id_pedido: id } });
    setBAndando(false);
    if (!error) return setBureau(data as Bureau);
    let texto = "Não consegui consultar o bureau.";
    try {
      const corpo = await (error as { context?: Response }).context?.json();
      if (corpo?.erro) texto = corpo.erro;
    } catch {
      /* resposta sem corpo JSON */
    }
    setBErro(texto);
  }

  async function salvar(e: FormEvent) {
    e.preventDefault();
    const linha: Record<string, unknown> = { id_pedido: id, acao, justificativa: just.trim() };
    if (acao === "aprovar") linha.valor = Number(valor.replace(/\./g, "").replace(",", "."));
    setSalvando(true);
    const { error } = await sb.from("revisoes").insert(linha);
    setSalvando(false);
    if (error) {
      const texto = error.code === "P0001" ? error.message
        : error.code === "23514" ? "Confira a justificativa (5+ caracteres) e o valor."
        : "Não consegui registrar a revisão.";
      return setMsg({ ok: false, texto });
    }
    setMsg({ ok: true, texto: "Revisão registrada." });
    setJust("");
    setValor("");
    setRecarga((r) => r + 1);
    onSalvo();
  }

  if (!d) return <section className="card"><p className="muted">Carregando {id}…</p></section>;
  const teto = Math.min(d.valor_solicitado, 30000);

  return (
    <section className="card detalhe" aria-label={`Pedido ${id}`}>
      <header className="card-head">
        <h2 className="card-title">{id}</h2>
        <div className="card-actions"><Selo d={d} /></div>
      </header>

      <div className="det-grid">
        <Info rotulo={`Decisão da IA${d.politica ? ` (${d.politica})` : ""}`} valor={dec(d.decisao, d.valor_aprovado)} />
        <Info rotulo="Política atual" valor={dec(d.atual_decisao, d.atual_valor)} />
        <Info rotulo="Regras do time" valor={dec(d.regras_decisao, d.regras_valor)} />
        <Info rotulo="Solicitado" valor={`${moeda(d.valor_solicitado)} · ${d.prazo_meses}x`} />
        <Info rotulo="Chance de não pagar" valor={d.p_nao_paga != null ? pct(d.p_nao_paga) : "—"} />
        <Info rotulo="Ganho esperado" valor={d.ganho_esperado != null ? moeda(d.ganho_esperado) : "—"} />
      </div>
      {d.motivo && <p className="det-motivo">{d.motivo}</p>}
      {d.faixa && (
        <p className="det-faixa">
          <span className={`faixa is-${d.faixa}`}>Faixa {FAIXA_TEXTO[d.faixa]}{d.faixa !== "barreira" ? ` · ${d.pontos} ponto(s)` : ""}</span>
          <span className="muted">{d.pontos_detalhe}</span>
        </p>
      )}
      {motor && entrada && (
        <div className="bureau-box">
          <div className="linha">
            <h3>Por que a IA decidiu assim</h3>
            <a className="btn-tonal sl link-sim" href={`${BASE}/simulador/#${encodeURIComponent(id)}`}>Simular variações</a>
          </div>
          <PorQue motor={motor} entrada={entrada} publicada={{ aprova: d.decisao === "APROVADO", valor: Number(d.valor_aprovado) }} />
        </div>
      )}
      {d.revisao_acao && (
        <p className="muted">
          Última revisão: {d.revisao_por} {ACAO_TEXTO[d.revisao_acao]}
          {d.revisao_valor != null ? ` ${moeda(d.revisao_valor)}` : ""} em {quando(d.revisao_em!)}: “{d.revisao_justificativa}”
        </p>
      )}

      <div className="bureau-box">
        <div className="linha">
          <h3>Bureau ao vivo</h3>
          <button type="button" className="btn-tonal sl" onClick={consultarBureau} disabled={bAndando}>
            {bAndando ? "Consultando…" : "Consultar"}
          </button>
        </div>
        {bErro && <p className="erro" role="alert">{bErro}</p>}
        {bureau && (
          <>
            <dl className="stats stats-5">
              {BUREAU_CAMPOS.map(([campo, rotulo, fmt]) => (
                <div key={campo}><dt>{rotulo}</dt><dd>{fmt(Number(bureau.dados[campo]))}</dd></div>
              ))}
            </dl>
            <p className="foot">
              {bureau.fonte === "cache" ? "Do cache" : "Direto da API"} · {bureau.tentativas} tentativa(s) · {int(bureau.ms)} ms
              · {quando(bureau.consultado_em)}
            </p>
          </>
        )}
      </div>

      <form className="form" onSubmit={salvar}>
        <div className="seg" role="group" aria-label="Ação do analista">
          {ACOES.map(([id_, nome]) => (
            <button key={id_} type="button" className="seg-btn sl" aria-pressed={acao === id_} onClick={() => setAcao(id_)}>
              {acao === id_ && <IconCheck />}
              {nome}
            </button>
          ))}
        </div>
        {acao === "aprovar" && (
          <label className="field">
            <span>Valor aprovado (até {moeda(teto)})</span>
            <input inputMode="decimal" required value={valor} onChange={(e) => setValor(e.target.value)} placeholder="8000,00" />
          </label>
        )}
        <label className="field">
          <span>Justificativa</span>
          <textarea required minLength={5} rows={3} value={just} onChange={(e) => setJust(e.target.value)} />
        </label>
        {msg && <p className={msg.ok ? "ok" : "erro"} role="status">{msg.texto}</p>}
        <button type="submit" className="btn sl" disabled={salvando}>{salvando ? "Registrando…" : "Registrar revisão"}</button>
      </form>
    </section>
  );
}

function dec(decisao: string | null, valor: number | null) {
  if (!decisao) return "—";
  return decisao === "APROVADO" ? moeda(valor ?? 0) : "Negado";
}

/** CSV no formato do manual (5.2): cabeçalho exato, UTF-8 sem BOM, vírgula, ponto decimal com 2 casas, LF. */
function ArquivoEntrega() {
  const sb = supabase()!;
  const [msg, setMsg] = useState<{ ok: boolean; texto: string } | null>(null);
  const [andando, setAndando] = useState(false);

  async function baixar(comRevisoes: boolean) {
    setAndando(true);
    setMsg(null);
    const linhas: Decisao[] = [];
    for (let de = 0; ; de += 1000) {
      const { data, error } = await sb.from("decisoes_revisadas").select("*").order("id_pedido").range(de, de + 999);
      if (error) {
        setAndando(false);
        return setMsg({ ok: false, texto: "Não consegui ler as decisões." });
      }
      linhas.push(...((data ?? []) as Decisao[]));
      if (!data || data.length < 1000) break;
    }
    setAndando(false);
    const ids = new Set(linhas.map((l) => l.id_pedido));
    if (linhas.length !== 2000 || ids.size !== 2000) {
      return setMsg({ ok: false, texto: `Esperava 2.000 pedidos únicos e vieram ${linhas.length}. Nada foi baixado.` });
    }
    const corpo = linhas.map((l) => {
      const decisao = comRevisoes ? l.decisao_final : l.decisao;
      const valor = decisao === "APROVADO" ? Number(comRevisoes ? l.valor_final : l.valor_aprovado) : 0;
      return `${l.id_pedido},${decisao},${valor.toFixed(2)}`;
    });
    const csv = ["id_pedido,decisao,valor_aprovado", ...corpo].join("\n") + "\n";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = comRevisoes ? "spread_final_com_revisoes.csv" : "spread_final.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    const aprovados = linhas.filter((l) => (comRevisoes ? l.decisao_final : l.decisao) === "APROVADO").length;
    setMsg({ ok: true, texto: `${a.download}: 2.000 pedidos, ${int(aprovados)} aprovados.` });
  }

  return (
    <section className="card rev-arquivo" aria-label="Arquivo de entrega">
      <header className="card-head"><h2 className="card-title">Arquivo de entrega</h2></header>
      <p className="muted">
        CSV no formato do manual, com as decisões publicadas: iguais ao <code>saida/spread_final.csv</code> que o pipeline gera.
        Valide no Teams (checkpoint 14h15) e entregue como <code>spread_final.csv</code> até 15h30.
      </p>
      <div className="linha-botoes">
        <button type="button" className="btn sl" onClick={() => baixar(false)} disabled={andando}>
          {andando ? "Gerando…" : "Baixar CSV da IA"}
        </button>
        <button type="button" className="btn-tonal sl" onClick={() => baixar(true)} disabled={andando}>
          Com as revisões do analista
        </button>
      </div>
      <p className="foot">
        A versão com revisões troca a decisão da IA pela do analista onde houve revisão. Antes de entregar assim,
        confirme com a organização: arquivo que a solução não gerou desclassifica.
      </p>
      {msg && <p className={msg.ok ? "ok" : "erro"} role="status">{msg.texto}</p>}
    </section>
  );
}

function Info({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div>
      <span className="muted">{rotulo}</span>
      <span className="det-v">{valor}</span>
    </div>
  );
}
