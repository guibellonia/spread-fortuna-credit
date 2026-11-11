"""Compara variantes do hazard: calibração de vida inteira vs KM direto por prazo e quintil."""
import numpy as np, pandas as pd, tool_risco as t
from sklearn.ensemble import HistGradientBoostingClassifier
from score_direto import km, d as D, ped
from sklearn.metrics import roc_auc_score
_, A, _, _ = t.painel_parcelas()
def fit(df, feats, **kw):
    X = df.assign(k_frac=df.k/df.prazo)[feats].astype(float).values
    m = HistGradientBoostingClassifier(monotonic_cst=[t.MONO.get(f,0) for f in feats], random_state=0, **kw)
    return m.fit(X, df.y.values)
base_feats = t.FEATS
vars_ = {
 "atual": (base_feats, dict(max_iter=300, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=80, l2_regularization=1.0)),
 "sem_k": ([f for f in base_feats if f!="k"], dict(max_iter=300, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=80, l2_regularization=1.0)),
 "mais_cap": (base_feats, dict(max_iter=600, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=30, l2_regularization=1.0)),
 "sem_k_mais_cap": ([f for f in base_feats if f!="k"], dict(max_iter=600, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=30, l2_regularization=1.0)),
}
P = ped.reset_index(drop=True)
for nm, (feats, kw) in vars_.items():
    md, ma = fit(D, feats, **kw), fit(A, feats, **kw)
    old = t.FEATS; t.FEATS = feats
    pr = t.prever_df(P, P.valor_aprovado.values, {"hazard_inad": md, "hazard_atraso": ma})
    t.FEATS = old
    pp = pr.p_nao_paga.values
    q = pd.qcut(pp, 5, labels=False)
    s = [f"{nm:15s} média {100*pp.mean():.1f}% (KM {100*km(D):.1f}%)"]
    s.append("quintis prev/KM: " + " ".join(f"{100*pp[q==i].mean():.1f}/{100*km(D[D.id_pedido.isin(P.id_pedido[q==i])]):.1f}" for i in range(5)))
    s.append("prazo prev/KM: " + " ".join(f"{pz}:{100*pp[P.prazo==pz].mean():.1f}/{100*km(D[D.id_pedido.isin(P.id_pedido[P.prazo==pz])]):.1f}" for pz in [6,12,18,24,36]))
    print("\n  ".join(s))
