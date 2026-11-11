"use client";

import { useState, type ReactNode } from "react";
import { brl, brlSinal, dataHora, int, mes, pct } from "@/lib/format";
import type { BaseHist, DadosHistorico } from "@/lib/types";
import { TopBar } from "./TopBar";
import { Card, ChartCard, IconCheck, IconDown, IconUp, useTip, vars } from "./ui";

type IdBase = keyof DadosHistorico["bases"];

const taxa = (t: number | null | undefined) => (t == null ? "—" : pct(t));
const dois = (x: number) => x.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function Historico({ dados }: { dados: DadosHistorico }) {
  const [base, setBase] = useState<IdBase>("todos");
  const b = dados.bases[base];
  const opcoes: { id: IdBase; nome: string }[] = [
    { id: "todos", nome: `${int(dados.bases.todos.pedidos)} pedidos` },
    { id: "maduros", nome: `Só maduros · até ${mes(dados.maduroAte.slice(0, 7))}` },
  ];

  return (
    <>
      <TopBar ativo="historico" fim={<>Dados de {dataHora(dados.geradoEm)}</>} />

      <main className="page">
        <div className="page-head">
          <h1 className="display">Proposta no histórico</h1>
          <div className="filters">
            <div className="seg" role="group" aria-label="Pedidos considerados">
              {opcoes.map((o) => (
                <button key={o.id} type="button" className="seg-btn sl" aria-pressed={o.id === base} onClick={() => setBase(o.id)}>
                  {o.id === base && <IconCheck />}
                  {o.nome}
                </button>
              ))}
            </div>
            <span className="chip">{mes(b.periodo[0])} a {mes(b.periodo[1])}</span>
          </div>
        </div>
        <p className="hist-intro">
          Cada pedido do histórico decidido de novo pela Proposta e comparado com o que a Fortuna decidiu e com o que
          aconteceu depois. Para não haver vazamento, o modelo que decide um trimestre foi treinado sem ele. Resultado
          pela regra da nota: +15% em dia, +5% com atraso, −60% sem pagar.
        </p>

        <div className="grid hist">
          <VereditoCard b={b} />
          <AjustesCard b={b} />
          <MatrizCard b={b} />
          <MesesCard b={b} />
          <EstimativaCard e={dados.estimativa} />
          {dados.piloto && <PilotoCard p={dados.piloto} />}
        </div>

        <footer className="page-foot">
          Proposta de <code>src/politica.py</code> refeita trimestre a trimestre, com o modelo treinado nos outros sete ·
          desfecho do banco Fortuna · gerado por <code>site/scripts/historico.py</code>
        </footer>
      </main>
    </>
  );
}

function VereditoCard({ b }: { b: BaseHist }) {
  const dif = b.proposta.resultado - b.real.resultado;
  const melhorou = dif >= 0;
  return (
    <Card title="Resultado observado" area="ver">
      <div className="hero-row">
        <span className="hero">{brlSinal(dif)}</span>
        <span className={`chip chip-sm ${melhorou ? "is-up" : "is-down"}`}>
          {melhorou ? <IconUp /> : <IconDown />}
          {melhorou ? "melhorou" : "piorou"}
        </span>
      </div>
      <p className="muted">
        A Proposta rende {brl(b.proposta.resultado)} contra {brl(b.real.resultado)} da decisão real, nos mesmos pedidos e
        com o desfecho que aconteceu.
      </p>
      <dl className="stats">
        <div><dt>Calote dos aprovados</dt><dd>{taxa(b.real.taxa)} → {taxa(b.proposta.taxa)}</dd></div>
        <div><dt>Contratos sem pagar</dt><dd>{int(b.real.calotes)} → {int(b.proposta.calotes)}</dd></div>
        <div className="is-largo"><dt>Volume com desfecho</dt><dd>{brl(b.real.volume)} → {brl(b.proposta.volume)}</dd></div>
        <div className="is-largo">
          <dt>Aprovações novas, que a Fortuna negou</dt>
          <dd>{int(b.proposta.novos)} <small>· {brl(b.proposta.volumeNovos)}</small></dd>
        </div>
      </dl>
      <p className="hist-total">
        Somando o ganho esperado das aprovações novas, que não têm desfecho porque a Fortuna negou:{" "}
        <b>{brlSinal(dif + b.proposta.resultadoNovos)}</b>
      </p>
    </Card>
  );
}

