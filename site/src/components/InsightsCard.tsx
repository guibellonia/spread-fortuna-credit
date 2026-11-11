"use client";

import { useState } from "react";
import { int, pct } from "@/lib/format";
import type { Dados } from "@/lib/types";
import { IconSpark } from "./ui";

/** Padrões no formato do manual, um por vez. Avança sozinho; para no hover/foco e com movimento reduzido. */
export function InsightsCard({ padroes }: { padroes: Dados["padroes"] }) {
  const [i, setI] = useState(0);
  const itens = padroes.itens;
  if (!itens.length || padroes.media == null) return null;
  const p = itens[i];
  const taxa = p.aprox ? "~100%" : pct(p.taxa, 0);

  return (
    <section className="card insight" style={{ gridArea: "ins" }} aria-roledescription="carrossel" aria-label="Padrões encontrados">
      <header className="card-head">
        <span className="chip chip-sm chip-glass"><IconSpark />Padrões</span>
        <span className="muted insight-count">{i + 1} de {itens.length}</span>
      </header>

      <div className="insight-body" key={i} aria-live="polite">
        <span className="insight-num">{taxa}</span>
        <p className="insight-text">
          Clientes com {p.grupo} têm inadimplência de {taxa}, contra {pct(padroes.media)} da média.
        </p>
        <p className="insight-sub">Afeta {int(p.clientes)} clientes · {p.vsMedia.toLocaleString("pt-BR")}× a média</p>
      </div>

      <div className="progress" role="group" aria-label="Escolher padrão">
        {itens.map((it, k) => (
          <button
            key={it.grupo}
            type="button"
            className={k < i ? "is-done" : k === i ? "is-on" : ""}
            aria-label={`Padrão ${k + 1}: ${it.grupo}`}
            aria-current={k === i}
            onClick={() => setI(k)}
          >
            <span><i onAnimationEnd={() => setI((i + 1) % itens.length)} /></span>
          </button>
        ))}
      </div>
      <p className="insight-foot">Inadimplência observada no {padroes.fonte}</p>
    </section>
  );
}
