"use client";

import { useState, type ReactNode } from "react";
import { brl, moeda, pct } from "@/lib/format";
import { decidir, type Decisao, type Entrada, type Motor } from "@/lib/motor";
import { IconButton, IconChart, IconTable, useTip, vars } from "./ui";

const ROTULO_RUIM: Record<string, string> = {
  risco: "risco acima do limite",
  ganho: "ganho esperado negativo",
  "mínimo": "abaixo de R$ 500",
};

/** Por que a IA aprovou ou negou: cada passo da política com o valor medido contra o limite, e a escolha do valor. */
export function PorQue({ motor, entrada, publicada }: {
  motor: Motor; entrada: Entrada; publicada?: { aprova: boolean; valor: number };
}) {
  const d = decidir(entrada, motor);
  const p = motor.politica;
  const barrado = d.barreiras.restricao || d.barreiras.apertada || d.barreiras.pesada || d.barreiras.negativos || d.barreiras.score;
  const difere = publicada && (publicada.aprova !== d.aprova || Math.abs(publicada.valor - d.valor) > 0.005);

  return (
    <div className="pq">
      <div className="pq-head">
        <span className={`selo ${d.aprova ? "is-ok" : "is-no"}`}>{d.aprova ? `Sugere aprovar · ${moeda(d.valor)}` : "Sugere negar"}</span>
        <span className="pq-frase">{frase(d)}</span>
      </div>
      {difere && (
        <p className="erro">
          O cálculo de agora deu {d.aprova ? moeda(d.valor) : "negado"} e a decisão registrada é{" "}
          {publicada.aprova ? moeda(publicada.valor) : "negado"}. Avise quem administra o painel.
        </p>
      )}

      <ol className="pq-passos">
        <Passo n={1} titulo="Restrição ativa no bureau" ok={!d.barreiras.restricao}
          medido={`${d.restricoes} ${d.restricoes === 1 ? "restrição" : "restrições"}`} limite="nenhuma" />
        <Passo n={2} titulo="Conta apertada nos 3 meses antes do pedido" ok={!d.barreiras.apertada}
          medido={`${d.mesesApertada} de 3 meses com saídas maiores que entradas`} limite="nenhum mês" />
        <Passo n={3} titulo="Parcela sobre a renda real" ok={!d.barreiras.pesada}
          medido={pct(d.parcelaRendaReal)} limite={`até ${pct(p.teto_parcela_renda_real, 0)}`}
          medida={{ valor: d.parcelaRendaReal, limite: p.teto_parcela_renda_real }}
          detalhe={`parcela de ${moeda(d.parcelaRef)} sobre renda real de ${moeda(d.rendaReal)} (a menor entre a declarada e as entradas da conta)`} />
        <Passo n={4} titulo="Risco de não pagar no valor escolhido" ok={!barrado ? d.valor > 0 : null}
          medido={pct(d.risco)} limite={`até ${pct(p.risco_max)} e ganho positivo`}
          medida={{ valor: d.risco, limite: p.risco_max }}
          detalhe={barrado ? "Não conta: uma barreira já negou o pedido." : "Estimado pela IA a partir dos empréstimos passados."} />
        <Passo n={5} titulo="Valor" ok={!barrado && d.valor > 0 ? true : null}
          medido={d.valor > 0 ? `${moeda(d.valor)} de ${moeda(d.solicitado)}` : "—"}
          limite={`parcela até ${pct(p.max_comprometimento, 0)} da renda declarada: até ${moeda(d.tetoRenda)}`}
          detalhe={d.valor > 0 && d.valor < d.solicitado ? "Reduzido para o valor de maior ganho esperado dentro dos limites." : undefined} />
      </ol>

      {barrado ? (
        <p className="muted">O modelo nem escolhe o valor: a barreira nega antes.</p>
      ) : (
        <Curva d={d} riscoMax={p.risco_max} />
      )}

      {d.aprova && (
        <dl className="stats pq-res">
          <div><dt>Lucro esperado</dt><dd>+{moeda(d.lucro)}</dd></div>
          <div><dt>Prejuízo esperado</dt><dd>−{moeda(d.prejuizo)}</dd></div>
          <div><dt>Resultado esperado</dt><dd>{moeda(d.ganho)}</dd></div>
        </dl>
      )}
    </div>
  );
}

export function frase(d: Decisao) {
  if (d.barreiras.restricao) return "Negado na primeira barreira: o bureau mostra restrição ativa.";
  if (d.barreiras.apertada) return "Negado: a conta teve saídas maiores que as entradas antes do pedido.";
  if (d.barreiras.pesada) return "Negado: a parcela pesa demais sobre a renda que de fato entra na conta.";
  if (!d.aprova) return "Passou nas barreiras, mas nenhum valor tem risco aceitável com ganho positivo.";
  if (d.valor < d.solicitado) return "Aprovado com valor menor: é onde o ganho esperado é maior dentro dos limites.";
  return "Aprovado no valor pedido: passou em todas as barreiras e o risco está dentro do limite.";
}

