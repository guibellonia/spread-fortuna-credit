"use client";

import type { Session } from "@supabase/supabase-js";
import { useEffect, useMemo, useState, type ChangeEvent, type ReactNode } from "react";
import { int, moeda, pct } from "@/lib/format";
import { decidir, type Entrada, type Motor } from "@/lib/motor";
import { supabase, supabaseConfigurado } from "@/lib/supabase";
import { PorQue } from "./PorQue";
import { Login } from "./Revisao";
import { TopBar } from "./TopBar";

type Chave = keyof Entrada;
type Campo = { k: Chave; rotulo: string; opcional?: boolean };

const GRUPOS: [string, Campo[]][] = [
  ["Pedido", [
    { k: "valor_solicitado", rotulo: "Valor solicitado (R$)" },
    { k: "prazo_meses", rotulo: "Prazo (meses)" },
  ]],
  ["Cliente", [
    { k: "renda_declarada", rotulo: "Renda declarada (R$/mês)" },
    { k: "tipo_vinculo", rotulo: "Vínculo" },
    { k: "idade", rotulo: "Idade (anos)", opcional: true },
    { k: "meses_conta", rotulo: "Meses de conta" },
  ]],
  ["Bureau", [
    { k: "score", rotulo: "Score" },
    { k: "restricoes_ativas", rotulo: "Restrições ativas" },
    { k: "consultas_90_dias", rotulo: "Consultas em 90 dias" },
    { k: "meses_historico_bureau", rotulo: "Meses de histórico" },
    { k: "parcelas_outras_instituicoes", rotulo: "Parcelas em outras instituições (R$/mês)", opcional: true },
  ]],
  ["Conta, média dos 12 meses antes do pedido", [
    { k: "mov_entradas_media", rotulo: "Entradas (R$/mês)", opcional: true },
    { k: "mov_salario_media", rotulo: "Salário (R$/mês)", opcional: true },
    { k: "mov_saidas_media", rotulo: "Saídas (R$/mês)", opcional: true },
    { k: "mov_saldo_medio", rotulo: "Saldo médio (R$)", opcional: true },
    { k: "mov_saldo_minimo_min", rotulo: "Menor saldo (R$)", opcional: true },
    { k: "mov_dias_cheque_total", rotulo: "Dias no cheque especial", opcional: true },
    { k: "mov_meses_cheque", rotulo: "Meses com saldo negativo", opcional: true },
    { k: "mov_entradas_cv", rotulo: "Variação das entradas (0,09 = 9%)", opcional: true },
    { k: "mov_meses_saida_maior_3m", rotulo: "Meses com saídas > entradas (dos 3 últimos)", opcional: true },
  ]],
];
const CAMPOS = GRUPOS.flatMap(([, c]) => c);
const PRAZOS = [6, 12, 18, 24, 36];
const VINCULOS: [string, string][] = [
  ["assalariado", "Assalariado"], ["autonomo", "Autônomo"], ["aposentado", "Aposentado"], ["empresario", "Empresário"],
];
const PERFIS: [string, (t: Entrada) => Partial<Entrada>][] = [
  ["Cliente típico", () => ({})],
  ["Com restrição", () => ({ restricoes_ativas: 1 })],
  ["Conta apertada", () => ({ mov_meses_saida_maior_3m: 2 })],
  ["Renda real baixa", (t) => ({ mov_entradas_media: Math.round(t.renda_declarada * 0.25),
    mov_salario_media: Math.round(t.renda_declarada * 0.2), mov_saidas_media: Math.round(t.renda_declarada * 0.2) })],
  ["Pedido alto", () => ({ valor_solicitado: 25000, prazo_meses: 36 })],
  ["Score baixo", () => ({ score: 480 })],
];

type Form = Record<Chave, string>;
const texto = (e: Entrada): Form =>
  Object.fromEntries(CAMPOS.map(({ k }) => [k, e[k] == null ? "" : String(e[k]).replace(".", ",")])) as Form;

function numero(s: string): number | null {
  const t = s.trim().replace(/\s/g, "");
  if (!t) return null;
  const n = Number(t.includes(",") ? t.replace(/\./g, "").replace(",", ".") : t);
  return Number.isFinite(n) ? n : NaN;
}