function AjustesCard({ b }: { b: BaseHist }) {
  const { box, bind, node } = useTip();
  const pos = Math.max(0, ...b.ajustes.map((a) => a.efeito));
  const neg = Math.max(0, ...b.ajustes.map((a) => -a.efeito));
  const escala = pos + neg || 1;
  const z = neg / escala;
  const observado = b.ajustes.filter((a) => !a.estimado).reduce((s, a) => s + a.efeito, 0);
  const sub = (a: BaseHist["ajustes"][number]) => {
    if (a.pedidos === 0) return "nenhum pedido nesta base";
    if (a.estimado) return `${int(a.pedidos)} pedidos sem desfecho · risco estimado ${taxa(a.pNaoPaga)}`;
    if (a.id === "valor") return `${int(a.pedidos)} com valor menor · ${taxa(a.taxa)} não pagaram`;
    return `nega ${int(a.pedidos)} que a Fortuna aprovou · ${taxa(a.taxa)} não pagaram`;
  };

  return (
    <ChartCard
      title="O que cada ajuste fez no resultado"
      area="aj"
      table={
        <table className="dtable">
          <thead><tr><th>Ajuste</th><th>Pedidos</th><th>Não pagaram</th><th>Efeito</th></tr></thead>
          <tbody>
            {b.ajustes.map((a) => (
              <tr key={a.id}>
                <th scope="row">{a.rotulo}{a.estimado ? " *" : ""}</th>
                <td>{int(a.pedidos)}</td>
                <td>{a.estimado ? `${taxa(a.pNaoPaga)} est.` : taxa(a.taxa)}</td>
                <td>{brlSinal(a.efeito)}</td>
              </tr>
            ))}
          </tbody>
          <caption>* sem desfecho: ganho esperado pelo modelo</caption>
        </table>
      }
    >
      <div className="div-wrap" ref={box}>
        <ul className="div-list">
          {b.ajustes.map((a) => (
            <li
              key={a.id}
              className="div-row sl"
              {...bind(
                <><b>{a.rotulo}</b> · {brlSinal(a.efeito)}{a.estimado ? " estimado" : ""}</>,
                `${a.rotulo}: ${brlSinal(a.efeito)}${a.estimado ? ", estimado" : ""}`,
              )}
            >
              <div>
                <div className="div-label">{a.rotulo}</div>
                <div className="div-sub">{sub(a)}</div>
              </div>
              <div className="div-track" style={vars({ "--z": z })} aria-hidden>
                {a.efeito !== 0 && (
                  <div
                    className={`div-bar${a.efeito < 0 ? " is-neg" : ""}${a.estimado ? " is-est" : ""}`}
                    style={vars({ "--l": a.efeito >= 0 ? z : z - -a.efeito / escala, "--w": Math.abs(a.efeito) / escala })}
                  />
                )}
              </div>
              <span className="div-val num">{brlSinal(a.efeito)}</span>
            </li>
          ))}
        </ul>
        {node}
      </div>
      <ul className="legend">
        <li><i className="sw is-mature" />melhorou</li>
        <li><i className="sw is-neg" />piorou</li>
        <li><i className="sw" />estimado, sem desfecho</li>
      </ul>
      <p className="foot">
        Os ajustes com desfecho somam {brlSinal(observado)}, a diferença do resultado observado. Barreira e modelo: o
        efeito é deixar de ter o resultado que esses pedidos deram. Valor: supõe o mesmo desfecho com o valor menor, o
        que é conservador para a Proposta.
      </p>
    </ChartCard>
  );
}

