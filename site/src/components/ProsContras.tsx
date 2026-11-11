"use client";

import { moeda, pct } from "@/lib/format";
import { decidir, sinais, type Entrada, type Motor } from "@/lib/motor";
import type { Dados } from "@/lib/types";
import { frase } from "./PorQue";

type Ponto = { titulo: string; detalhe?: string; grupo?: string };

// grupo dos padrões do painel (mesmo texto de site/scripts/snapshot.py) com o calote que aquele perfil teve
const GRUPO_SINAL: Record<string, [string, string]> = {
  prazo_curto: ["Prazo curto (6 ou 12 meses)", "prazo de 6 ou 12 meses"],
  prazo_36: ["Prazo longo (36 meses)", "prazo de 36 meses"],
  autonomo: ["Autônomo ou empresário", "vínculo de autônomo ou empresário"],
  aposentado: ["Aposentado", "vínculo de aposentado"],
  instavel: ["Entradas da conta instáveis", "entradas da conta instáveis (variação de 16% ou mais)"],
  dividas: ["Parcela e dívidas passam de 35% da renda real", "parcela mais dívidas em outras instituições acima de 35% da renda real"],
};

/** Pontos a favor e contra o cliente, lado a lado, com o calote que cada perfil teve no histórico. */
export function ProsContras({ motor, entrada, padroes, faixa, pontos }: {
  motor: Motor; entrada: Entrada; padroes: Dados["padroes"]; faixa?: string | null; pontos?: number | null;
}) {
  const d = decidir(entrada, motor);
  const p = motor.politica;
  const taxa = (grupo?: string) => padroes.itens.find((i) => i.grupo === grupo)?.taxa;
  const favor: Ponto[] = [];
  const contra: Ponto[] = [];

  if (d.barreiras.restricao) {
    contra.push({ titulo: "Restrição ativa no bureau", detalhe: `${d.restricoes} ${d.restricoes === 1 ? "restrição" : "restrições"}`,
      grupo: "1 restrição ativa no bureau" });
  } else favor.push({ titulo: "Sem restrição no bureau" });

  if (d.barreiras.apertada) {
    contra.push({ titulo: "Conta apertada antes do pedido", detalhe: `saídas maiores que as entradas em ${d.mesesApertada} dos 3 meses`,
      grupo: "saídas maiores que as entradas em algum dos 3 meses antes do pedido" });
  } else favor.push({ titulo: "Conta sem aperto nos 3 meses antes do pedido" });

  const parcela = `parcela de ${moeda(d.parcelaRef)} sobre ${moeda(d.rendaReal)} que entram na conta`;
  if (d.barreiras.pesada) {
    contra.push({ titulo: `Parcela pesa ${pct(d.parcelaRendaReal)} da renda real`, detalhe: `${parcela}; o limite é ${pct(p.teto_parcela_renda_real, 0)}`,
      grupo: "parcela acima de 28% da renda real" });
  } else {
    favor.push({ titulo: `Parcela cabe na renda real (${pct(d.parcelaRendaReal)})`, detalhe: parcela,
      grupo: d.barreiras.apertada ? undefined : "nenhuma das duas barreiras (conta folgada e parcela até 28% da renda real)" });
  }

  const barrado = Object.values(d.barreiras).some(Boolean);
  if (!barrado && d.aprova) {
    favor.push({ titulo: `Risco de não pagar estimado em ${pct(d.risco)}`, detalhe: `o limite é ${pct(p.risco_max)}` });
  } else if (!barrado) {
    contra.push({ titulo: "Risco alto em todos os valores testados", detalhe: `${pct(d.risco)} no valor pedido; o limite é ${pct(p.risco_max)}` });
  }

  for (const s of sinais(entrada, d.valor)) {
    const [titulo, grupo] = GRUPO_SINAL[s.id] ?? [s.nome, undefined];
    (s.peso > 0 ? contra : favor).push({ titulo, grupo });
  }

  const lista = (itens: Ponto[], tipo: "favor" | "contra") => (
    <section className={`pc-col is-${tipo}`} aria-label={tipo === "favor" ? "Pontos a favor" : "Pontos contra"}>
      <h3>
        <span className={`pc-ic ${tipo === "favor" ? "is-ok" : "is-no"}`} aria-hidden>{tipo === "favor" ? "✓" : "✕"}</span>
        {tipo === "favor" ? "A favor" : "Contra"}
        <span className="pc-n">{itens.length}</span>
      </h3>
      {itens.length === 0 ? (
        <p className="pc-vazio">Nenhum ponto {tipo === "favor" ? "a favor" : "contra"}.</p>
      ) : (
        <ul className="pc-lista">
          {itens.map((i) => {
            const t = taxa(i.grupo);
            return (
              <li key={i.titulo}>
                <span className="pc-titulo">{i.titulo}</span>
                {i.detalhe && <span className="pc-det">{i.detalhe}</span>}
                {t != null && padroes.media != null && (
                  <span className={`pc-hist${t > padroes.media ? " is-alto" : ""}`}>
                    {pct(t)} de calote em clientes assim, contra {pct(padroes.media)} da média
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );

  return (
    <div className="pc-box">
      <div className="pc-head">
        <span className={`selo ${d.aprova ? "is-ok" : "is-no"}`}>{d.aprova ? `IA sugere aprovar ${moeda(d.valor)}` : "IA sugere negar"}</span>
        {faixa && faixa !== "barreira" && (
          <span className={`faixa is-${faixa}`}>Faixa {faixa[0].toUpperCase() + faixa.slice(1)}{pontos != null ? ` · ${pontos} ponto(s)` : ""}</span>
        )}
        <span className="pq-frase">{frase(d)}</span>
      </div>
      <div className="pc">
        {lista(favor, "favor")}
        {lista(contra, "contra")}
      </div>
    </div>
  );
}
