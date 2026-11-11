"use client";

import { useRef, type KeyboardEvent } from "react";
import { pct } from "@/lib/format";
import { decidir, type Entrada, type Motor } from "@/lib/motor";

export type Modo = "digitar" | "deslizar";
type Chave = keyof Entrada;
type Campo = { k: Chave; rotulo: string; opcional?: boolean };

const MODOS: [Modo, string][] = [["digitar", "Digitar"], ["deslizar", "Deslizar"]];

/** Abas "Digitar | Deslizar": a vista atual continua intacta; a outra mexe nos mesmos campos. */
export function SeletorModo({ modo, aoMudar }: { modo: Modo; aoMudar: (m: Modo) => void }) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  function teclas(ev: KeyboardEvent) {
    const i = MODOS.findIndex(([m]) => m === modo);
    const j = ev.key === "ArrowRight" ? (i + 1) % MODOS.length : ev.key === "ArrowLeft" ? (i + MODOS.length - 1) % MODOS.length
      : ev.key === "Home" ? 0 : ev.key === "End" ? MODOS.length - 1 : -1;
    if (j < 0) return;
    ev.preventDefault();
    aoMudar(MODOS[j][0]);
    refs.current[MODOS[j][0]]?.focus();
  }
  return (
    <div className="sim-modos" role="tablist" aria-label="Como preencher o simulador" onKeyDown={teclas}>
      {MODOS.map(([m, nome]) => (
        <button key={m} type="button" role="tab" id={`sim-aba-${m}`} aria-selected={modo === m} aria-controls="sim-painel"
          tabIndex={modo === m ? 0 : -1} className="sim-modo" ref={(el) => { refs.current[m] = el; }} onClick={() => aoMudar(m)}>
          {nome}
        </button>
      ))}
    </div>
  );
}

/** Faixa fixa no rodapé do celular: o resultado continua à vista enquanto o dedo arrasta. */
export function ResumoFixo({ motor, entrada }: { motor: Motor; entrada: Entrada | null }) {
  if (!entrada) return <div className="sd-resumo" aria-hidden="true"><span className="muted">Confira os campos</span></div>;
  const d = decidir(entrada, motor);
  const reais = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  return (
    <div className="sd-resumo" aria-hidden="true">
      <span className={`selo ${d.aprova ? "is-ok" : "is-no"}`}>{d.aprova ? `Aprovado · ${reais.format(d.valor)}` : "Negado"}</span>
      <span className="muted">{d.aprova ? `risco ${pct(d.risco, 1)}` : d.motivo}</span>
    </div>
  );
}

const REAIS = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const R = (v: number) => REAIS.format(v);
const N = new Intl.NumberFormat("pt-BR");
const plural = (v: number, um: string, varios: string) => `${N.format(v)} ${Math.abs(v) === 1 ? um : varios}`;

type Faixa = { min: number; max: number; passo: number; fmt: (v: number) => string };

/** Faixas dos controles. Valor e prazo vêm dos limites da política; os demais, de limites de bom senso para o pedido
 *  de crédito. Se o pedido carregado passar do limite, a faixa se estende para caber nele. */
function faixas(motor: Motor): Partial<Record<Chave, Faixa>> {
  const p = motor.politica;
  return {
    valor_solicitado: { min: p.valor_min, max: p.valor_max, passo: 100, fmt: R },
    renda_declarada: { min: 500, max: 30000, passo: 100, fmt: R },
    idade: { min: 18, max: 85, passo: 1, fmt: (v) => plural(v, "ano", "anos") },
    meses_conta: { min: 0, max: 240, passo: 1, fmt: (v) => plural(v, "mês", "meses") },
    score: { min: 0, max: 1000, passo: 10, fmt: (v) => N.format(v) },
    restricoes_ativas: { min: 0, max: 5, passo: 1, fmt: (v) => (v === 0 ? "Nenhuma" : plural(v, "restrição", "restrições")) },
    consultas_90_dias: { min: 0, max: 15, passo: 1, fmt: (v) => plural(v, "consulta", "consultas") },
    meses_historico_bureau: { min: 0, max: 240, passo: 1, fmt: (v) => plural(v, "mês", "meses") },
    parcelas_outras_instituicoes: { min: 0, max: 5000, passo: 50, fmt: R },
    mov_entradas_media: { min: 0, max: 30000, passo: 100, fmt: R },
    mov_salario_media: { min: 0, max: 30000, passo: 100, fmt: R },
    mov_saidas_media: { min: 0, max: 30000, passo: 100, fmt: R },
    mov_saldo_medio: { min: -10000, max: 50000, passo: 100, fmt: R },
    mov_saldo_minimo_min: { min: -10000, max: 30000, passo: 100, fmt: R },
    mov_dias_cheque_total: { min: 0, max: 365, passo: 1, fmt: (v) => plural(v, "dia", "dias") },
    mov_meses_cheque: { min: 0, max: 12, passo: 1, fmt: (v) => plural(v, "mês", "meses") },
    mov_entradas_cv: { min: 0, max: 1, passo: 0.01, fmt: (v) => pct(v, 0) },
    mov_meses_saida_maior_3m: { min: 0, max: 3, passo: 1, fmt: (v) => plural(v, "mês", "meses") },
  };
}

