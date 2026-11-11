// Formato de src/data/dashboard.json, gerado por scripts/snapshot.py (só agregados).

export type Etapa = { rotulo: string; restantes: number };

export type Politica = {
  id: string;
  nome: string;
  funil: Etapa[];
  aprovados: number;
  volume: number;
  reduzidos: number;
  porVinculo: { vinculo: string; volume: number; pedidos: number }[];
  vsAtual?: {
    aprovaAMais: number;
    volumeAMais: number;
    negaAMais: number;
    volumeAMenos: number;
    valorMudou: number;
    iguais: number;
  };
};

export type Faixa = { faixa: string; n: number };

// Formato de src/data/historico.json, gerado por scripts/historico.py (só agregados).
export type BaseHist = {
  pedidos: number;
  periodo: string[];
  real: { aprovados: number; volume: number; resultado: number; calotes: number; taxa: number | null };
  proposta: {
    aprovados: number; comDesfecho: number; volume: number; resultado: number; calotes: number; taxa: number | null;
    novos: number; volumeNovos: number; resultadoNovos: number;
  };
  matriz: {
    fortuna: boolean; proposta: boolean; pedidos: number; volumeReal: number; volumeProposta: number;
    calotes: number | null; taxa: number | null;
  }[];
  ajustes: {
    id: string; rotulo: string; pedidos: number; calotes: number | null; taxa: number | null; pNaoPaga?: number | null;
    efeito: number; estimado: boolean;
  }[];
  meses: {
    mes: string; maduro: boolean; real: number; proposta: number; estimado: number;
    aprovadosReal: number; calotesReal: number; calotesProposta: number;
  }[];
};

export type DadosHistorico = {
  geradoEm: string;
  maduroAte: string;
  bases: { todos: BaseHist; maduros: BaseHist };
  estimativa: {
    contratos: number; calotes: number; aucModelo: number; aucScore: number;
    faixas: { faixa: string; pedidos: number; estimada: number; observada: number }[];
    ganhoEstimado: number; ganhoObservado: number; aprovadosProposta: number;
  };
  piloto: {
    aprovadosForaDaRegra: number; propostaAprova: number; taxaAprova: number | null;
    propostaNega: number; taxaNega: number | null;
  } | null;
};

export type Dados = {
  geradoEm: string;
  corte: string;
  reproducaoAtual: number;
  pedidos: {
    total: number;
    periodo: string[];
    porDiaSemana: { dia: string; n: number }[];
    mediaMensalHistorico: number;
    valorSolicitado: number;
    valorMediano: number;
    comContaApertada: number;
    parcelaAcima28Real: number;
  };
  politicas: Politica[];
  safras: {
    mediaMadura: number;
    contratosMaduros: number;
    meses: { mes: string; aprovados: number; inadimplentes: number; taxa: number; maduro: boolean }[];
  };
  bureau: {
    scoreMediano: number;
    scoreFaixas: Faixa[];
    comRestricao: number;
    consultas4mais: number;
    total: number;
  };
  api: {
    clientes: number;
    comBureau: number;
    chamadas: number;
    status: Record<string, number>;
    clientesComRetry: number;
    maxTentativas: number;
    latencia: { p50: number; p90: number; p95: number; p99: number; max: number; media: number } | null;
    histograma: Faixa[];
    desde: string | null;
    ate: string | null;
    config: { timeoutSeg: number; tentativas: number; esperaBaseSeg: number; paralelo: number };
  };
  padroes: {
    media: number | null;
    itens: { grupo: string; taxa: number; aprox: boolean; clientes: number; vsMedia: number; novos?: number }[];
    fonte: string;
    base?: number;
  };
  proposta: {
    passos: { titulo: string; texto: string; negados?: number; reduzidos?: number; divergentes?: number; laranja?: number }[];
    aprovados: number;
    volume: number;
    faixas: Record<string, number>;
  };
  comparacao: {
    id: string;
    nome: string;
    aprovados: number;
    volume: number;
    ganhoMin: number;
    ganhoMax: number;
    foraAmostra: number | null;
    calotesForaAmostra: number | null;
  }[];
};
