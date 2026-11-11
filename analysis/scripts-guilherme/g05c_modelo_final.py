"""Etapa 6 · Escolha do modelo final de PD de vida inteira (EM com censura, ver g05b).

Compara fora do tempo (treino até set/25 com corte simulado; teste out/25–mar/26, 62% piloto):
  A. logística EM, atributos contínuos
  B. logística EM, contínuos + 16 regras binárias descobertas nas etapas 4–5 (scorecard interpretável)
  C. gradient boosting EM regularizado, contínuos + regras
Critério: calibração da PD de vida inteira por quintil contra KM (é ela que decide perto do equilíbrio de 17,5%)
e AUC. Depois: previsões fora da dobra (5 dobras) em todos os aprovados para conferir calibração por decil.
Saídas: out/g05c_modelo_final.md, out/modelo_final.joblib (pd, em_dia, função de atributos)
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from g_util import carregar, km_vida  # noqa: E402
from g05_modelo import DO_VALOR, atributos  # noqa: E402
from g05b_modelo_em import ajustar_em, janela, obs_no_corte  # noqa: E402

OUT = AQUI / "out"
CORTE_SIM = pd.Timestamp("2025-09-30")
L = []

REGRAS = {
    "r_parcela_50pct_sobra": lambda f: (f.pss >= 0.5) | (f.sobra_pos < 0),
    "r_deficit_3m": lambda f: f.deficit_3m >= 1,
    "r_deficit_2m_12m": lambda f: f.meses_deficit >= 2,
    "r_cheque_2m_12m": lambda f: f.cheq_meses >= 2,
    "r_saidas_80pct": lambda f: f.sai_ent >= 0.8,
    "r_valor_reduzido": lambda f: f.excesso > 1.001,
    "r_pedido_30pct_renda": lambda f: f.comp_decl_solic > 0.30,
    "r_restricao": lambda f: f.restricoes_ativas > 0,
    "r_score_600": lambda f: f.score <= 600,
    "r_renda_conta_60pct": lambda f: f.renda_ratio < 0.6,
    "r_consultas_6": lambda f: f.consultas_90_dias >= 6,
    "r_birô_12m": lambda f: f.meses_historico_bureau < 12,
    "r_saidas_subindo_50pct": lambda f: f.sai_tend >= 1.5,
    "r_outras_40pct": lambda f: f.comp_antes >= 0.4,
    "r_prazo_6": lambda f: f.prazo_meses == 6,
    "r_conta_3m": lambda f: f.mov_meses <= 3,
}


def atributos_r(x, valor):
    f = atributos(x, valor)
    for k, fn in REGRAS.items():
        f[k] = fn(f).astype(float)
    return f


def logit():
    return make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                         LogisticRegression(C=0.3, max_iter=5000))


def gbm_reg():
    return HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_leaf_nodes=8, min_samples_leaf=150,
                                          l2_regularization=3.0, random_state=42)


def calib(te, pv, rot="quintil", n=5):
    te = te.assign(pv=pv)
    te["q"] = pd.qcut(te.pv.rank(method="first"), n, labels=False) + 1
    linhas = []
    for q, g in te.groupby("q"):
        k = km_vida(g)
        linhas.append({rot: q, "n": len(g), "PD prevista": g.pv.mean(), "PD KM": k[0], "KM IC95": f"{100*k[1]:.1f}–{100*k[2]:.1f}%"})
    t = pd.DataFrame(linhas).set_index(rot)
    erro = (t["PD prevista"] - t["PD KM"]).abs().mean()
    return t, erro


def main():
    d, hist, ap, novos = carregar()
    per = pd.read_pickle(OUT / "periodos.pkl")
    ap = ap.reset_index(drop=True)
    tr = ap[ap.data_pedido <= CORTE_SIM].reset_index(drop=True)
    te = ap[(ap.data_pedido > CORTE_SIM) & (ap.data_pedido <= "2026-03-31")].reset_index(drop=True)
    e_tr, w_tr = obs_no_corte(tr, per, CORTE_SIM, "pd")
    y4 = (te.parou & (te.k_parada <= np.minimum(4, te.prazo_meses))).astype(int).values
    frac4 = np.minimum(4, janela(te.prazo_meses, "pd")) / janela(te.prazo_meses, "pd")
    Xtr, Xte = atributos_r(tr, tr.valor_aprovado), atributos_r(te, te.valor_aprovado)
    cont = [c for c in Xtr.columns if not c.startswith("r_")]
    cands = {"A. logística, contínuos": (logit, cont), "B. logística, contínuos + regras": (logit, list(Xtr.columns)),
             "C. boosting regularizado, contínuos + regras": (gbm_reg, list(Xtr.columns))}
    k_te = km_vida(te)
    L.append("\n## 6.1c Comparação fora do tempo (PD de vida inteira)\n")
    L.append(f"Teste: {len(te):,} contratos; PD vida KM {100*k_te[0]:.1f}% [{100*k_te[1]:.1f}–{100*k_te[2]:.1f}].\n")
    res, tabs = [], {}
    for nome, (fab, cols) in cands.items():
        m = ajustar_em(Xtr[cols], e_tr, w_tr, fab)
        pv = m.predict_proba(Xte[cols])[:, 1]
        t, erro = calib(te, pv)
        tabs[nome] = t
        res.append({"modelo": nome, "AUC até 4ª": roc_auc_score(y4, pv * frac4), "Brier até 4ª": brier_score_loss(y4, pv * frac4),
                    "PD vida prevista": pv.mean(), "erro médio de calibração (quintis)": erro})
    L.append(pd.DataFrame(res).set_index("modelo").round(4).to_markdown())
    for nome, t in tabs.items():
        L.append(f"\n**{nome}** — calibração por quintil:\n")
        L.append(t.round(3).to_markdown())

    # ---------- validação cruzada (5 dobras) em todos os aprovados, rótulos no corte real
    X = atributos_r(ap, ap.valor_aprovado)
    e = ap.parou.fillna(False).astype(bool).values
    J = janela(ap.prazo_meses, "pd")
    w = np.clip(np.minimum(ap.k_obs.fillna(0), J) / J, 0, 1).values
    k_any = np.fmin(ap.k_parada.fillna(np.inf), ap.k_1o_atraso.fillna(np.inf)).values
    e_any = np.isfinite(k_any)
    w_any = np.clip(ap.n_decididas.fillna(0) / ap.prazo_meses, 0, 1).values
    L.append("\n## 6.6c Previsões fora da dobra (5 dobras) em todos os 6.033 aprovados, por decil\n")
    for nome in ["B. logística, contínuos + regras", "C. boosting regularizado, contínuos + regras"]:
        fab, cols = cands[nome]
        oof = np.zeros(len(ap))
        for itr, ite in KFold(5, shuffle=True, random_state=0).split(X):
            m = ajustar_em(X.iloc[itr][cols].reset_index(drop=True), e[itr], w[itr], fab)
            oof[ite] = m.predict_proba(X.iloc[ite][cols])[:, 1]
        t, erro = calib(ap, oof, "decil", 10)
        L.append(f"\n**{nome}** — erro médio {erro:.3f}; média prevista {oof.mean():.3f} vs KM {km_vida(ap)[0]:.3f}\n")
        L.append(t.round(3).to_markdown())
        ap[f"oof_{nome[0]}"] = oof

    # ---------- modelo final: ensemble (média) de B e C; P(em dia) pelo mesmo método
    mB = ajustar_em(X, e, w, logit)
    mC = ajustar_em(X, e, w, gbm_reg)
    # P(em dia) só com atributos que NÃO dependem do valor: com eles, o otimizador explorava um artefato
    # (P(em dia) saltava de 40% para 48% com 0,1% de redução por causa da flag de valor reduzido)
    cols_any = [c for c in X.columns if c not in DO_VALOR + ["r_parcela_50pct_sobra", "r_valor_reduzido"]]
    aB = ajustar_em(X[cols_any], e_any, w_any, logit)
    aC = ajustar_em(X[cols_any], e_any, w_any, gbm_reg)
    ens = 0.5 * (ap["oof_B"] + ap["oof_C"])
    t, erro = calib(ap, ens, "decil", 10)
    L.append(f"\n**Ensemble B+C (média)** fora da dobra — erro médio {erro:.3f}; AUC (parou, todos) "
             f"{roc_auc_score(e, ens):.3f}\n")
    L.append(t.round(3).to_markdown())
    joblib.dump({"pd": [mB, mC], "any": [aB, aC], "cols": list(X.columns), "cols_any": cols_any}, OUT / "modelo_final.joblib")
    (OUT / "g05c_modelo_final.md").write_text("# Saída de g05c_modelo_final.py\n" + "\n".join(L), encoding="utf-8")
    print("\n".join(L))


def prever(modelo, x, valor):
    """PD de vida, P(em dia), P(atraso) para pedidos x e valor candidato."""
    X = atributos_r(x, valor)[modelo["cols"]]
    pdv = np.mean([m.predict_proba(X)[:, 1] for m in modelo["pd"]], axis=0)
    Xa = X[modelo.get("cols_any", modelo["cols"])]
    pany = np.mean([m.predict_proba(Xa)[:, 1] for m in modelo["any"]], axis=0)
    em_dia = np.clip(1 - np.maximum(pany, pdv), 0, 1)
    atraso = np.clip(1 - em_dia - pdv, 0, 1)
    return pdv, em_dia, atraso


if __name__ == "__main__":
    main()
