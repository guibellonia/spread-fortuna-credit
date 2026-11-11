"use client";

import { int, mes, pct } from "@/lib/format";
import type { Dados } from "@/lib/types";
import { ChartCard, useTip, vars } from "./ui";

export function CohortCard({ safras }: { safras: Dados["safras"] }) {
  const { box, bind, node } = useTip();
  const { meses, mediaMadura } = safras;
  const topo = Math.ceil((Math.max(...meses.map((m) => m.taxa)) * 100) / 5) * 0.05;
  const pico = meses.reduce((a, m, i) => (m.taxa > meses[a].taxa ? i : a), 0);

  return (
    <ChartCard
      title="Inadimplência por safra"
      area="saf"
      table={
        <table className="dtable">
          <thead><tr><th>Safra</th><th>Aprovados</th><th>Não pagaram</th><th>Taxa</th></tr></thead>
          <tbody>
            {meses.map((m) => (
              <tr key={m.mes}>
                <th scope="row">{mes(m.mes)}{m.maduro ? "" : " *"}</th>
                <td>{int(m.aprovados)}</td>
                <td>{int(m.inadimplentes)}</td>
                <td>{pct(m.taxa)}</td>
              </tr>
            ))}
          </tbody>
          <caption>* menos de 12 meses de contrato na data de corte</caption>
        </table>
      }
    >
      <div>
        <span className="hero">{pct(mediaMadura)}</span>
        <p className="muted">média nos {int(safras.contratosMaduros)} contratos maduros</p>
      </div>

      <div className="cohort" ref={box}>
        <div className="cohort-plot" style={vars({ "--n": meses.length })}>
          <div className="refline" style={vars({ "--p": mediaMadura / topo })} aria-hidden />
          {meses.map((m, i) => (
            <div
              key={m.mes}
              className="cohort-col sl"
              {...bind(
                <><b>{mes(m.mes)}</b> · {pct(m.taxa)} · {int(m.inadimplentes)} de {int(m.aprovados)}{m.maduro ? "" : " · em maturação"}</>,
                `${mes(m.mes)}: ${pct(m.taxa)} de inadimplência`,
              )}
            >
              {i === pico && <span className="badge" style={vars({ "--p": m.taxa / topo })}>{pct(m.taxa, 0)}</span>}
              <div className={`cohort-bar${m.maduro ? " is-mature" : ""}`} style={vars({ "--p": m.taxa / topo })} />
            </div>
          ))}
        </div>
        <div className="cohort-x" style={vars({ "--n": meses.length })} aria-hidden>
          {meses.map((m, i) => (i % 6 === 0 ? <span key={m.mes} style={{ gridColumn: `${i + 1} / span 6` }}>{mes(m.mes)}</span> : null))}
        </div>
        {node}
      </div>

      <ul className="legend">
        <li><i className="sw is-mature" />12+ meses</li>
        <li><i className="sw" />em maturação</li>
        <li><i className="sw-line" />média madura</li>
      </ul>
    </ChartCard>
  );
}
