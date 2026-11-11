"use client";

import { useState } from "react";
import { brl, dataHora, int, mes, pct } from "@/lib/format";
import type { Dados } from "@/lib/types";
import { ApiCard } from "./ApiCard";
import { CohortCard } from "./CohortCard";
import { CompareCard } from "./CompareCard";
import { DotsCard } from "./DotsCard";
import { FunnelCard } from "./FunnelCard";
import { InsightsCard } from "./InsightsCard";
import { PadroesCard } from "./PadroesCard";
import { PropostaCard } from "./PropostaCard";
import { ResultadoIACard } from "./ResultadoIACard";
import { TopBar } from "./TopBar";
import { IconCheck } from "./ui";
import { VolumeCard } from "./VolumeCard";

export function Dashboard({ dados }: { dados: Dados }) {
  const [polId, setPolId] = useState(dados.politicas.some((p) => p.id === "proposta") ? "proposta" : dados.politicas[0].id);
  const atual = dados.politicas[0];
  const pol = dados.politicas.find((p) => p.id === polId) ?? atual;
  const { pedidos, bureau } = dados;

  return (
    <>
      <TopBar ativo="geral" fim={<>Dados de {dataHora(dados.geradoEm)}</>} />

      <main className="page">
        <div className="page-head">
          <h1 className="display">Visão geral</h1>
          <div className="filters">
            <div className="seg" role="group" aria-label="Política">
              {dados.politicas.map((p) => (
                <button key={p.id} type="button" className="seg-btn sl" aria-pressed={p.id === pol.id} onClick={() => setPolId(p.id)}>
                  {p.id === pol.id && <IconCheck />}
                  {p.nome}
                </button>
              ))}
            </div>
            <span className="chip">{mes(pedidos.periodo[0].slice(0, 7))} · {int(pedidos.total)} pedidos novos</span>
            <span className="chip">Corte {dataHora(dados.corte)}</span>
          </div>
        </div>

        <div className="grid">
          <FunnelCard pol={pol} />
          <VolumeCard pol={pol} atual={atual} />
          {dados.resultadoIA && <ResultadoIACard r={dados.resultadoIA} />}
          <CohortCard safras={dados.safras} />
          <DotsCard
            title="Pedidos novos"
            area="ped"
            hero={int(pedidos.total)}
            heroLabel={`${brl(pedidos.valorSolicitado)} solicitados`}
            colunas={pedidos.porDiaSemana.map((d) => ({ rotulo: d.dia, n: d.n }))}
            picoPrefixo="Pico"
            unidade="pedidos"
            lado={{ rotulo: "Valor mediano", valor: brl(pedidos.valorMediano) }}
          />
          <DotsCard
            title="Score do bureau"
            area="sco"
            hero={int(bureau.scoreMediano)}
            heroLabel="score mediano"
            colunas={bureau.scoreFaixas.map((f) => ({ rotulo: f.faixa, n: f.n, curto: f.faixa.split("–")[0] }))}
            picoPrefixo="Maior faixa"
            unidade="clientes"
            lado={{ rotulo: "Com restrição", valor: int(bureau.comRestricao), detalhe: pct(bureau.comRestricao / bureau.total) }}
          />
          <InsightsCard padroes={dados.padroes} />
          <PropostaCard proposta={dados.proposta} />
          <PadroesCard padroes={dados.padroes} />
          <ApiCard api={dados.api} />
          <CompareCard politicas={dados.politicas} comparacao={dados.comparacao} sel={pol.id} onSel={setPolId} />
        </div>

        <footer className="page-foot">
          Política atual reproduzida em {pct(dados.reproducaoAtual, 0)} das decisões do histórico · banco Fortuna e API do bureau ·
          gerado por <code>site/scripts/snapshot.py</code>
        </footer>
      </main>
    </>
  );
}
