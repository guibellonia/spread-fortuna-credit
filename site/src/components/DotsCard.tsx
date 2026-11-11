"use client";

import type { ReactNode } from "react";
import { int, pct } from "@/lib/format";
import { ChartCard, useTip, vars } from "./ui";

type Coluna = { rotulo: string; n: number; curto?: string };

type Props = {
  title: string;
  area: string;
  hero: ReactNode;
  heroLabel: string;
  colunas: Coluna[];
  picoPrefixo: string;
  unidade: string;
  lado: { rotulo: string; valor: ReactNode; detalhe?: string };
  linhas?: number;
};

/** Matriz de pontos: cada coluna é uma categoria; a mais alta fica em destaque. */
export function DotsCard({ title, area, hero, heroLabel, colunas, picoPrefixo, unidade, lado, linhas = 9 }: Props) {
  const { box, bind, node } = useTip();
  const max = Math.max(...colunas.map((c) => c.n));
  const total = colunas.reduce((s, c) => s + c.n, 0);
  const pico = colunas.findIndex((c) => c.n === max);

  return (
    <ChartCard
      title={title}
      area={area}
      table={
        <table className="dtable">
          <thead><tr><th>{picoPrefixo}</th><th>{unidade}</th><th>% do total</th></tr></thead>
          <tbody>
            {colunas.map((c) => (
              <tr key={c.rotulo}><th scope="row">{c.rotulo}</th><td>{int(c.n)}</td><td>{pct(c.n / total)}</td></tr>
            ))}
          </tbody>
        </table>
      }
    >
      <div className="dots-layout">
        <div className="dots-hero">
          <span className="hero">{hero}</span>
          <span className="muted">{heroLabel}</span>
        </div>

        <div className="dots" ref={box}>
          <div className="dots-grid" style={vars({ "--n": colunas.length, "--rows": linhas })}>
            {colunas.map((c, i) => {
              const qtd = c.n ? Math.max(1, Math.round((c.n / max) * linhas)) : 0;
              return (
                <div
                  key={c.rotulo}
                  className={`dot-col sl${i === pico ? " is-peak" : ""}`}
                  {...bind(<><b>{c.rotulo}</b> · {int(c.n)} {unidade} · {pct(c.n / total)}</>, `${c.rotulo}: ${int(c.n)} ${unidade}`)}
                >
                  {i === pico && <span className="badge badge-top">{picoPrefixo}: {c.rotulo}</span>}
                  {Array.from({ length: qtd }, (_, k) => <i key={k} className="dot" />)}
                </div>
              );
            })}
          </div>
          <div className="dots-x" style={vars({ "--n": colunas.length })} aria-hidden>
            {colunas.map((c) => <span key={c.rotulo}>{c.curto ?? c.rotulo}</span>)}
          </div>
          {node}
        </div>

        <div className="dots-side">
          <span className="muted">{lado.rotulo}</span>
          <span className="side-value">{lado.valor}</span>
          {lado.detalhe && <span className="muted">{lado.detalhe}</span>}
        </div>
      </div>
    </ChartCard>
  );
}
