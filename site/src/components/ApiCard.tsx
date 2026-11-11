"use client";

import { dataHora, int, pct, segundos } from "@/lib/format";
import type { Dados } from "@/lib/types";
import { LivePing } from "./LivePing";
import { ChartCard, useTip, vars } from "./ui";

export function ApiCard({ api }: { api: Dados["api"] }) {
  const { box, bind, node } = useTip();
  const s503 = api.status["503"] ?? 0;
  const max = Math.max(1, ...api.histograma.map((h) => h.n));
  const lat = api.latencia;
  const c = api.config;

  return (
    <ChartCard
      title="API do bureau"
      area="api"
      actions={<LivePing />}
      table={
        <table className="dtable">
          <thead><tr><th>Tempo de resposta</th><th>Chamadas</th><th>% das chamadas</th></tr></thead>
          <tbody>
            {api.histograma.map((h) => (
              <tr key={h.faixa}><th scope="row">{h.faixa}</th><td>{int(h.n)}</td><td>{pct(h.n / api.chamadas)}</td></tr>
            ))}
          </tbody>
        </table>
      }
    >
      <div className="api-layout">
        <div className="api-main">
          <div>
            <span className="hero">{int(api.comBureau)}</span>
            <span className="hero-of"> / {int(api.clientes)}</span>
            <p className="muted">clientes consultados{api.comBureau === api.clientes ? ", nenhum sem resposta" : ""}</p>
          </div>
          <dl className="stats">
            <div><dt>Chamadas</dt><dd>{int(api.chamadas)}</dd></div>
            <div><dt>Respostas 503</dt><dd>{int(s503)} <small>{pct(s503 / Math.max(1, api.chamadas))}</small></dd></div>
            <div><dt>Recuperados no retry</dt><dd>{int(api.clientesComRetry)} <small>até {api.maxTentativas} tentativas</small></dd></div>
            {lat && <div><dt>Latência p50 · p95</dt><dd>{segundos(lat.p50)} <small>· {segundos(lat.p95)}</small></dd></div>}
          </dl>
        </div>

        <div className="lat" ref={box}>
          <span className="muted">Tempo de resposta por chamada</span>
          <div className="lat-plot" style={vars({ "--n": api.histograma.length })}>
            {api.histograma.map((h) => (
              <div key={h.faixa} className="lat-col sl" {...bind(<><b>{h.faixa}</b> · {int(h.n)} chamadas · {pct(h.n / api.chamadas)}</>, `${h.faixa}: ${int(h.n)} chamadas`)}>
                <div className="lat-bar" style={vars({ "--p": h.n / max })} />
              </div>
            ))}
          </div>
          <div className="lat-x" style={vars({ "--n": api.histograma.length })} aria-hidden>
            {api.histograma.map((h) => <span key={h.faixa}>{h.faixa.replace(" s", "")}</span>)}
          </div>
          {node}
        </div>
      </div>

      <p className="foot">
        Quando o bureau falha, a consulta é repetida até {c.tentativas} vezes, esperando um pouco mais a cada tentativa
        {api.ate && <> · última consulta {dataHora(api.ate)}</>}.
      </p>
    </ChartCard>
  );
}
