"""A política do time Spread, como função pura sobre a base de features.

Estratégia (decidida em analysis/para-discussao.md): partir da política atual e **só apertar**.
Aprovar quem a atual nega é a única direção que pode dar ganho negativo — e ganho negativo zera
40% da nota. Negar quem a atual aprova e não paga só pode melhorar.

Os dois filtros vêm de analysis/analise-enio.md, ambos conferidos em duas metades da base:
  - conta apertada: saídas > entradas em algum dos 3 meses antes do pedido -> 91% de calote
  - parcela pesada: acima de 28% da renda real (min entre declarada e entradas médias) -> 50%

PARAMS é o que o painel do analista mexe.
"""
import numpy as np
import pandas as pd

PARAMS = {
    "score_min": 600,
    "renda_min": 2000,
    "restricoes_max": 0,
    "teto_parcela_renda_declarada": 0.30,
    "nega_conta_apertada": True,
    "teto_parcela_renda_real": 0.28,
}


def parcela_price(valor, prazo, i=0.03):
    """Parcela da tabela Price: 3% ao mês (manual)."""
    return valor * i / (1 - (1 + i) ** (-prazo))


def valor_para_parcela(parcela, prazo, i=0.03):
    """Inverso da Price: maior valor cujo a parcela não passa de `parcela`."""
    return parcela * (1 - (1 + i) ** (-prazo)) / i


def renda_real(df: pd.DataFrame) -> pd.Series:
    """A menor entre a renda declarada e as entradas médias da conta.

    Quem não tem movimentação cai na renda declarada — não inventamos risco por falta de dado.
    """
    return np.minimum(df.renda_declarada, df.ent_media.fillna(df.renda_declarada))


def atual(df: pd.DataFrame, p: dict = PARAMS) -> pd.DataFrame:
    """A política atual da Fortuna: o piso contra o qual a nota é medida."""
    aprova = ((df.score > p["score_min"])
              & (df.renda_declarada > p["renda_min"])
              & (df.restricoes_ativas <= p["restricoes_max"]))
    teto = valor_para_parcela(df.renda_declarada * p["teto_parcela_renda_declarada"], df.prazo_meses)
    valor = np.minimum(df.valor_solicitado, teto).round(2)
    return pd.DataFrame({"decisao": np.where(aprova, "APROVADO", "NEGADO"),
                         "valor_aprovado": np.where(aprova, valor, 0.0)}, index=df.index)


def spread(df: pd.DataFrame, p: dict = PARAMS) -> pd.DataFrame:
    """A política do time: a atual, mais os dois filtros de risco."""
    r = atual(df, p)
    aprova = r.decisao == "APROVADO"

    if p["nega_conta_apertada"]:
        aprova &= ~(df.meses_saida_maior_3m.fillna(0) > 0)

    parcela = parcela_price(r.valor_aprovado, df.prazo_meses)
    aprova &= (parcela / renda_real(df)) <= p["teto_parcela_renda_real"]

    return pd.DataFrame({"decisao": np.where(aprova, "APROVADO", "NEGADO"),
                         "valor_aprovado": np.where(aprova, r.valor_aprovado, 0.0).round(2)},
                        index=df.index)


POLITICAS = {"atual": atual, "spread": spread}
