"""Etapa 6 · Modelos de risco com correção de censura e validação fora do tempo.

Modelo: hazard em tempo discreto (uma linha por parcela decidida). h(k) = P(parar na parcela k | pagou até k-1).
  PD vida = 1 - prod_{k=1..prazo} (1 - h(k)).   P(em dia) vem de um 2º hazard: "1º atraso OU parada".
Validação temporal SEM vazamento:
  treino = contratos com pedido <= 30/09/2025, só parcelas vencidas até 31/07/2025 (decididas no corte simulado
           de 30/09/2025: parcela paga nunca atrasou > 60 dias, então o status delas já era o final)
  teste  = contratos com pedido entre 01/10/2025 e 31/03/2026 (inclui o piloto: score <= 600 e restrição),
           alvo = parou até a 4ª parcela (observável para todo o teste no corte real)
Atributos: só o que existe na data do pedido. Gênero, estado civil, CEP e idade ficam FORA (testados à parte).
Saídas: out/g05_modelo.md, out/modelo_pd.joblib, out/modelo_emdia.joblib
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from g_util import carregar, km_vida  # noqa: E402

OUT = AQUI / "out"
L = []
TAXA = 0.03
CORTE_SIM = pd.Timestamp("2025-09-30")
H = 4  # horizonte observável no teste

ESTATICOS = ["prazo_meses", "score", "restricoes_ativas", "consultas_90_dias", "meses_historico_bureau",
             "comp_antes", "renda_declarada", "renda_ratio", "ent_cv", "sai_ent", "meses_deficit", "deficit_3m",
             "cheq_meses", "cheq_meses_3m", "cheq_dias_media", "saldo_min", "saldo_medio", "sai_tend", "ent_tend",
             "sai_pico", "sal_share", "mov_meses", "meses_conta", "vinc_autonomo", "vinc_empresario",
             "vinc_aposentado", "comp_decl_solic", "comp_real_solic"]
DO_VALOR = ["comp_real", "comp_decl", "comp_total", "pss", "sobra_pos", "endiv", "parcela", "excesso"]
DEMOG = ["fem", "casado", "idade", "regiao_num"]


def pmt(v, n):
    return v * TAXA / (1 - (1 + TAXA) ** (-np.asarray(n, float)))


def atributos(x: pd.DataFrame, valor, demog=False) -> pd.DataFrame:
    """Atributos do pedido para um valor candidato (o que depende do valor é recalculado)."""
    f = x.copy()
    valor = np.asarray(valor, float)
    parc = pmt(valor, f.prazo_meses)
    f["comp_real"] = parc / f.renda_est
    f["comp_decl"] = parc / f.renda_declarada
    f["comp_total"] = (parc + f.outras_parc) / f.renda_est
    f["pss"] = np.clip(np.where(f.sobra_media > 0, parc / f.sobra_media, 5.0), -1, 5)
    f["sobra_pos"] = f.sobra_media - parc
    f["endiv"] = valor / f.renda_est
    f["parcela"] = parc
    f["excesso"] = f.valor_solicitado / np.maximum(valor, 1)
    for v in ["autonomo", "empresario", "aposentado"]:
        f[f"vinc_{v}"] = (f.tipo_vinculo == v).astype(int)
    cols = ESTATICOS + DO_VALOR
    if demog:
        f["fem"] = (f.genero == "feminino").astype(int)
        f["casado"] = f.estado_civil.isin(["casado", "uniao_estavel"]).astype(int)
        f["regiao_num"] = f.cep.str[0].astype(int)
        cols = cols + DEMOG
    return f[cols].astype(float)


def painel(ap, per, ate_venc=None, evento="parada"):
    """Linhas (contrato × parcela) com atributos + tempo. evento='parada' ou 'qualquer' (1º atraso ou parada)."""
    p = per.copy()
    if ate_venc is not None:
        p = p[p.data_vencimento <= ate_venc]
    if evento == "qualquer":
        p["evt"] = ((p.evento_parada == 1) | (p.evento_atraso == 1)).astype(int)
        primeiro = p[p.evt == 1].groupby("id_pedido").numero_parcela.min().rename("k1")
        p = p.merge(primeiro, on="id_pedido", how="left")
        p = p[p.k1.isna() | (p.numero_parcela <= p.k1)]
    else:
        p["evt"] = p.evento_parada
    X = atributos(ap.set_index("id_pedido").loc[p.id_pedido].reset_index(), ap.set_index("id_pedido").loc[p.id_pedido, "valor_aprovado"].values)
    X["k"] = p.numero_parcela.values
    X["t"] = p.numero_parcela.values / p.prazo_meses.values
    return X, p.evt.values


def gbm():
    return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=60,
                                          l2_regularization=1.0, random_state=42)


def logit():
    return make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), LogisticRegression(C=0.5, max_iter=3000))


def prob_ate(m, X0: pd.DataFrame, prazo, kmax=None):
    """P(evento até kmax) = 1 - prod (1-h_k). kmax=None -> prazo inteiro (vida)."""
    prazo = np.asarray(prazo, int)
    kmax_v = prazo if kmax is None else np.minimum(prazo, kmax)
    S = np.ones(len(X0))
    for k in range(1, int(kmax_v.max()) + 1):
        ativo = k <= kmax_v
        if not ativo.any():
            break
        Xk = X0[ativo].copy()
        Xk["k"] = k
        Xk["t"] = k / prazo[ativo]
        ordem = getattr(m, "feature_names_in_", None)
        if ordem is not None:
            Xk = Xk[list(ordem)]
        S[ativo] *= 1 - m.predict_proba(Xk)[:, 1]
    return 1 - S


def h(t):
    L.append(f"\n## {t}\n")


def main():
    d, hist, ap, novos = carregar()
    per = pd.read_pickle(OUT / "periodos.pkl")

    # ------------------------------------------------ validação temporal
    tr_ids = ap[ap.data_pedido <= CORTE_SIM]
    te = ap[(ap.data_pedido > CORTE_SIM) & (ap.data_pedido <= "2026-03-31")].copy()
    per_tr = per[per.id_pedido.isin(tr_ids.id_pedido)]
    Xtr, ytr = painel(ap, per_tr, ate_venc=CORTE_SIM - pd.Timedelta(days=61))
    X0te = atributos(te, te.valor_aprovado)
    y4 = (te.parou & (te.k_parada <= np.minimum(H, te.prazo_meses))).astype(int).values

    feats_score = ["score", "k", "t", "prazo_meses"]
    modelos = {
        "Score do birô sozinho (logístico)": ("score", make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))),
        "Regressão logística (hazard)": ("all", logit()),
        "Gradient boosting (hazard)": ("all", gbm()),
    }
    h("6.1 Validação fora do tempo (treino: pedidos até set/25 com corte simulado; teste: out/25–mar/26)")
    L.append(f"Treino: {tr_ids.shape[0]:,} contratos, {len(ytr):,} parcelas decididas, {ytr.sum()} paradas. "
             f"Teste: {len(te):,} contratos ({(te.politica_aplicada == 'piloto').sum()} do piloto), "
             f"{y4.sum()} pararam até a {H}ª parcela ({100 * y4.mean():.1f}%).\n")
    res, preds = [], {}
    for nome, (tipo, m) in modelos.items():
        cols = feats_score if tipo == "score" else list(Xtr.columns)
        m.fit(Xtr[cols], ytr)
        X0 = X0te.copy()

        class W:  # adapta para prob_ate com subconjunto de colunas
            def __init__(s, m, c): s.m, s.c = m, c
            def predict_proba(s, X): return s.m.predict_proba(X[s.c])
        w = W(m, cols)
        p4 = prob_ate(w, X0, te.prazo_meses, kmax=H)
        pv = prob_ate(w, X0, te.prazo_meses)
        preds[nome] = (p4, pv)
        res.append({"modelo": nome, "AUC (parou até 4ª)": roc_auc_score(y4, p4), "Brier": brier_score_loss(y4, p4),
                    "prevista até 4ª": p4.mean(), "observada até 4ª": y4.mean(), "PD vida média prevista": pv.mean()})
    # regra da política atual como classificador
    atual_nega = ((te.score <= 600) | (te.renda_declarada <= 2000) | (te.restricoes_ativas > 0)).astype(int).values
    res.append({"modelo": "Regra da política atual (nega=1)", "AUC (parou até 4ª)": roc_auc_score(y4, atual_nega)})
    r = pd.DataFrame(res).set_index("modelo")
    L.append(r.round(4).to_markdown())
    km_te = km_vida(te)
    L.append(f"\nPD vida observada (KM) no teste: {100 * km_te[0]:.1f}% [{100 * km_te[1]:.1f}–{100 * km_te[2]:.1f}] — "
             f"comparar com a PD vida média prevista.")

    # calibração por quintil (GBM) — até a 4ª parcela e vida (KM)
    p4, pv = preds["Gradient boosting (hazard)"]
    te["p4"], te["pv"] = p4, pv
    te["q"] = pd.qcut(te.pv, 5, labels=["Q1 (menor risco)", "Q2", "Q3", "Q4", "Q5 (maior risco)"])
    cal = []
    for q, g in te.groupby("q", observed=True):
        k = km_vida(g)
        cal.append({"quintil": q, "n": len(g), "prevista até 4ª": g.p4.mean(), "observada até 4ª": y4[te.q == q].mean(),
                    "PD vida prevista": g.pv.mean(), "PD vida KM": k[0], "KM IC95": f"{100*k[1]:.1f}–{100*k[2]:.1f}%"})
    h("6.2 Calibração (gradient boosting, teste fora do tempo)")
    L.append(pd.DataFrame(cal).set_index("quintil").round(3).to_markdown())

    # matriz de confusão da decisão: nega se PD vida prevista > 17,5% (ponto de equilíbrio)
    h("6.3 Decisão pelo ponto de equilíbrio (nega se PD vida prevista > 17,5%) vs quem parou até a 4ª parcela")
    for nome in ["Gradient boosting (hazard)", "Regressão logística (hazard)"]:
        p4, pv = preds[nome]
        yhat = (pv > 0.175).astype(int)
        cm = confusion_matrix(y4, yhat)
        L.append(f"**{nome}**: precisão {precision_score(y4, yhat):.3f} · recall {recall_score(y4, yhat):.3f} · "
                 f"F1 {f1_score(y4, yhat):.3f} · nega {yhat.mean():.1%} do teste")
        L.append(pd.DataFrame(cm, index=["pagou até 4ª", "parou até 4ª"], columns=["aprova", "nega"]).to_markdown())
        L.append("")
    yhat = atual_nega
    cm = confusion_matrix(y4, yhat)
    L.append(f"**Regra da política atual**: precisão {precision_score(y4, yhat):.3f} · recall {recall_score(y4, yhat):.3f} · "
             f"F1 {f1_score(y4, yhat):.3f} · nega {yhat.mean():.1%} do teste (sem a redução de valor)")
    L.append(pd.DataFrame(cm, index=["pagou até 4ª", "parou até 4ª"], columns=["aprova", "nega"]).to_markdown())

    # ------------------------------------------------ demográficas: ganho incremental?
    h("6.4 Gênero, estado civil, região e idade acrescentam poder preditivo?")
    Xtr_d, _ = painel(ap, per_tr, ate_venc=CORTE_SIM - pd.Timedelta(days=61))
    ap_d = ap.set_index("id_pedido")
    pt = per_tr[per_tr.data_vencimento <= CORTE_SIM - pd.Timedelta(days=61)]
    D = atributos(ap_d.loc[pt.id_pedido].reset_index(), ap_d.loc[pt.id_pedido, "valor_aprovado"].values, demog=True)[DEMOG]
    Xtr_d = pd.concat([Xtr_d.reset_index(drop=True), D.reset_index(drop=True)], axis=1)
    m_d = gbm().fit(Xtr_d, ytr)
    X0d = pd.concat([X0te.reset_index(drop=True), atributos(te, te.valor_aprovado, demog=True)[DEMOG].reset_index(drop=True)], axis=1)
    p4d = prob_ate(m_d, X0d, te.prazo_meses.values, kmax=H)
    L.append(f"AUC sem demográficas {roc_auc_score(y4, preds['Gradient boosting (hazard)'][0]):.4f} · "
             f"com demográficas {roc_auc_score(y4, p4d):.4f} (teste fora do tempo, n={len(te)}).")

    # ------------------------------------------------ importância (permutação no teste, GBM)
    h("6.5 O que o modelo usa (queda de AUC ao embaralhar cada atributo no teste)")
    m = modelos["Gradient boosting (hazard)"][1]
    base_auc = roc_auc_score(y4, preds["Gradient boosting (hazard)"][0])
    rng = np.random.default_rng(0)
    imp = []
    for c in X0te.columns:
        X0 = X0te.copy()
        X0[c] = rng.permutation(X0[c].values)
        imp.append({"atributo": c, "queda_AUC": base_auc - roc_auc_score(y4, prob_ate(m, X0, te.prazo_meses, kmax=H))})
    L.append(pd.DataFrame(imp).sort_values("queda_AUC", ascending=False).head(15).set_index("atributo").round(4).to_markdown())

    # ------------------------------------------------ modelos finais (todos os dados, corte real)
    Xall, yall = painel(ap, per)
    m_pd = gbm().fit(Xall, yall)
    Xany, yany = painel(ap, per, evento="qualquer")
    m_any = gbm().fit(Xany, yany)
    joblib.dump({"pd": m_pd, "any": m_any, "cols": list(Xall.columns)}, OUT / "modelos_finais.joblib")
    X0 = atributos(ap, ap.valor_aprovado)
    ap["pv"] = prob_ate(m_pd, X0, ap.prazo_meses)
    ap["p_em_dia"] = 1 - prob_ate(m_any, X0, ap.prazo_meses)
    h("6.6 Modelo final (todos os aprovados): PD vida prevista vs KM por decil (dentro da amostra)")
    ap["dec"] = pd.qcut(ap.pv, 10, labels=False)
    cal = []
    for q, g in ap.groupby("dec"):
        k = km_vida(g)
        cal.append({"decil": q + 1, "n": len(g), "PD prevista": g.pv.mean(), "PD KM": k[0], "P(em dia) prevista": g.p_em_dia.mean()})
    L.append(pd.DataFrame(cal).set_index("decil").round(3).to_markdown())
    L.append(f"\nMédia prevista {ap.pv.mean():.3f} vs KM de todos {km_vida(ap)[0]:.3f}.")

    (OUT / "g05_modelo.md").write_text("# Saída de g05_modelo.py\n" + "\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