/** Converte o formulário (ou uma linha de CSV) em entrada do motor; devolve os campos inválidos. */
function paraEntrada(f: Record<string, string | undefined>): { e: Entrada | null; faltam: string[] } {
  const e: Record<string, unknown> = {};
  const faltam: string[] = [];
  for (const { k, rotulo, opcional } of CAMPOS) {
    if (k === "tipo_vinculo") {
      const v = (f[k] ?? "").trim().toLowerCase();
      if (!VINCULOS.some(([id]) => id === v)) faltam.push(rotulo);
      e[k] = v;
      continue;
    }
    const v = numero(f[k] ?? "");
    if (v === null ? !opcional : Number.isNaN(v)) faltam.push(rotulo);
    e[k] = v;
  }
  if (!faltam.length && ((e.renda_declarada as number) <= 0 || (e.valor_solicitado as number) <= 0)) {
    faltam.push("renda e valor maiores que zero");
  }
  return { e: faltam.length ? null : (e as Entrada), faltam };
}

export function Simulador() {
  if (!supabaseConfigurado) {
    return <Pagina><section className="card estreito"><p className="muted">O simulador usa o Supabase, que ainda não está configurado.</p></section></Pagina>;
  }
  return <Conectado />;
}

function Pagina({ fim, children }: { fim?: ReactNode; children: ReactNode }) {
  return (
    <>
      <TopBar ativo="simulador" fim={fim} />
      <main className="page">
        <div className="page-head"><h1 className="display">Simulador</h1></div>
        {children}
      </main>
    </>
  );
}

function Conectado() {
  const sb = supabase()!;
  const [sessao, setSessao] = useState<Session | null>(null);
  const [pronto, setPronto] = useState(false);
  const [motor, setMotor] = useState<Motor | null | "sem-acesso" | "sem-modelo">(null);

  useEffect(() => {
    sb.auth.getSession().then(({ data }) => {
      setSessao(data.session);
      setPronto(true);
    });
    const { data } = sb.auth.onAuthStateChange((_evento, s) => setSessao(s));
    return () => data.subscription.unsubscribe();
  }, [sb]);

  useEffect(() => {
    if (!sessao) return;
    (async () => {
      const { data: membro } = await sb.rpc("eh_membro");
      if (membro !== true) return setMotor("sem-acesso");
      const { data } = await sb.from("modelo").select("conteudo").eq("id", "proposta").maybeSingle();
      setMotor(data ? (data.conteudo as Motor) : "sem-modelo");
    })();
  }, [sb, sessao]);

  const fim = sessao ? (
    <span className="usuario">
      {sessao.user.email}
      <button type="button" className="link-btn" onClick={() => sb.auth.signOut()}>Sair</button>
    </span>
  ) : null;

  let corpo: ReactNode = <p className="muted">Carregando…</p>;
  if (pronto && !sessao) corpo = <Login />;
  else if (motor === "sem-acesso") corpo = <Aviso titulo="Sem acesso">Seu e-mail ainda não está na lista de membros do painel.</Aviso>;
  else if (motor === "sem-modelo") {
    corpo = <Aviso titulo="Simulador indisponível">O simulador ainda não está disponível. Fale com quem administra o painel.</Aviso>;
  } else if (motor) corpo = <AreaSimulador motor={motor} />;
  return <Pagina fim={fim}>{corpo}</Pagina>;
}

function Aviso({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="card estreito">
      <h2 className="card-title">{titulo}</h2>
      <p className="muted">{children}</p>
    </section>
  );
}

