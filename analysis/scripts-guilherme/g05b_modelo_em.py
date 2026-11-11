"""Etapa 6 (modelo principal) · PD de vida inteira por EM com censura, usando a estrutura da base:
a parada cai (aprox.) uniforme entre a 1ª parcela e J = ceil(2/3 do prazo) (analysis/censura-agregado.md).

Para um contrato não parado observado numa fração w da janela:
  P(vai parar | não parou até w) = p (1-w) / (1 - p w)          (rótulo suave, passo E)
Passo M: classificador com linhas duplicadas (y=1 peso q, y=0 peso 1-q). 6 iterações.
O mesmo vale para P(algum problema) = 1º atraso ou parada, com janela = prazo inteiro -> P(em dia).

Validação fora do tempo: treino com corte simulado em 30/09/2025 (só parcelas vencidas até 31/07/2025);
teste = pedidos out/25–mar/26 (inclui o piloto). Saída: out/g05b_modelo_em.md e out/modelo_em.joblib
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score,
                             roc_auc_score)

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from g_util import carregar, km_vida  # noqa: E402
from g05_modelo import atributos, gbm, logit  # noqa: E402

OUT = AQUI / "out"
L = []
CORTE_SIM = pd.Timestamp("2025-09-30")
H = 4


def janela(prazo, tipo):
    prazo = np.asarray(prazo, float)
    return np.ceil(prazo * 2 / 3) if tipo == "pd" else prazo


def obs_no_corte(ap, per, corte, tipo):
    """(evento, w) por contrato no corte dado. tipo 'pd' = parada; 'any' = 1º atraso ou parada."""
    p = per[per.data_vencimento <= corte - pd.Timedelta(days=61)]
    if tipo == "pd":
        evt_k = p[p.evento_parada == 1].groupby("id_pedido").numero_parcela.min()
    else:
        evt_k = p[(p.evento_parada == 1) | (p.evento_atraso == 1)].groupby("id_pedido").numero_parcela.min()
    n_dec = p.groupby("id_pedido").numero_parcela.max()
    e = ap.id_pedido.map(evt_k).notna().values
    n = ap.id_pedido.map(n_dec).fillna(0).values
    J = janela(ap.prazo_meses, tipo)
    w = np.clip(np.minimum(n, J) / J, 0, 1)
    return e, w


def ajustar_em(X, e, w, fabrica=gbm, it=6):
    ok = e | (w > 0)
    X, e, w = X[ok].reset_index(drop=True), e[ok], w[ok]
    q = np.where(e, 1.0, 0.0)
    # início: rótulo duro com peso de censura (estimador do time)
    Xd = pd.concat([X, X], ignore_index=True)
    m = None
    for i in range(it):
        if i == 0:
            y = np.r_[np.ones(len(X)), np.zeros(len(X))]
            sw = np.r_[np.where(e, 1.0, 0.0), np.where(e, 0.0, np.maximum(w, 1e-3))]
        else:
            p = m.predict_proba(X)[:, 1]
            q = np.where(e, 1.0, p * (1 - w) / np.maximum(1 - p * w, 1e-6))
            y = np.r_[np.ones(len(X)), np.zeros(len(X))]
            sw = np.r_[q, 1 - q]
        keep = sw > 1e-6
        m = fabrica()
        try:
            m.fit(Xd[keep], y[keep], **({"sample_weight": sw[keep]} if not hasattr(m, "steps") else
                                       {m.steps[-1][0] + "__sample_weight": sw[keep]}))
        except TypeError:
            m.fit(Xd[keep], y[keep])
    return m


def main():
    d, hist, ap, novos = carregar()
    per = pd.read_pickle(OUT / "periodos.pkl")
    ap = ap.reset_index(drop=True)

    # ---------------- validação fora do tempo
    tr = ap[ap.data_pedido <= CORTE_SIM].reset_index(drop=True)
    te = ap[(ap.data_pedido > CORTE_SIM) & (ap.data_pedido <= "2026-03-31")].reset_index(drop=True)
    Xtr, Xte = atributos(tr, tr.valor_aprovado), atributos(te, te.valor_aprovado)
    e_tr, w_tr = obs_no_corte(tr, per, CORTE_SIM, "pd")
    y4 = (te.parou & (te.k_parada <= np.minimum(H, te.prazo_meses))).astype(int).values
    Jte = janela(te.prazo_meses, "pd")
    frac4 = np.minimum(H, Jte) / Jte

    L.append("\n## 6.1b Validação fora do tempo — modelo EM de PD de vida inteira\n")
    L.append(f"Treino (corte simulado 30/09/2025): {len(tr):,} contratos, {int(e_tr.sum())} paradas observadas até então, "
             f"w médio {w_tr.mean():.2f}. Teste: {len(te):,} contratos ({(te.politica_aplicada == 'piloto').sum()} do piloto); "
             f"{y4.sum()} pararam até a {H}ª parcela.\n")
    res, prev = [], {}
    for nome, fab, cols in [("Score sozinho (EM, logístico)", logit, ["score", "prazo_meses"]),
                            ("Regressão logística (EM)", logit, None),
                            ("Gradient boosting (EM)", gbm, None)]:
        c = cols or list(Xtr.columns)
        m = ajustar_em(Xtr[c], e_tr, w_tr, fab)
        pv = m.predict_proba(Xte[c])[:, 1]
        p4 = pv * frac4
        prev[nome] = pv
        res.append({"modelo": nome, "AUC até 4ª": roc_auc_score(y4, p4), "Brier até 4ª": brier_score_loss(y4, p4),
                    "prevista até 4ª": p4.mean(), "observada até 4ª": y4.mean(), "PD vida prevista (média)": pv.mean()})
    k = km_vida(te)
    L.append(pd.DataFrame(res).set_index("modelo").round(4).to_markdown())
    L.append(f"\nPD vida observada (KM) no teste: **{100*k[0]:.1f}%** [{100*k[1]:.1f}–{100*k[2]:.1f}].")

    pv = prev["Gradient boosting (EM)"]
    te["pv"] = pv
    te["q"] = pd.qcut(pv, 5, labels=["Q1 (menor risco)", "Q2", "Q3", "Q4", "Q5 (maior risco)"])
    cal = []
    for q, g in te.groupby("q", observed=True):
        kk = km_vida(g)
        cal.append({"quintil": q, "n": len(g), "PD vida prevista": g.pv.mean(), "PD vida KM": kk[0],
                    "KM IC95": f"{100*kk[1]:.1f}–{100*kk[2]:.1f}%",
                    "piloto %": (g.politica_aplicada == "piloto").mean()})
    L.append("\nCalibração por quintil (gradient boosting EM, teste fora do tempo):\n")
    L.append(pd.DataFrame(cal).set_index("quintil").round(3).to_markdown())

    L.append("\n## 6.3b Decisão no ponto de equilíbrio (nega se PD vida prevista > 17,5%)\n")
    L.append("Alvo observável: parou até a 4ª parcela. Precisão = dos negados, quantos pararam; recall = dos que pararam, quantos foram negados.\n")
    atual_nega = ((te.score <= 600) | (te.renda_declarada <= 2000) | (te.restricoes_ativas > 0)).astype(int).values
    for nome, yhat in [("Gradient boosting (EM)", (pv > 0.175).astype(int)),
                       ("Regressão logística (EM)", (prev["Regressão logística (EM)"] > 0.175).astype(int)),
                       ("Score > 600 sozinho", (te.score <= 600).astype(int).values),
                       ("Regra da política atual", atual_nega)]:
        cm = confusion_matrix(y4, yhat)
        kk_ap = km_vida(te[yhat == 0])
        kk_ng = km_vida(te[yhat == 1]) if yhat.sum() >= 30 else (np.nan, np.nan, np.nan)
        L.append(f"**{nome}**: nega {yhat.mean():.1%} · precisão {precision_score(y4, yhat, zero_division=0):.3f} · "
                 f"recall {recall_score(y4, yhat):.3f} · F1 {f1_score(y4, yhat):.3f} · PD vida (KM) dos aprovados "
                 f"{100*kk_ap[0]:.1f}% · dos negados {100*kk_ng[0]:.1f}%")
        L.append(pd.DataFrame(cm, index=["pagou até 4ª", "parou até 4ª"], columns=["aprova", "nega"]).to_markdown() + "\n")

    # ---------------- modelos finais com todos os dados (corte real)
    X = atributos(ap, ap.valor_aprovado)
    e_pd, w_pd = obs_no_corte(ap, per, pd.Timestamp("2026-09-30") + pd.Timedelta(days=61) - pd.Timedelta(days=61), "pd")
    # no corte real a regra de "decidida" é a do g02 (paga até o corte OU vencida há 61+ dias); usar k_obs
    e_pd = ap.parou.fillna(False).astype(bool).values
    w_pd = np.clip(np.minimum(ap.k_obs.fillna(0), janela(ap.prazo_meses, "pd")) / janela(ap.prazo_meses, "pd"), 0, 1)
    k_any = np.fmin(ap.k_parada.fillna(np.inf), ap.k_1o_atraso.fillna(np.inf))
    e_any = np.isfinite(k_any)
    w_any = np.clip(ap.n_decididas.fillna(0) / ap.prazo_meses, 0, 1)
    m_pd = ajustar_em(X, e_pd, w_pd.values, gbm)
    m_any = ajustar_em(X, e_any, w_any.values, gbm)
    joblib.dump({"pd": m_pd, "any": m_any, "cols": list(X.columns)}, OUT / "modelo_em.joblib")
    ap["pv"] = m_pd.predict_proba(X)[:, 1]
    ap["p_any"] = m_any.predict_proba(X)[:, 1]
    ap["p_em_dia"] = 1 - np.maximum(ap.p_any, ap.pv)
    L.append("\n## 6.6b Modelo final (todos os 6.033 aprovados) — PD prevista vs KM por decil (na amostra)\n")
    ap["dec"] = pd.qcut(ap.pv, 10, labels=False)
    cal = []
    for q, g in ap.groupby("dec"):
        kk = km_vida(g)
        cal.append({"decil": q + 1, "n": len(g), "PD prevista": g.pv.mean(), "PD KM": kk[0],
                    "KM IC95": f"{100*kk[1]:.1f}–{100*kk[2]:.1f}%", "P(em dia) prevista": g.p_em_dia.mean()})
    L.append(pd.DataFrame(cal).set_index("decil").round(3).to_markdown())
    L.append(f"\nMédia prevista {ap.pv.mean():.3f} vs KM de todos {km_vida(ap)[0]:.3f}.")
    (OUT / "g05b_modelo_em.md").write_text("# Saída de g05b_modelo_em.py\n" + "\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
