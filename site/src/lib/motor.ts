// Motor da Proposta no navegador: o mesmo cálculo de src/politica.py (politica_proposta) com o modelo corrigido de
// censura de src/cenarios.py. Explica cada pedido na Revisão e responde o simulador na hora.
// Modelo e parâmetros vêm de painel.modelo (supabase/publicar_motor.py), só para membros. A paridade com o Python
// (as 2.000 decisões, valores e motivos) é conferida em site/scripts/paridade-motor.mjs antes de publicar.
// Sem imports: o mesmo arquivo roda no Next e no Node (--experimental-strip-types).

export type Entrada = {
  valor_solicitado: number;
  prazo_meses: number;
  renda_declarada: number;
  tipo_vinculo: string;
  idade: number;
  meses_conta: number;
  score: number;
  restricoes_ativas: number;
  consultas_90_dias: number;
  meses_historico_bureau: number;
  parcelas_outras_instituicoes: number | null;
  mov_entradas_media: number | null;
  mov_salario_media: number | null;
  mov_saidas_media: number | null;
  mov_saldo_medio: number | null;
  mov_saldo_minimo_min: number | null;
  mov_dias_cheque_total: number | null;
  mov_meses_cheque: number | null;
  mov_entradas_cv: number | null;
  mov_meses_saida_maior_3m: number | null;
};

type Arvore = { f: number[]; t: number[]; e: number[]; d: number[]; m: number[]; v: number[]; folha: number[] };

export type Motor = {
  atributos: string[];
  base: number;
  arvores: Arvore[];
  politica: {
    min_score: number; max_restricoes: number; max_meses_negativos: number; max_comprometimento: number;
    risco_max: number; ganho_min: number; nega_conta_apertada_3m: boolean; teto_parcela_renda_real: number;
    r_atraso: number; ganho: number[]; fracoes: number[]; valor_min: number; valor_max: number; taxa: number;
  };
  tipico: Entrada;
  auc?: number;
  fonte?: string;
};

export type PontoCurva = {
  fracao: number;
  valor: number;
  risco: number;
  ganho: number;
  ok: boolean;
  porque: "mínimo" | "risco" | "ganho" | null;
};

export type Decisao = {
  aprova: boolean;
  valor: number;
  motivo: string;
  risco: number;
  ganho: number;
  lucro: number;
  prejuizo: number;
  solicitado: number;
  tetoRenda: number;
  barreiras: { restricao: boolean; apertada: boolean; pesada: boolean; negativos: boolean; score: boolean };
  restricoes: number;
  mesesApertada: number;
  parcelaRef: number;
  rendaReal: number;
  parcelaRendaReal: number;
  curva: PontoCurva[];
};

const num = (v: number | null | undefined) => (v == null ? NaN : v);

/** np.rint: no empate (.5) vai para o par, como o numpy. */
function rint(x: number) {
  const r = Math.round(x);
  return r - x === 0.5 && r % 2 !== 0 ? r - 1 : r;
}

/** Parcela da tabela Price arredondada a centavos (src/features.py, parcela_price). */
function parcelaPrice(valor: number, prazo: number, taxa: number) {
  return rint(((valor * taxa) / (1 - (1 + taxa) ** -prazo)) * 100) / 100;
}

/** Atributos do modelo para um valor concedido (src/modelo.py, atributos_para_valor), na ordem do treino. */
function atributos(x: Entrada, valor: number, m: Motor): number[] {
  const parc = parcelaPrice(valor, x.prazo_meses, m.politica.taxa);
  const renda = x.renda_declarada;
  const outras = num(x.parcelas_outras_instituicoes);
  const ent = num(x.mov_entradas_media);
  const a: Record<string, number> = {
    comp_aprov: parc / renda,
    comp_total_aprov: (parc + outras) / renda,
    comp_real_aprov: (parc + outras) / Math.max(ent, 1),
    prazo_meses: x.prazo_meses,
    valor_aprov_sobre_renda: valor / renda,
    score: x.score,
    restricoes_ativas: x.restricoes_ativas,
    consultas_90_dias: x.consultas_90_dias,
    meses_historico_bureau: x.meses_historico_bureau,
    parcelas_outras_instituicoes: outras,
    renda_declarada: renda,
    salario_sobre_renda: num(x.mov_salario_media) / renda,
    entradas_sobre_renda: ent / renda,
    sobra_mensal: ent - num(x.mov_saidas_media),
    mov_dias_cheque_total: num(x.mov_dias_cheque_total),
    mov_meses_cheque: num(x.mov_meses_cheque),
    mov_entradas_cv: num(x.mov_entradas_cv),
    mov_saldo_medio: num(x.mov_saldo_medio),
    mov_saldo_minimo_min: num(x.mov_saldo_minimo_min),
    meses_conta: x.meses_conta,
    idade: x.idade,
    vinc_autonomo: x.tipo_vinculo === "autonomo" ? 1 : 0,
    vinc_empresario: x.tipo_vinculo === "empresario" ? 1 : 0,
    vinc_aposentado: x.tipo_vinculo === "aposentado" ? 1 : 0,
  };
  return m.atributos.map((n) => {
    if (!(n in a)) throw new Error(`atributo desconhecido no modelo: ${n}`);
    return a[n];
  });
}

