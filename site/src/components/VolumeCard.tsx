"use client";

import { brl, int, pct, VINCULO } from "@/lib/format";
import type { Politica } from "@/lib/types";
import { Card, IconDown, IconUp, vars } from "./ui";

const ORDEM = ["assalariado", "autonomo", "aposentado", "empresario"];

export function VolumeCard({ pol, atual }: { pol: Politica; atual: Politica }) {
  const delta = pol.volume / atual.volume - 1;
  const grupos = [...pol.porVinculo].sort((a, b) => ORDEM.indexOf(a.vinculo) - ORDEM.indexOf(b.vinculo));

  return (
    <Card title="Volume aprovado" area="vol">
      <div className="hero-row">
        <span className="hero">{brl(pol.volume)}</span>
        {pol.id !== atual.id && (
          <span className="chip chip-sm delta" title="Comparado ao volume da política atual">
            {delta >= 0 ? <IconUp /> : <IconDown />}
            {pct(Math.abs(delta))} {delta >= 0 ? "a mais" : "a menos"} que a política atual
          </span>
        )}
      </div>
      <p className="muted">
        {int(pol.aprovados)} aprovados
        {pol.reduzidos > 0 && <> · {int(pol.reduzidos)} com valor reduzido</>}
      </p>
      <ul className="hbars">
        {grupos.map((g) => (
          <li key={g.vinculo}>
            <div className="hbar-row">
              <span>{VINCULO[g.vinculo] ?? g.vinculo}</span>
              <span className="num">{brl(g.volume)}</span>
            </div>
            <div className="hbar" role="img" aria-label={`${VINCULO[g.vinculo]}: ${pct(g.volume / pol.volume)} do volume, ${int(g.pedidos)} pedidos`}>
              <div style={vars({ "--p": g.volume / pol.volume })} />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
