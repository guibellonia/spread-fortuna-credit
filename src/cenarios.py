"""Resultado esperado de longo prazo (vida inteira do contrato) de cada política nos 2.000 pedidos novos.

Risco estimado por um modelo corrigido para censura (mesmo método de analysis/censura-agregado.md):
o calote só aparece até ~2/3 do prazo; um contrato não inadimplente observado numa fração w dessa janela
entra no treino com peso w. Inadimplente entra com peso 1.
Ganho por real: +15% em dia, +5% com atraso, -60% não paga. Fração de pagadores com atraso: R_ATRASO.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from db import consulta
from modelo import SAIDA, atributos_para_valor, carregar
from politica import politica_atual, politica_proposta

R_ATRASO = 0.23


def pesos_censura(ap: pd.DataFrame) -> pd.Series:
    p = consulta("""SELECT id_pedido, count(*) FILTER (WHERE data_vencimento <= '2026-09-30') decididas
                    FROM hackathon.parcelas GROUP BY 1""")
    ap = ap.merge(p, on="id_pedido", how="left")
    janela = np.ceil(ap["prazo_meses"] * 2 / 3)
    w = (np.minimum(ap["decididas"].fillna(0), janela) / janela).clip(0, 1)
    w = np.where(ap["situacao_final"] == "inadimplente", 1.0, w)
    return pd.Series(w, index=ap.index), ap


def treinar_corrigido(hist):
    ap = hist[hist.decisao == "aprovado"].reset_index(drop=True)
    w, ap = pesos_censura(ap)
    X = atributos_para_valor(ap, ap["valor_aprovado"])
    y = (ap["situacao_final"] == "inadimplente").astype(int)
    ok = w > 0
    cfg = dict(max_iter=300, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=40,
               l2_regularization=1.0, random_state=42)
    tr = (ap["data_pedido"] <= "2025-09-30") & ok
    te = (ap["data_pedido"] > "2025-09-30") & ok
    m = HistGradientBoostingClassifier(**cfg).fit(X[tr], y[tr], sample_weight=w[tr])
    auc = roc_auc_score(y[te], m.predict_proba(X[te])[:, 1], sample_weight=w[te])
    final = HistGradientBoostingClassifier(**cfg).fit(X[ok], y[ok], sample_weight=w[ok])
    proj = y[ok].sum() / w[ok].sum()
    prev = (final.predict_proba(X[ok])[:, 1] * w[ok]).sum() / w[ok].sum()
    return final, {"auc": round(auc, 3), "inad_projetada_base": round(float(proj), 4),
                   "inad_media_modelo": round(float(prev), 4)}


def resultado(dec, x, m, fator=1.0):
    d = dec.merge(x, on="id_pedido")
    d = d[d["valor"] > 0]
    if d.empty:
        return dict(aprovados=0, volume=0, inad_esperada=0, resultado=0)
    p = np.clip(m.predict_proba(atributos_para_valor(d, d["valor"]))[:, 1] * fator, 0, 1)
    g = 0.15 * (1 - p) * (1 - R_ATRASO) + 0.05 * (1 - p) * R_ATRASO - 0.60 * p
    return dict(aprovados=len(d), volume=round(d["valor"].sum()),
                inad_esperada=round(float((p * d["valor"]).sum() / d["valor"].sum()), 4),
                resultado=round(float((g * d["valor"]).sum())))


def main():
    hist = pd.read_pickle(SAIDA / "hist.pkl")
    x = pd.read_pickle(SAIDA / "novos.pkl")
    m, meta = treinar_corrigido(hist)
    print("modelo corrigido:", meta)
    antigo = carregar()

    x = x.copy()
    x["r_saidas"] = x["mov_saidas_media"] / x["mov_entradas_media"]
    extra = (x["r_saidas"] >= 0.8) | (x["entradas_sobre_renda"] < 0.6)

    def com_filtros(dec):
        dec = dec.copy()
        bloq = dec["id_pedido"].isin(x.loc[extra, "id_pedido"])
        dec.loc[bloq, ["aprova", "valor"]] = [False, 0.0]
        return dec

    cen = {
        "A. Política atual": politica_atual(x),
        "B. Proposta v1 (sem corte de score)": politica_proposta(x, antigo, {"min_score": 0, "risco_max": 0.20}),
        "C. Proposta v2 (score > 600)": politica_proposta(x, antigo, {"min_score": 600, "risco_max": 0.20}),
        "D. v2 + filtros saídas>=80% e renda real<60%": com_filtros(politica_proposta(x, antigo, {"min_score": 600, "risco_max": 0.20})),
        "E. v2 com modelo corrigido, risco <= 17,5%": politica_proposta(x, m_wrap(m), {"risco_max": 0.175, "min_score": 600}),
        "G. corrigido, risco <= 17,5%, sem score (CSV de entrega)": politica_proposta(x, m_wrap(m), {"risco_max": 0.175, "min_score": 0}),
        "H. G com corte de score em 500": politica_proposta(x, m_wrap(m), {"risco_max": 0.175, "min_score": 499}),
        "F. E + filtros novos": com_filtros(politica_proposta(x, m_wrap(m), {"risco_max": 0.175, "min_score": 600})),
    }
    linhas = []
    for nome, dec in cen.items():
        base = resultado(dec, x, m)
        lin = {"cenario": nome, **base,
               "pessimista(+20% risco)": resultado(dec, x, m, 1.2)["resultado"],
               "otimista(-20% risco)": resultado(dec, x, m, 0.8)["resultado"]}
        linhas.append(lin)
    df = pd.DataFrame(linhas)
    atual = df.loc[0, "resultado"]
    df["ganho_vs_atual"] = df["resultado"] - atual
    pd.set_option("display.width", 250)
    print(df.to_string(index=False))
    df.to_csv(SAIDA / "cenarios.csv", index=False, encoding="utf-8")


class m_wrap:
    """Adapta o modelo binário corrigido para a interface de 3 classes usada em politica_proposta."""
    def __init__(self, m):
        self.m = m

    def predict_proba(self, X):
        p = self.m.predict_proba(X)[:, 1]
        return np.column_stack([(1 - p) * (1 - R_ATRASO), (1 - p) * R_ATRASO, p])


if __name__ == "__main__":
    main()