function MatrizCard({ b }: { b: BaseHist }) {
  const m = (f: boolean, p: boolean) => b.matriz.find((x) => x.fortuna === f && x.proposta === p)!;
  const concorda = (m(true, true).pedidos + m(false, false).pedidos) / b.pedidos;
  const cel = (f: boolean, p: boolean) => {
    const c = m(f, p);
    let sub: ReactNode = "as duas negam";
    if (f && p) sub = <>{brl(c.volumeProposta)} na Proposta, {brl(c.volumeReal)} na real · {taxa(c.taxa)} não pagaram</>;
    else if (f) sub = <>{brl(c.volumeReal)} emprestados · <b>{taxa(c.taxa)} não pagaram</b></>;
    else if (p) sub = <>{brl(c.volumeProposta)} · sem desfecho, a Fortuna negou</>;
    return (
      <td className={f !== p ? "is-dif" : undefined}>
        <span className="mat-n">{int(c.pedidos)}</span>
        <span className="mat-sub">{sub}</span>
      </td>
    );
  };

  return (
    <Card title="Decisão real × Proposta" area="mat">
      <p className="muted">As duas concordam em {pct(concorda, 0)} dos {int(b.pedidos)} pedidos.</p>
      <table className="matriz">
        <thead>
          <tr><td /><th scope="col">Proposta aprova</th><th scope="col">Proposta nega</th></tr>
        </thead>
        <tbody>
          <tr><th scope="row">Fortuna aprovou</th>{cel(true, true)}{cel(true, false)}</tr>
          <tr><th scope="row">Fortuna negou</th>{cel(false, true)}{cel(false, false)}</tr>
        </tbody>
      </table>
      <p className="foot">
        Calote dos {int(b.real.aprovados)} aprovados pela Fortuna: {taxa(b.real.taxa)}. A Proposta limita a parcela a 28%
        da renda, então nunca empresta mais do que a Fortuna emprestou.
      </p>
    </Card>
  );
}

