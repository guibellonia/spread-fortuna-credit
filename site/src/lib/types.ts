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
    itens: { grupo: string; taxa: number; aprox: boolean; clientes: number; vsMedia: number }[];
    fonte: string;
  };
};