function Passo({ n, titulo, ok, medido, limite, detalhe, medida }: {
  n: number; titulo: string; ok: boolean | null; medido: string; limite: string; detalhe?: string;
  medida?: { valor: number; limite: number };
}) {
  const estado = ok === null ? "is-skip" : ok ? "is-ok" : "is-no";
  const topo = medida ? Math.max(medida.limite * 2, medida.valor * 1.1) : 1;
  return (
    <li className={`pq-passo ${estado}`}>
      <span className="pq-ic" aria-label={ok === null ? "não avaliado" : ok ? "passou" : "barrou"}>
        {ok === null ? n : ok ? "✓" : "✕"}
      </span>
      <div className="pq-corpo">
        <div className="pq-linha">
          <span className="pq-titulo">{titulo}</span>
          <span className="pq-medido">{medido}</span>
        </div>
        {medida && (
          <div className="pq-gauge" role="img" aria-label={`${medido}, limite ${limite}`}>
            <div className="pq-fill" style={vars({ "--p": Math.min(medida.valor / topo, 1) })} />
            <i style={vars({ "--p": medida.limite / topo })} />
          </div>
        )}
        <div className="pq-sub">Limite: {limite}{detalhe ? ` · ${detalhe}` : ""}</div>
      </div>
    </li>
  );
}

/** Ganho esperado de cada valor que a política testa (100% a 10% do pedido); fica o maior entre os aceitáveis. */
function Curva({ d, riscoMax }: { d: Decisao; riscoMax: number }) {
  const { box, bind, node } = useTip();
  const [tabela, setTabela] = useState(false);
  const pts = d.curva.filter((c) => c.valor > 0).sort((a, b) => a.valor - b.valor);
  if (!pts.length) return <p className="muted">O pedido fica abaixo do mínimo de R$ 500 com a parcela até 28% da renda.</p>;
  const pos = Math.max(0, ...pts.map((c) => c.ganho));
  const neg = Math.max(0, ...pts.map((c) => -c.ganho));
  const escala = pos + neg || 1;
  const z = neg / escala;
  const cor = (c: (typeof pts)[number]) => (c.ok ? "" : c.porque === "risco" ? " is-risco" : " is-neg");
  const tip = (c: (typeof pts)[number]): ReactNode => (
    <><b>{moeda(c.valor)}</b> · risco {pct(c.risco)} · ganho {moeda(c.ganho)}{c.porque ? ` · ${ROTULO_RUIM[c.porque]}` : ""}</>
  );

  return (
    <div className="pq-curva">
      <div className="linha">
        <h3 className="pq-h3">Quanto emprestar: ganho esperado de cada valor</h3>
        <IconButton label={tabela ? "Ver gráfico" : "Ver tabela"} onClick={() => setTabela(!tabela)}>
          {tabela ? <IconChart /> : <IconTable />}
        </IconButton>
      </div>
      {tabela ? (
        <div className="table-wrap">
          <table className="dtable">
            <thead><tr><th>Valor</th><th>Risco</th><th>Ganho esperado</th><th>Situação</th></tr></thead>
            <tbody>
              {pts.map((c) => (
                <tr key={c.valor}>
                  <th scope="row">{moeda(c.valor)}{c.valor === d.valor ? " ✓" : ""}</th>
                  <td>{pct(c.risco)}</td>
                  <td>{moeda(c.ganho)}</td>
                  <td>{c.ok ? (c.valor === d.valor ? "escolhido" : "aceitável") : ROTULO_RUIM[c.porque ?? "risco"]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="pq-plot-box" ref={box}>
          <div className="pq-plot" style={vars({ "--n": pts.length })}>
            <div className="mes-zero" style={vars({ "--z": z })} aria-hidden />
            {pts.map((c) => (
              <div key={c.valor} className={`pq-col sl${c.valor === d.valor && d.aprova ? " is-esc" : ""}`}
                {...bind(tip(c), `${moeda(c.valor)}: risco ${pct(c.risco)}, ganho ${moeda(c.ganho)}`)}>
                <div className={`pq-bar${c.ganho < 0 ? " is-baixo" : ""}${cor(c)}`}
                  style={vars({ "--b": c.ganho >= 0 ? z : z - -c.ganho / escala, "--h": Math.abs(c.ganho) / escala })} />
              </div>
            ))}
          </div>
          <div className="pq-x" aria-hidden>
            <span>{brl(pts[0].valor)}</span>
            <span>{brl(pts[pts.length - 1].valor)}</span>
          </div>
          {node}
        </div>
      )}
      <ul className="legend">
        <li><i className="sw is-mature" />aceitável</li>
        <li><i className="sw is-risco" />risco acima de {pct(riscoMax)}</li>
        <li><i className="sw is-neg" />ganho negativo</li>
        {d.aprova && <li><i className="sw is-esc" />escolhido</li>}
      </ul>
    </div>
  );
}
