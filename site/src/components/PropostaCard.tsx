"use client";

import { brl, int } from "@/lib/format";
import type { Dados } from "@/lib/types";
import { Card } from "./ui";

/** Parte 2 do painel (manual 5.1): a política proposta em passos, na ordem em que são aplicados. */
export function PropostaCard({ proposta }: { proposta: Dados["proposta"] }) {
  return (
    <Card
      title="Política proposta"
      area="prop"
      actions={<span className="chip chip-sm">{int(proposta.aprovados)} aprovados · {brl(proposta.volume)}</span>}
    >
      <ol className="passos">
        {proposta.passos.map((p, i) => (
          <li key={p.titulo}>
            <span className="passo-n" aria-hidden>{i + 1}</span>
            <div>
              <p className="passo-titulo">{p.titulo}</p>
              <p className="passo-texto">{p.texto}</p>
              {p.negados != null && <span className="chip chip-sm">nega {int(p.negados)}</span>}
              {p.reduzidos != null && <span className="chip chip-sm">{int(p.reduzidos)} aprovados com menos que o pedido</span>}
              {p.divergentes != null && (
                <span className="chip chip-sm">
                  {int(p.divergentes)} diferentes da atual · {int(p.laranja ?? 0)} na faixa laranja
                </span>
              )}
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
