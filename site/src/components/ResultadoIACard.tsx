"use client";

import { useState } from "react";
import { brl, brlSinal, int, pct } from "@/lib/format";
import type { ResultadoIA, SomaIA } from "@/lib/types";
import { ChartCard, IconCheck, useTip, vars } from "./ui";

type Visao = "risco" | "faixa";
const FAIXA: Record<string, string> = { verde: "Faixa verde", amarela: "Faixa amarela", laranja: "Faixa laranja" };
const dec2 = (x: number) => x.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function ResultadoIACard({ r }: { r: ResultadoIA }) {
  const { box, bind, node } = useTip();
  const [visao, setVisao] = useState<Visao>("risco");
  const linhas = (visao === "risco" ? r.porRisco : r.porFaixa).map((l) => ({
    ...l, rotulo: visao === "risco" ? `Risco estimado ${l.faixa}` : FAIXA[l.faixa] ?? l.faixa,
  }));
  const escala = Math.max(...linhas.map((l) => l.lucro), 1) + Math.max(...linhas.map((l) => l.prejuizo), 1);
  const z = Math.max(...linhas.map((l) => l.prejuizo), 1) / escala;
  const sub = (l: SomaIA) => `${int(l.aprovados)} aprovados · ${brl(l.volume)} · cerca de ${int(Math.round(l.calotes))} sem pagar`;

  return (
    <ChartCard
      title="Lucro e prejuízo esperados das decisões da IA"
      area="res"
      actions={
        <div className="seg" role="group" aria-label="Agrupar por">
          {([["risco", "Por risco"], ["faixa", "Por faixa"]] as [Visao, string][]).map(([id, nome]) => (
            <button key={id} type="button" className="seg-btn sl" aria-pressed={visao === id} onClick={() => setVisao(id)}>
              {visao === id && <IconCheck />}
              {nome}
            </button>
          ))}
        </div>
      }
      table={
        <table className="dtable">
          <thead><tr><th>Grupo</th><th>Aprovados</th><th>Volume</th><th>Lucro</th><th>Prejuízo</th><th>Resultado</th></tr></thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.faixa}>
                <th scope="row">{l.rotulo}</th>
                <td>{int(l.aprovados)}</td>
                <td>{brl(l.volume)}</td>
                <td>{brlSinal(l.lucro)}</td>
                <td>{brlSinal(-l.prejuizo)}</td>
                <td>{brlSinal(l.resultado)}</td>
              </tr>
            ))}
            <tr>
              <th scope="row">Total</th>
              <td>{int(r.aprovados)}</td>
              <td>{brl(r.volume)}</td>
              <td>{brlSinal(r.lucro)}</td>
              <td>{brlSinal(-r.prejuizo)}</td>
              <td>{brlSinal(r.resultado)}</td>
            </tr>
          </tbody>
          <caption>Esperado pelo modelo que decidiu, nos pedidos que a IA aprovou, no valor aprovado</caption>
        </table>
      }
    >
      <div className="res-layout">
        <div className="res-resumo">
          <div>
            <span className="hero">{brlSinal(r.resultado)}</span>
            <p className="muted">resultado esperado nos {int(r.aprovados)} pedidos que a IA aprovou ({brl(r.volume)})</p>
          </div>
          <dl className="stats">
            <div><dt><i className="sw is-mature" /> Lucro de quem paga</dt><dd>{brlSinal(r.lucro)}</dd></div>
            <div>
              <dt><i className="sw is-neg" /> Prejuízo dos calotes</dt>
              <dd>{brlSinal(-r.prejuizo)} <small>cerca de {int(Math.round(r.calotes))} contratos</small></dd>
            </div>
          </dl>
          {(r.calibracao || r.atual) && (
            <p className="hist-total">
              {r.calibracao && (
                <>
                  Ajustado pelo histórico (× {dec2(r.calibracao.fator)}): <b>{brlSinal(r.calibracao.resultado)}</b>. Nos
                  pedidos passados, o ganho observado ficou {pct(1 - r.calibracao.fator)} abaixo do que o modelo estimava.
                </>
              )}
              {r.atual && <> Política atual nos mesmos pedidos, pelo mesmo modelo: {brlSinal(r.atual.resultado)}.</>}
            </p>
          )}
        </div>

        <div>
          <div className="div-wrap" ref={box}>
            <ul className="div-list">
              {linhas.map((l) => (
                <li
                  key={l.faixa}
                  className="div-row sl"
                  {...bind(
                    <><b>{l.rotulo}</b> · lucro {brlSinal(l.lucro)} · prejuízo {brlSinal(-l.prejuizo)} · {brlSinal(l.resultado)}</>,
                    `${l.rotulo}: lucro ${brlSinal(l.lucro)}, prejuízo ${brlSinal(-l.prejuizo)}, resultado ${brlSinal(l.resultado)}`,
                  )}
                >
                  <div>
                    <div className="div-label">{l.rotulo}</div>
                    <div className="div-sub">{sub(l)}</div>
                  </div>
                  <div className="div-track" style={vars({ "--z": z })} aria-hidden>
                    <div className="div-bar is-neg" style={vars({ "--l": z - l.prejuizo / escala, "--w": l.prejuizo / escala })} />
                    <div className="div-bar" style={vars({ "--l": z, "--w": l.lucro / escala })} />
                  </div>
                  <span className="div-val num">{brlSinal(l.resultado)}</span>
                </li>
              ))}
            </ul>
            {node}
          </div>
          <ul className="legend res-legenda">
            <li><i className="sw is-mature" />lucro esperado</li>
            <li><i className="sw is-neg" />prejuízo esperado</li>
            <li>à direita, o resultado do grupo</li>
          </ul>
        </div>
      </div>
      <p className="foot">
        Para cada pedido aprovado, no valor aprovado: prejuízo = 60% do valor × chance de não pagar; lucro = +15% de quem
        paga em dia e +5% de quem paga com atraso. É o que o modelo espera, não desfecho. Fonte: <code>saida/decisoes_mescla.csv</code>{" "}
        via <code>site/scripts/snapshot.py</code>; ajuste pelo histórico em <code>site/scripts/historico.py</code>.
      </p>
    </ChartCard>
  );
}
