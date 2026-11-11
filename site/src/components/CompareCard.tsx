"use client";

import { brl, int } from "@/lib/format";
import type { Politica } from "@/lib/types";
import { Card } from "./ui";

export function CompareCard({ politicas, sel, onSel }: { politicas: Politica[]; sel: string; onSel: (id: string) => void }) {
  return (
    <Card title="Comparativo" area="cmp">
      <div className="cmp-wrap">
      <table className="cmp">
        <thead>
          <tr><th>Política</th><th>Aprovados</th><th>Volume</th><th>vs atual</th></tr>
        </thead>
        <tbody>
          {politicas.map((p) => (
            <tr key={p.id} className={p.id === sel ? "is-sel" : ""} onClick={() => onSel(p.id)}>
              <th scope="row">
                <button type="button" aria-pressed={p.id === sel} onClick={(e) => { e.stopPropagation(); onSel(p.id); }}>
                  {p.nome}
                </button>
              </th>
              <td className="num">{int(p.aprovados)}</td>
              <td className="num">{brl(p.volume)}</td>
              <td className="num">
                {p.vsAtual ? (
                  <span title={`Aprova ${p.vsAtual.aprovaAMais} que a atual nega · nega ${p.vsAtual.negaAMais} que a atual aprova`}>
                    <span className="up">+{int(p.vsAtual.aprovaAMais)}</span> / <span className="down">−{int(p.vsAtual.negaAMais)}</span>
                  </span>
                ) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <p className="foot">+ aprova quem a atual nega · − nega quem a atual aprova</p>
    </Card>
  );
}
