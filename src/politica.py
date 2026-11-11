"""Políticas de crédito: a atual da Fortuna e a proposta pelo time Spread."""
import numpy as np
import pandas as pd

from modelo import GANHO, probabilidades

VALOR_MIN, VALOR_MAX = 500.0, 30000.0
FRACOES = np.round(np.arange(1.0, 0.05, -0.05), 2)  # 100%, 95%, ... 10% do solicitado

# parâmetros ajustáveis pelo analista de risco
PARAMS = {
    "min_score": 0,               # sem corte de score: depois dos filtros, score <= 600 tem ~7% projetado, igual a > 600
    "max_restricoes": 0,         # filtro: restrição ativa nega
    "max_meses_negativos": 12,    # desligado (12 = nunca nega): conta apertada já pega esse risco e erra menos (analysis/pontuacao-risco.md)
    "max_comprometimento": 0.28,  # teto da parcela sobre a renda declarada; até 28% o risco é plano (analysis/pontuacao-risco.md)
    "risco_max": 0.175,           # P(não pagar) máxima no valor aprovado
    "ganho_min": 0.0,             # ganho esperado mínimo por real
    # filtros de cliente do Bilosca (src/politica_regras.py), que o modelo não captava sozinho:
    "nega_conta_apertada_3m": True,      # nega se saídas > entradas em algum dos 3 meses antes do pedido
    "teto_parcela_renda_real": 0.28,     # nega se a parcela do valor de referência passa de 28% da renda real
}


def filtros_cliente(x: pd.DataFrame, p: dict) -> tuple:
    """Filtros de cliente medidos como na política por regras: a parcela é a do valor que a política atual
    concederia (solicitado, limitado a 30% da renda declarada), e a renda real é a menor entre a declarada e as
    entradas médias da conta. No teste fora da amostra, os clientes que só esses filtros barram deram 42% de calote."""
    n = len(x)
    apertada = np.zeros(n, bool)
    if p.get("nega_conta_apertada_3m") and "mov_meses_saida_maior_3m" in x:
        apertada = x["mov_meses_saida_maior_3m"].fillna(0).to_numpy() > 0
    pesada = np.zeros(n, bool)
    if p.get("teto_parcela_renda_real") and "mov_entradas_media" in x:
        teto30 = 0.30 * x["renda_declarada"] * (1 - 1.03 ** (-x["prazo_meses"].astype(float))) / 0.03
        ref = np.minimum(x["valor_solicitado"], teto30)
        renda_real = np.minimum(x["renda_declarada"], x["mov_entradas_media"].fillna(x["renda_declarada"]))
        parc = ref * 0.03 / (1 - 1.03 ** (-x["prazo_meses"].astype(float)))
        pesada = (parc / renda_real).to_numpy() > p["teto_parcela_renda_real"]
    return apertada, pesada


def valor_max_parcela(renda, prazo, pct):
    fator = 0.03 / (1 - 1.03 ** (-np.asarray(prazo, dtype=float)))
    return np.floor(pct * np.asarray(renda, dtype=float) / fator / 100) * 100  # múltiplo de R$100 para baixo


def politica_atual(x: pd.DataFrame) -> pd.DataFrame:
    """Score > 600, renda > 2.000, sem restrição; valor reduzido até a parcela caber em 30% da renda."""
    passa = (x["score"] > 600) & (x["renda_declarada"] > 2000) & (x["restricoes_ativas"] == 0)
    teto = 0.30 * x["renda_declarada"] * (1 - 1.03 ** (-x["prazo_meses"].astype(float))) / 0.03
    valor = np.minimum(x["valor_solicitado"], np.floor(teto * 100) / 100)
    valor = np.where(passa, np.minimum(valor, VALOR_MAX), 0.0)
    return pd.DataFrame({"id_pedido": x["id_pedido"].values, "aprova": valor > 0, "valor": valor})


def politica_proposta(x: pd.DataFrame, modelo, params=None) -> pd.DataFrame:
    p = {**PARAMS, **(params or {})}
    x = x.reset_index(drop=True)
    sol = np.minimum(x["valor_solicitado"].to_numpy(float), VALOR_MAX)
    teto = np.minimum(sol, valor_max_parcela(x["renda_declarada"], x["prazo_meses"], p["max_comprometimento"]))

    melhor_valor = np.zeros(len(x)); melhor_ganho = np.zeros(len(x))
    melhor_prob = np.tile([np.nan] * 3, (len(x), 1))
    for f in FRACOES:
        v = np.minimum(np.round(sol * f, -2), teto)
        v = np.where(v >= VALOR_MIN, v, 0.0)
        prob = probabilidades(modelo, x, np.where(v > 0, v, VALOR_MIN))
        g_real = prob @ GANHO
        ok = (v > 0) & (prob[:, 2] <= p["risco_max"]) & (g_real > p["ganho_min"])
        ganho = np.where(ok, v * g_real, 0.0)
        troca = ganho > melhor_ganho
        melhor_valor = np.where(troca, v, melhor_valor)
        melhor_ganho = np.where(troca, ganho, melhor_ganho)
        melhor_prob[troca] = prob[troca]
        primeiro = np.isnan(melhor_prob[:, 0])
        melhor_prob[primeiro] = prob[primeiro]

    motivo = np.full(len(x), "aprovado", dtype=object)
    motivo[melhor_valor == 0] = "risco acima do limite ou ganho esperado negativo"
    motivo[teto < VALOR_MIN] = "parcela mínima passa do teto de comprometimento"
    neg = x["mov_meses_cheque"].fillna(0).to_numpy() > p["max_meses_negativos"]
    restr = x["restricoes_ativas"].to_numpy() > p["max_restricoes"]
    motivo[neg] = "2+ meses com saldo negativo na conta"
    score_baixo = x["score"].to_numpy() <= p["min_score"]
    motivo[score_baixo] = f"score até {p['min_score']}"
    apertada, pesada = filtros_cliente(x, p)
    motivo[pesada] = "parcela acima de 28% da renda real"
    motivo[apertada] = "conta apertada: saídas > entradas nos últimos 3 meses"
    motivo[restr] = "restrição ativa no bureau"
    valor = np.where(neg | restr | score_baixo | apertada | pesada, 0.0, melhor_valor)
    return pd.DataFrame({
        "id_pedido": x["id_pedido"], "aprova": valor > 0, "valor": valor,
        "p_em_dia": melhor_prob[:, 0].round(4), "p_atraso": melhor_prob[:, 1].round(4),
        "p_nao_paga": melhor_prob[:, 2].round(4), "ganho_esperado": np.where(valor > 0, melhor_ganho, 0).round(2),
        "motivo": motivo,
    })