/** Formulário, decisão e lote; recebe o motor já carregado (o login e a leitura ficam em Conectado). */
export function AreaSimulador({ motor }: { motor: Motor }) {
  const sb = supabase();
  const [form, setForm] = useState<Form>(() => texto(motor.tipico));
  const [perfil, setPerfil] = useState("Cliente típico");
  const [pedido, setPedido] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const { e, faltam } = useMemo(() => paraEntrada(form), [form]);

  async function carregar(id: string) {
    const alvo = id.trim().toUpperCase();
    if (!alvo || !sb) return;
    const { data } = await sb.from("decisoes").select("entrada").eq("id_pedido", alvo).maybeSingle();
    if (!data?.entrada) return setMsg(`Não achei ${alvo} com entrada publicada.`);
    setForm(texto(data.entrada as Entrada));
    setPerfil(alvo);
    setPedido(alvo);
    setMsg(null);
  }

  useEffect(() => {
    const id = decodeURIComponent(window.location.hash.slice(1));
    if (id) carregar(id);
  }, []); // só na abertura: /simulador/#<pedido> vem do botão da Revisão

  const muda = (k: Chave) => (ev: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: ev.target.value });

  return (
    <div className="sim-grid">
      <section className="card sim-form" aria-label="Dados do cliente e do pedido">
        <header className="card-head"><h2 className="card-title">Cliente e pedido</h2></header>
        <div className="chips" role="group" aria-label="Perfis prontos">
          {PERFIS.map(([nome, ajuste]) => (
            <button key={nome} type="button" className="chip-btn sl" aria-pressed={perfil === nome}
              onClick={() => { setForm(texto({ ...motor.tipico, ...ajuste(motor.tipico) })); setPerfil(nome); }}>
              {nome}
            </button>
          ))}
        </div>
        {sb && (
          <form className="sim-carregar" onSubmit={(ev) => { ev.preventDefault(); carregar(pedido); }}>
            <label className="field">
              <span>Ou partir de um pedido real</span>
              <input value={pedido} onChange={(ev) => setPedido(ev.target.value)} placeholder="número do pedido" />
            </label>
            <button type="submit" className="btn-tonal sl">Carregar</button>
          </form>
        )}
        {msg && <p className="erro" role="alert">{msg}</p>}
        {GRUPOS.map(([grupo, campos]) => (
          <fieldset key={grupo} className="sim-grupo">
            <legend>{grupo}</legend>
            {campos.filter(({ k }) => k !== "idade" || motor.atributos.includes("idade")).map(({ k, rotulo }) => (
              <label key={k} className="field">
                <span>{rotulo}</span>
                {k === "prazo_meses" ? (
                  <select value={form[k]} onChange={muda(k)}>
                    {PRAZOS.map((p) => <option key={p} value={String(p)}>{p} meses</option>)}
                  </select>
                ) : k === "tipo_vinculo" ? (
                  <select value={form[k]} onChange={muda(k)}>
                    {VINCULOS.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
                  </select>
                ) : (
                  <input inputMode="decimal" value={form[k]} onChange={muda(k)} />
                )}
              </label>
            ))}
          </fieldset>
        ))}
        <p className="foot">Os campos da conta podem ficar vazios se o cliente não tem movimentação.</p>
      </section>

      <section className="card sim-res" aria-live="polite" aria-label="Decisão da IA">
        <header className="card-head">
          <h2 className="card-title">Decisão da IA</h2>
          <span className="muted card-actions">{perfil}</span>
        </header>
        {e ? <PorQue motor={motor} entrada={e} /> : <p className="erro">Confira: {faltam.join(", ")}.</p>}
        <p className="foot">A mesma IA que decidiu os 2.000 pedidos novos.</p>
      </section>

      <Lote motor={motor} />
    </div>
  );
}

type Linha = { linha: string; d: ReturnType<typeof decidir> };