/** P(não pagar): soma das árvores sobre a previsão base e logística, como o HistGradientBoostingClassifier. */
export function risco(m: Motor, xs: number[]) {
  let raw = m.base;
  for (const a of m.arvores) {
    let i = 0;
    while (!a.folha[i]) {
      const v = xs[a.f[i]];
      i = Number.isNaN(v) ? (a.m[i] ? a.e[i] : a.d[i]) : v <= a.t[i] ? a.e[i] : a.d[i];
    }
    raw += a.v[i];
  }
  return 1 / (1 + Math.exp(-raw));
}

export function decidir(x: Entrada, m: Motor): Decisao {
  const p = m.politica;
  const prazo = x.prazo_meses;
  const renda = x.renda_declarada;
  const sol = Math.min(x.valor_solicitado, p.valor_max);
  const fator = 0.03 / (1 - 1.03 ** -prazo);
  const tetoRenda = Math.floor((p.max_comprometimento * renda) / fator / 100) * 100;
  const teto = Math.min(sol, tetoRenda);
  const [g0, g1, g2] = p.ganho;
  const R = p.r_atraso;

  let melhorValor = 0;
  let melhorGanho = 0;
  let melhorRisco = NaN;
  let melhorG = 0;
  const curva: PontoCurva[] = [];
  for (const f of p.fracoes) {
    let v = Math.min(rint((sol * f) / 100) * 100, teto);
    if (!(v >= p.valor_min)) v = 0;
    const pr = risco(m, atributos(x, v > 0 ? v : p.valor_min, m));
    const g = (1 - pr) * (1 - R) * g0 + (1 - pr) * R * g1 + pr * g2;
    const ok = v > 0 && pr <= p.risco_max && g > p.ganho_min;
    const ganho = ok ? v * g : 0;
    if (ganho > melhorGanho) {
      melhorValor = v;
      melhorGanho = ganho;
      melhorRisco = pr;
      melhorG = g;
    }
    if (Number.isNaN(melhorRisco)) melhorRisco = pr;
    if (!curva.some((c) => c.valor === v)) {
      curva.push({ fracao: f, valor: v, risco: pr, ganho: v * g, ok,
        porque: v === 0 ? "mínimo" : pr > p.risco_max ? "risco" : g <= p.ganho_min ? "ganho" : null });
    }
  }

  const ent = num(x.mov_entradas_media);
  const teto30 = (0.3 * renda * (1 - 1.03 ** -prazo)) / 0.03;
  const parcelaRef = (Math.min(x.valor_solicitado, teto30) * 0.03) / (1 - 1.03 ** -prazo);
  const rendaReal = Math.min(renda, Number.isNaN(ent) ? renda : ent);
  const parcelaRendaReal = parcelaRef / rendaReal;
  const mesesApertada = num(x.mov_meses_saida_maior_3m) || 0;
  const barreiras = {
    restricao: x.restricoes_ativas > p.max_restricoes,
    apertada: p.nega_conta_apertada_3m && mesesApertada > 0,
    pesada: p.teto_parcela_renda_real ? parcelaRendaReal > p.teto_parcela_renda_real : false,
    negativos: (num(x.mov_meses_cheque) || 0) > p.max_meses_negativos,
    score: x.score <= p.min_score,
  };

  let motivo = "aprovado";
  if (melhorValor === 0) motivo = "risco acima do limite ou ganho esperado negativo";
  if (teto < p.valor_min) motivo = "parcela mínima passa do teto de comprometimento";
  if (barreiras.negativos) motivo = "2+ meses com saldo negativo na conta";
  if (barreiras.score) motivo = `score até ${p.min_score}`;
  if (barreiras.pesada) motivo = "parcela acima de 28% da renda real";
  if (barreiras.apertada) motivo = "conta apertada: saídas > entradas nos últimos 3 meses";
  if (barreiras.restricao) motivo = "restrição ativa no bureau";
  const barrado = Object.values(barreiras).some(Boolean);
  const valor = barrado ? 0 : melhorValor;
  const prejuizo = valor > 0 ? valor * melhorRisco * -g2 : 0;

  return {
    aprova: valor > 0,
    valor,
    motivo,
    risco: melhorRisco,
    ganho: valor > 0 ? melhorGanho : 0,
    lucro: valor > 0 ? valor * melhorG + prejuizo : 0,
    prejuizo,
    solicitado: x.valor_solicitado,
    tetoRenda,
    barreiras,
    restricoes: x.restricoes_ativas,
    mesesApertada,
    parcelaRef,
    rendaReal,
    parcelaRendaReal,
    curva,
  };
}
