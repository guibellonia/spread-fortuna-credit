"use client";

import { int, pct } from "@/lib/format";
import type { Dados } from "@/lib/types";
import { ChartCard, vars } from "./ui";

/** Parte 1 do painel (manual 5.1): cada padrão no formato pedido, com a taxa comparada à média. */
export function PadroesCard({ padroes }: { padroes: Dados["padroes"] }) {
  const media = padroes.media ?? 0;
  const topo = Math.max(...padroes.itens.map((i) => i.taxa), media);

  return (
    <ChartCard
      title="Padrões encontrados"
      area="pad"
      actions={<span className="chip chip-sm">Média {pct(media)}</span>}
      table={
        <table className="dtable">
          <thead><tr><th>Clientes com</th><th>Inadimplência</th><th>vs média</th><th>Clientes</th><th>Novos</th></tr></thead>
          <tbody>
            {padroes.itens.map((p) => (
              <tr key={p.grupo}>
                <th scope="row">{p.grupo}</th>
                <td>{pct(p.taxa)}</td>
                <td>{p.vsMedia.toLocaleString("pt-BR")}×</td>
                <td>{int(p.clientes)}</td>
                <td>{p.novos != null ? int(p.novos) : "—"}</td>
              </tr>
            ))}
          </tbody>
          <caption>{padroes.fonte}; “novos” = pedidos de out/26 com a mesma característica</caption>
        </table>
      }
    >
      <ul className="padroes" style={vars({ "--media": media / topo })}>
        {padroes.itens.map((p) => (
          <li key={p.grupo} className={p.vsMedia >= 1.3 ? "is-alto" : p.vsMedia <= 0.75 ? "is-baixo" : ""}>
            <p className="pad-frase">
              Clientes com {p.grupo} têm inadimplência de <b>{pct(p.taxa)}</b>, contra {pct(media)} da média.
              Afeta {int(p.clientes)} clientes.
            </p>
            <div className="pad-barra" role="img" aria-label={`${pct(p.taxa)} contra ${pct(media)} da média`}>
              <div style={vars({ "--p": p.taxa / topo })} />
              <i aria-hidden />
            </div>
            {p.novos != null && <span className="muted pad-novos">{int(p.novos)} nos novos</span>}
          </li>
        ))}
      </ul>
      <p className="foot">{padroes.fonte}. A linha vertical marca a média.</p>
    </ChartCard>
  );
}