/** Vários clientes novos de uma vez: um CSV com as colunas da entrada; devolve decisões e o resultado esperado. */
function Lote({ motor }: { motor: Motor }) {
  const [res, setRes] = useState<{ linhas: Linha[]; erros: string[] } | null>(null);

  function baixar(nome: string, csv: string) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = nome;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  function modelo() {
    const t = motor.tipico;
    const cab = ["id", ...CAMPOS.map((c) => c.k)];
    const linha = ["cliente-1", ...CAMPOS.map((c) => t[c.k] ?? "")];
    baixar("clientes_novos_modelo.csv", `${cab.join(",")}\n${linha.join(",")}\n`);
  }

  async function ler(ev: ChangeEvent<HTMLInputElement>) {
    const arq = ev.target.files?.[0];
    if (!arq) return;
    const linhas = (await arq.text()).replace(/^﻿/, "").split(/\r?\n/).filter((l) => l.trim());
    const sep = linhas[0].includes(";") ? ";" : ",";
    const cab = linhas[0].split(sep).map((c) => c.trim().toLowerCase());
    const faltando = CAMPOS.filter((c) => !c.opcional && !cab.includes(c.k)).map((c) => c.k);
    if (faltando.length) return setRes({ linhas: [], erros: [`faltam colunas: ${faltando.join(", ")}`] });
    const out: Linha[] = [];
    const erros: string[] = [];
    linhas.slice(1).forEach((l, i) => {
      const v = l.split(sep);
      const f = Object.fromEntries(cab.map((c, j) => [c, sep === "," ? v[j] : v[j]?.replace(",", ".")]));
      const { e, faltam } = paraEntrada(f);
      const id = f.id?.trim() || `linha ${i + 2}`;
      if (!e) erros.push(`${id}: ${faltam.join(", ")}`);
      else out.push({ linha: id, d: decidir(e, motor) });
    });
    setRes({ linhas: out, erros });
    ev.target.value = "";
  }

  const soma = res && res.linhas.reduce((s, { d }) => ({
    aprovados: s.aprovados + (d.aprova ? 1 : 0), volume: s.volume + d.valor, lucro: s.lucro + d.lucro,
    prejuizo: s.prejuizo + d.prejuizo, resultado: s.resultado + d.ganho,
  }), { aprovados: 0, volume: 0, lucro: 0, prejuizo: 0, resultado: 0 });
  const motivos = res ? Object.entries(res.linhas.filter((l) => !l.d.aprova)
    .reduce<Record<string, number>>((m, { d }) => ({ ...m, [d.motivo]: (m[d.motivo] ?? 0) + 1 }), {}))
    .sort((a, b) => b[1] - a[1]) : [];

  function exportar() {
    if (!res) return;
    const corpo = res.linhas.map(({ linha, d }) =>
      [linha, d.aprova ? "APROVADO" : "NEGADO", d.valor.toFixed(2), `"${d.motivo}"`, d.risco.toFixed(4), d.ganho.toFixed(2)].join(","));
    baixar("decisoes_simuladas.csv", ["id,decisao,valor_aprovado,motivo,p_nao_paga,ganho_esperado", ...corpo].join("\n") + "\n");
  }

  return (
    <section className="card sim-lote" aria-label="Lote de clientes novos">
      <header className="card-head"><h2 className="card-title">Lote de clientes novos (CSV)</h2></header>
      <p className="muted">
        Um cliente por linha, com as colunas do modelo de CSV (vírgula e ponto decimal, ou ponto e vírgula e vírgula decimal).
        Os dados ficam só no seu computador.
      </p>
      <div className="linha-botoes">
        <label className="btn sl sim-arquivo">
          Escolher CSV
          <input type="file" accept=".csv,text/csv" onChange={ler} />
        </label>
        <button type="button" className="btn-tonal sl" onClick={modelo}>Baixar modelo de CSV</button>
        {res && res.linhas.length > 0 && <button type="button" className="btn-tonal sl" onClick={exportar}>Baixar decisões</button>}
      </div>
      {res && soma && (
        <>
          <dl className="stats stats-5">
            <div><dt>Clientes</dt><dd>{int(res.linhas.length)}</dd></div>
            <div><dt>Aprovados</dt><dd>{int(soma.aprovados)} <small>{res.linhas.length ? pct(soma.aprovados / res.linhas.length, 0) : ""}</small></dd></div>
            <div><dt>Volume</dt><dd>{moeda(soma.volume)}</dd></div>
            <div><dt>Lucro e prejuízo esperados</dt><dd>+{moeda(soma.lucro)} <small>−{moeda(soma.prejuizo)}</small></dd></div>
            <div><dt>Resultado esperado</dt><dd>{moeda(soma.resultado)}</dd></div>
          </dl>
          {motivos.length > 0 && (
            <p className="muted">Negados: {motivos.map(([m, n]) => `${int(n)} por ${m}`).join(" · ")}</p>
          )}
          {res.erros.length > 0 && (
            <p className="erro">{int(res.erros.length)} linha(s) ignorada(s): {res.erros.slice(0, 3).join("; ")}{res.erros.length > 3 ? "…" : ""}</p>
          )}
        </>
      )}
    </section>
  );
}