function MesesCard({ b }: { b: BaseHist }) {
  const { box, bind, node } = useTip();
  const meses = b.meses.map((m) => ({ ...m, dif: m.proposta - m.real }));
  const pos = Math.max(0, ...meses.map((m) => m.dif));
  const neg = Math.max(0, ...meses.map((m) => -m.dif));
  const escala = pos + neg || 1;
  const z = neg / escala;
  const passo = meses.length > 12 ? 6 : 3;
  const piores = meses.filter((m) => m.dif < 0);
  const maduros = meses.filter((m) => m.maduro);
  const temImaturo = meses.some((m) => !m.maduro);
  const soma = (l: typeof meses, k: "aprovadosReal" | "calotesReal") => l.reduce((s, m) => s + m[k], 0);

  return (
    <ChartCard
      title="Diferença mês a mês"
      area="mes"
      table={
        <table className="dtable">
          <thead><tr><th>Mês</th><th>Real</th><th>Proposta</th><th>Diferença</th><th>Calotes</th></tr></thead>
          <tbody>
            {meses.map((m) => (
              <tr key={m.mes}>
                <th scope="row">{mes(m.mes)}{m.maduro ? "" : " *"}</th>
                <td>{brl(m.real)}</td>
                <td>{brl(m.proposta)}</td>
                <td>{brlSinal(m.dif)}</td>
                <td>{int(m.calotesReal)} → {int(m.calotesProposta)}</td>
              </tr>
            ))}
          </tbody>
          <caption>* menos de 12 meses de contrato na data de corte · só desfecho observado</caption>
        </table>
      }
    >
      <div>
        <div className="hero-row">
          <span className="hero">{meses.filter((m) => m.dif > 0).length}</span>
          <span className="hero-of">de {meses.length} meses</span>
        </div>
        <p className="muted">em que a Proposta rende mais que a decisão real, só com desfecho observado</p>
      </div>

      <div className="mes" ref={box}>
        <div className="mes-plot" style={vars({ "--n": meses.length })}>
          <div className="mes-zero" style={vars({ "--z": z })} aria-hidden />
          {meses.map((m) => (
            <div
              key={m.mes}
              className="mes-col sl"
              {...bind(
                <><b>{mes(m.mes)}</b> · {brlSinal(m.dif)} · Proposta {brl(m.proposta)} × real {brl(m.real)}{m.maduro ? "" : " · em maturação"}</>,
                `${mes(m.mes)}: diferença de ${brlSinal(m.dif)}`,
              )}
            >
              <div
                className={`mes-bar${m.dif < 0 ? " is-neg" : ""}${m.maduro ? "" : " is-imaturo"}`}
                style={vars({ "--b": m.dif >= 0 ? z : z - -m.dif / escala, "--h": Math.abs(m.dif) / escala })}
              />
            </div>
          ))}
        </div>
        <div className="cohort-x" style={vars({ "--n": meses.length })} aria-hidden>
          {meses.map((m, i) => (i % passo === 0 ? <span key={m.mes} style={{ gridColumn: `${i + 1} / span ${passo}` }}>{mes(m.mes)}</span> : null))}
        </div>
        {node}
      </div>

      <ul className="legend">
        <li><i className="sw is-mature" />melhorou</li>
        {piores.length > 0 && <li><i className="sw is-neg" />piorou</li>}
        {temImaturo && <li><i className="sw is-soft" />tom claro: menos de 12 meses</li>}
      </ul>
      {piores.length > 0 && piores.every((m) => !m.maduro) && maduros.length > 0 && (
        <p className="foot">
          Os {piores.length} meses em que a Proposta perde são os mais recentes: só {pct(soma(piores, "calotesReal") / soma(piores, "aprovadosReal"))} dos
          aprovados neles aparecem como calote até agora, contra {pct(soma(maduros, "calotesReal") / soma(maduros, "aprovadosReal"))} nos
          meses maduros. Quem a Proposta nega ali ainda conta como bom pagador.
        </p>
      )}
    </ChartCard>
  );
}

function EstimativaCard({ e }: { e: DadosHistorico["estimativa"] }) {
  const { box, bind, node } = useTip();
  const topo = Math.ceil(Math.max(...e.faixas.flatMap((f) => [f.estimada, f.observada])) * 10) / 10;
  const desvio = e.ganhoObservado / e.ganhoEstimado - 1;
  const subestima = e.faixas.length > 0 && e.faixas[0].observada > e.faixas[0].estimada;

  return (
    <ChartCard
      title="A estimativa bate com o que aconteceu?"
      area="est"
      table={
        <table className="dtable">
          <thead><tr><th>Risco estimado</th><th>Contratos</th><th>Estimada</th><th>Observada</th></tr></thead>
          <tbody>
            {e.faixas.map((f) => (
              <tr key={f.faixa}>
                <th scope="row">{f.faixa}</th>
                <td>{int(f.pedidos)}</td>
                <td>{pct(f.estimada)}</td>
                <td>{pct(f.observada)}</td>
              </tr>
            ))}
          </tbody>
          <caption>Inadimplência estimada pelo modelo × observada, nos contratos maduros que a Fortuna aprovou</caption>
        </table>
      }
    >
      <div className="est-layout">
        <dl className="stats">
          <div><dt>AUC do modelo da Proposta</dt><dd>{dois(e.aucModelo)}</dd></div>
          <div><dt>AUC do score (regra atual)</dt><dd>{dois(e.aucScore)}</dd></div>
          <div><dt>Ganho estimado</dt><dd>{brl(e.ganhoEstimado)}</dd></div>
          <div>
            <dt>Ganho observado</dt>
            <dd>{brl(e.ganhoObservado)} <small>{pct(Math.abs(desvio))} {desvio < 0 ? "abaixo" : "acima"}</small></dd>
          </div>
        </dl>
        <div className="cal" ref={box}>
          <div className="cal-plot" style={vars({ "--n": e.faixas.length })}>
            {e.faixas.map((f) => (
              <div
                key={f.faixa}
                className="cal-grupo sl"
                {...bind(
                  <><b>Risco estimado {f.faixa}</b> · {int(f.pedidos)} contratos · estimada {pct(f.estimada)} · observada {pct(f.observada)}</>,
                  `Risco estimado ${f.faixa}: estimada ${pct(f.estimada)}, observada ${pct(f.observada)}`,
                )}
              >
                <div className="cal-bar" style={vars({ "--p": f.estimada / topo })} />
                <div className="cal-bar is-obs" style={vars({ "--p": f.observada / topo })} />
              </div>
            ))}
          </div>
          <div className="cal-x" style={vars({ "--n": e.faixas.length })} aria-hidden>
            {e.faixas.map((f) => <span key={f.faixa}>{f.faixa}</span>)}
          </div>
          {node}
        </div>
      </div>
      <ul className="legend">
        <li><i className="sw" />inadimplência estimada</li>
        <li><i className="sw is-mature" />observada</li>
      </ul>
      <p className="foot">
        Nos {int(e.contratos)} contratos maduros que a Fortuna aprovou ({int(e.calotes)} não pagaram), com o risco
        estimado no valor que ela aprovou por um modelo que não viu o trimestre do pedido. AUC: o quanto o número separa
        quem paga de quem não paga (0,50 é sorteio).
        {subestima && " O modelo subestima o calote de quem ele vê como mais seguro."} O ganho que ele promete
        sai {pct(Math.abs(desvio))} {desvio < 0 ? "acima" : "abaixo"} do que aconteceu, nos {int(e.aprovadosProposta)} pedidos
        que as duas aprovam, no valor da Proposta.
      </p>
    </ChartCard>
  );
}

