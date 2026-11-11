"use client";

import { int, pct } from "@/lib/format";
import type { Politica } from "@/lib/types";
import { ChartCard, useTip, vars } from "./ui";

export function FunnelCard({ pol }: { pol: Politica }) {
  const { box, bind, node } = useTip();
  const total = pol.funil[0].restantes;
  const ultima = pol.funil.length - 1;

  const linhas = pol.funil.map((e, i) => {
    const antes = i ? pol.funil[i - 1].restantes : total;
    return { ...e, i, perda: antes - e.restantes, queda: antes ? (antes - e.restantes) / antes : 0, p: e.restantes / total };
  });

  return (
    <ChartCard
      title="Funil de decisão"
      area="funil"
      actions={<span className="chip chip-sm">{pol.nome}</span>}
      table={
        <table className="dtable">
          <thead><tr><th>Etapa</th><th>Pedidos</th><th>% do total</th><th>Saem na etapa</th></tr></thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.rotulo}>
                <th scope="row">{l.i ? `${l.i}. ${l.rotulo}` : l.rotulo}</th>
                <td>{int(l.restantes)}</td>
                <td>{pct(l.p)}</td>
                <td>{l.i ? int(l.perda) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      <div className="funnel" ref={box} style={vars({ "--n": pol.funil.length })}>
        {linhas.map((l) => (
          <div
            key={l.rotulo}
            className={`stage sl${l.i === ultima ? " is-final" : ""}`}
            {...bind(
              <>
                <b>{int(l.restantes)} pedidos</b> · {pct(l.p, 0)} do total
                {l.i > 0 && <> · −{int(l.perda)} nesta etapa ({pct(l.queda, 0)})</>}
              </>,
              `${l.rotulo}: ${int(l.restantes)} pedidos`,
            )}
          >
            <div className="stage-head">
              <span className="stage-label">{l.i ? <><span className="stage-n">{l.i}</span>{l.rotulo}</> : l.rotulo}</span>
              <span className="stage-value">{int(l.restantes)}</span>
              <span className="stage-sub">{l.i === ultima ? "aprovados" : pct(l.p, 0)}</span>
            </div>
            <div className="track"><div className="fill" style={vars({ "--p": l.p })} /></div>
          </div>
        ))}
        {node}
      </div>
    </ChartCard>
  );
}
