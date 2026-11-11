"use client";

import { brl, int } from "@/lib/format";
import type { Dados, Politica } from "@/lib/types";
import { Card } from "./ui";

// linhas da comparação que correspondem a uma política do seletor
const LIGA: Record<string, string> = { atual: "atual", regras_bilosca: "regras", hibrida: "proposta" };

const sinal = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${brl(Math.abs(v))}`;

export function CompareCard({ politicas, comparacao, sel, onSel }: {
  politicas: Politica[]; comparacao: Dados["comparacao"]; sel: string; onSel: (id: string) => void;
}) {
  const linhas = comparacao.length
    ? comparacao
    : politicas.map((p) => ({ id: p.id, nome: p.nome, aprovados: p.aprovados, volume: p.volume,
        ganhoMin: NaN, ganhoMax: NaN, foraAmostra: null, calotesForaAmostra: null }));

  return (
    <Card title="Qual política rende mais" area="cmp">
      <div className="cmp-wrap">
        <table className="cmp">
          <thead>
            <tr>
              <th>Política</th><th>Aprovados</th><th>Volume</th>
              <th>Ganho esperado vs atual</th><th>Fora da amostra</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => {
              const alvo = LIGA[l.id] ?? (politicas.some((p) => p.id === l.id) ? l.id : null);
              return (
                <tr key={l.id} className={`${alvo && alvo === sel ? "is-sel" : ""}${alvo ? "" : " is-alt"}`}
                    onClick={() => alvo && onSel(alvo)}>
                  <th scope="row">
                    {alvo ? (
                      <button type="button" aria-pressed={alvo === sel} onClick={(e) => { e.stopPropagation(); onSel(alvo); }}>
                        {l.nome}
                      </button>
                    ) : <span>{l.nome} <small className="muted">· medida e recusada</small></span>}
                  </th>
                  <td className="num">{int(l.aprovados)}</td>
                  <td className="num">{brl(l.volume)}</td>
                  <td className="num">
                    {Number.isNaN(l.ganhoMin) ? "—" : l.id === "atual" ? "referência" : `${sinal(l.ganhoMin)} a ${sinal(l.ganhoMax)}`}
                  </td>
                  <td className="num">
                    {l.foraAmostra == null ? "—" : l.id === "atual" ? `${int(l.calotesForaAmostra ?? 0)} calotes` :
                      `${sinal(l.foraAmostra)} · ${int(l.calotesForaAmostra ?? 0)} calotes`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="foot">
        Ganho esperado: resultado da política menos o da atual nos 2.000 novos, pela regra da nota (+15% em dia, +5% com
        atraso, −60% sem pagar), estimado por três modelos (GBM corrigido, sobrevivência e logístico; os dois últimos não
        participam da decisão). Fora da amostra: pedidos de out/25 a mar/26 com desfecho observado, modelo treinado só até
        set/25. Fonte: <code>src/politica_mescla.py --comparar</code>.
      </p>
    </Card>
  );
}