function PilotoCard({ p }: { p: NonNullable<DadosHistorico["piloto"]> }) {
  const linhas = [
    { rotulo: "A Proposta aprovaria", n: p.propostaAprova, taxa: p.taxaAprova ?? 0 },
    { rotulo: "A Proposta negaria", n: p.propostaNega, taxa: p.taxaNega ?? 0 },
  ];
  const topo = Math.max(...linhas.map((l) => l.taxa), 0.01);

  return (
    <ChartCard
      title="Piloto: quem a regra atual nega"
      area="pil"
      table={
        <table className="dtable">
          <thead><tr><th>Aprovados no piloto fora da regra</th><th>Pedidos</th><th>Não pagaram</th></tr></thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.rotulo}><th scope="row">{l.rotulo}</th><td>{int(l.n)}</td><td>{pct(l.taxa)}</td></tr>
            ))}
          </tbody>
        </table>
      }
    >
      <div>
        <span className="hero">{taxa(p.taxaAprova)}</span>
        <p className="muted">
          de calote nos {int(p.propostaAprova)} que a Proposta aprovaria, entre os {int(p.aprovadosForaDaRegra)} que a
          Fortuna aprovou no piloto mesmo fora da regra atual
        </p>
      </div>
      <ul className="hbars">
        {linhas.map((l) => (
          <li key={l.rotulo}>
            <div className="hbar-row">
              <span>{l.rotulo} · {int(l.n)}</span>
              <span className="num">{pct(l.taxa)} não pagaram</span>
            </div>
            <div className="hbar" role="img" aria-label={`${l.rotulo}: ${int(l.n)} pedidos, ${pct(l.taxa)} não pagaram`}>
              <div style={vars({ "--p": l.taxa / topo })} />
            </div>
          </li>
        ))}
      </ul>
      <p className="foot">
        Score até 600, renda até R$ 2 mil ou restrição, aprovados assim mesmo no piloto da Fortuna: é o único desfecho
        observado de quem a regra atual nega, e o que sustenta as aprovações novas. Contratos com menos de 12 meses; o
        calote ainda pode crescer.
      </p>
    </ChartCard>
  );
}