/** Um controle: rótulo, valor grande ao lado e o arrastar embaixo. `valor` nulo = campo vazio (só nos opcionais). */
function Controle({ id, rotulo, valor, texto, min, max, passo, minRot, maxRot, aoMudar, aoLimpar }: {
  id: string; rotulo: string; valor: number | null; texto: string; min: number; max: number; passo: number;
  minRot: string; maxRot: string; aoMudar: (v: number) => void; aoLimpar?: () => void;
}) {
  const p = valor == null ? 0 : Math.min(1, Math.max(0, (valor - min) / (max - min)));
  return (
    <div className={`sd-campo${valor == null ? " is-vazio" : ""}`}>
      <div className="sd-linha">
        <label htmlFor={id} className="sd-rotulo">{rotulo}</label>
        <output htmlFor={id} className="sd-valor">{texto}</output>
      </div>
      <input id={id} type="range" className="sd-range" min={min} max={max} step={passo} value={valor ?? min}
        style={{ ["--p" as string]: `${p * 100}%` }} aria-valuetext={texto}
        onChange={(ev) => aoMudar(Number(ev.target.value))} />
      <div className="sd-pontas">
        <span>{minRot}</span>
        {aoLimpar && valor != null ? <button type="button" className="sd-limpar" onClick={aoLimpar}>Sem dado</button> : null}
        <span>{maxRot}</span>
      </div>
    </div>
  );
}

/** Vista "Deslizar": os mesmos campos da vista "Digitar" (mesmo formulário, mesma conta), cada um como controle. */
export function Deslizadores({ motor, grupos, form, prazos, vinculos, numero, aoMudar }: {
  motor: Motor; grupos: [string, Campo[]][]; form: Record<string, string>; prazos: number[]; vinculos: [string, string][];
  numero: (s: string) => number | null; aoMudar: (k: Chave, v: string) => void;
}) {
  const F = faixas(motor);
  const grava = (k: Chave, v: number) => aoMudar(k, String(Math.round(v * 100) / 100).replace(".", ","));
  return (
    <>
      {grupos.map(([grupo, campos]) => (
        <fieldset key={grupo} className="sim-grupo sd-grupo">
          <legend>{grupo}</legend>
          {campos.filter(({ k }) => k !== "idade" || motor.atributos.includes("idade")).map(({ k, rotulo, opcional }) => {
            if (k === "tipo_vinculo") {
              return (
                <div key={k} className="sd-campo">
                  <span className="sd-rotulo" id="sd-vinculo">{rotulo}</span>
                  <div className="chips" role="radiogroup" aria-labelledby="sd-vinculo">
                    {vinculos.map(([id, nome]) => (
                      <button key={id} type="button" role="radio" aria-checked={form[k] === id} className="chip-btn sl"
                        onClick={() => aoMudar(k, id)}>{nome}</button>
                    ))}
                  </div>
                </div>
              );
            }
            if (k === "prazo_meses") {
              const atual = numero(form[k]);
              const i = atual == null || Number.isNaN(atual) ? -1 : prazos.indexOf(atual);
              return (
                <Controle key={k} id={`sd-${k}`} rotulo={rotulo.replace(" (meses)", "")} valor={i < 0 ? null : i}
                  texto={i < 0 ? "—" : `${prazos[i]} meses`} min={0} max={prazos.length - 1} passo={1}
                  minRot={`${prazos[0]} meses`} maxRot={`${prazos[prazos.length - 1]} meses`}
                  aoMudar={(v) => aoMudar(k, String(prazos[v]))} />
              );
            }
            const f = F[k];
            if (!f) return null;
            const atual = numero(form[k] ?? "");
            const valor = atual == null || Number.isNaN(atual) ? null : atual;
            const min = valor != null ? Math.min(f.min, valor) : f.min;
            const max = valor != null ? Math.max(f.max, valor) : f.max;
            return (
              <Controle key={k} id={`sd-${k}`} rotulo={rotulo.replace(/ \((R\$[^)]*|anos|meses|0,09 = 9%)\)$/, "")} valor={valor}
                texto={valor == null ? "Sem dado" : f.fmt(valor)} min={min} max={max} passo={f.passo}
                minRot={f.fmt(min)} maxRot={f.fmt(max)} aoMudar={(v) => grava(k, v)}
                aoLimpar={opcional ? () => aoMudar(k, "") : undefined} />
            );
          })}
        </fieldset>
      ))}
      <p className="foot">Arraste para ajustar. Nos campos da conta, “Sem dado” deixa o valor vazio, como um cliente sem movimentação.</p>
    </>
  );
}
