"""Modelo de risco: estima P(paga em dia), P(paga com atraso), P(não paga) para um valor aprovado."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from features import parcela_price

SAIDA = Path(__file__).resolve().parents[1] / "saida"
DATA_MATURIDADE = "2026-03-31"  # pedidos com 6+ meses até o corte: desfecho já observável

ATRIBUTOS = [
    "comp_aprov", "comp_total_aprov", "comp_real_aprov", "prazo_meses", "valor_aprov_sobre_renda",
    "score", "restricoes_ativas", "consultas_90_dias", "meses_historico_bureau", "parcelas_outras_instituicoes",
    "renda_declarada", "salario_sobre_renda", "entradas_sobre_renda", "sobra_mensal",
    "mov_dias_cheque_total", "mov_meses_cheque", "mov_entradas_cv", "mov_saldo_medio", "mov_saldo_minimo_min",
    "meses_conta", "idade", "vinc_autonomo", "vinc_empresario", "vinc_aposentado",
]
GANHO = np.array([0.15, 0.05, -0.60])  # em dia, atraso, não pagou
CLASSES = {"quitado_em_dia": 0, "em_dia": 0, "quitado_com_atraso": 1, "em_atraso": 1, "inadimplente": 2}


def atributos_para_valor(x: pd.DataFrame, valor) -> pd.DataFrame:
    """Recalcula os atributos que dependem do valor concedido."""
    f = x.copy()
    valor = np.asarray(valor, dtype=float)
    parc = parcela_price(valor, f["prazo_meses"])
    f["comp_aprov"] = parc / f["renda_declarada"]
    f["comp_total_aprov"] = (parc + f["parcelas_outras_instituicoes"]) / f["renda_declarada"]
    f["comp_real_aprov"] = (parc + f["parcelas_outras_instituicoes"]) / f["mov_entradas_media"].clip(lower=1)
    f["valor_aprov_sobre_renda"] = valor / f["renda_declarada"]
    for v in ["autonomo", "empresario", "aposentado"]:
        f[f"vinc_{v}"] = (f["tipo_vinculo"] == v).astype(int)
    return f[ATRIBUTOS]


def base_treino(hist: pd.DataFrame, ate=DATA_MATURIDADE):
    ap = hist[(hist.decisao == "aprovado") & (hist.data_pedido <= ate)].copy()
    X = atributos_para_valor(ap, ap["valor_aprovado"])
    y = ap["situacao_final"].map(CLASSES).astype(int)
    return ap, X, y


def novo_modelo():
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.04, max_leaf_nodes=15,
                                          min_samples_leaf=40, l2_regularization=1.0, random_state=42)


def treinar(hist: pd.DataFrame):
    ap, X, y = base_treino(hist)
    # validação temporal: treina até set/2025, testa out/2025–mar/2026
    corte = ap["data_pedido"] <= "2025-09-30"
    m = novo_modelo().fit(X[corte], y[corte])
    p = m.predict_proba(X[~corte])
    auc = roc_auc_score((y[~corte] == 2).astype(int), p[:, 2])
    final = novo_modelo().fit(X, y)
    SAIDA.mkdir(exist_ok=True)
    joblib.dump(final, SAIDA / "modelo.joblib")
    meta = {"auc_inadimplencia_validacao_temporal": round(float(auc), 3), "n_treino": int(len(X)),
            "taxa_inadimplencia_treino": round(float((y == 2).mean()), 4)}
    (SAIDA / "modelo_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return final, meta


def carregar():
    return joblib.load(SAIDA / "modelo.joblib")


def probabilidades(modelo, x: pd.DataFrame, valor) -> np.ndarray:
    return modelo.predict_proba(atributos_para_valor(x, valor))


def ganho_esperado(prob: np.ndarray) -> np.ndarray:
    """Ganho esperado por real aprovado."""
    return prob @ GANHO
