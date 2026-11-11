"""Onda 2 / item 4: arvores rasas + busca de segmentos, com confirmacao temporal.
python analise/onda2_arvores.py  -> stdout + onda2_segmentos.csv
"""
import itertools
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from base import carregar
from util import extras

np.random.seed(42)
pd.set_option("display.width", 250)
d = extras(carregar())
ap = d[d.decisao == "aprovado"].copy()
M = ap[ap.data_pedido <= "2025-09-30"].copy()
OLD = M[M.data_pedido <= "2025-03-31"]
NEW = M[M.data_pedido > "2025-03-31"]
print("antigos", len(OLD), OLD.y_calote.mean().round(3), "| novos maduros", len(NEW), NEW.y_calote.mean().round(3))

F = ["renda_declarada", "score", "restricoes_ativas", "parcelas_outras_instituicoes", "consultas_90_dias",
     "meses_historico_bureau", "valor_aprovado", "prazo_meses", "idade", "tempo_conta_meses",
     "parc_aprov_renda", "parc_aprov_ent", "sal_renda", "ent_renda", "outras_renda", "comprom_renda", "comprom_ent",
     "valor_aprov_renda", "mov_meses", "ent_media", "sal_media", "sai_media", "saldo_medio_3m", "saldo_min_3m",
     "saldo_min_min", "cheque_12m", "cheque_3m", "meses_sem_salario", "cv_entradas", "meses_saida_maior",
     "tend_entradas", "queda_entradas", "saida_ent", "saida_ent_3m", "dia_pedido"]
X = lambda df: df[F].fillna(-999)

for depth in (2, 3, 4):
    t = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=50, random_state=42).fit(X(OLD), OLD.y_calote)
    print(f"\n--- arvore prof {depth} (treino: antigos) ---")
    print(export_text(t, feature_names=F, decimals=3, show_weights=False))
    lo, ln = t.apply(X(OLD)), t.apply(X(NEW))
    tab = pd.DataFrame({"folha": lo, "y": OLD.y_calote.values}).groupby("folha").y.agg(["size", "mean"]).join(
        pd.DataFrame({"folha": ln, "y": NEW.y_calote.values}).groupby("folha").y.agg(["size", "mean"]), rsuffix="_novos")
    print(tab.round(3).to_string())

# segmento sem estresse e sem comprometimento: o que sobra
S = (M.meses_saida_maior > 0) | ((M.cheque_3m > 6) & (M.saldo_min_3m < -300))
R = M[~S & (M.parc_aprov_renda <= 0.25) & (M.parc_aprov_ent <= 0.28)]
print("\nresiduo", len(R), R.y_calote.mean().round(3))
t = DecisionTreeClassifier(max_depth=3, min_samples_leaf=60, random_state=42).fit(X(R), R.y_calote)
print(export_text(t, feature_names=F, decimals=3))

# busca direta de pares de condicoes (cortes por quantis) com apoio >= 50 no antigo; confere no novo
cands = {}
for v in F:
    s = M[v].dropna()
    if s.nunique() <= 1:
        continue
    for q in (0.05, 0.1, 0.2, 0.8, 0.9, 0.95):
        c = s.quantile(q)
        if q < 0.5:
            cands[f"{v}<={c:.3g}"] = (lambda df, v=v, c=c: df[v] <= c)
        else:
            cands[f"{v}>{c:.3g}"] = (lambda df, v=v, c=c: df[v] > c)
for cat, val in [("tipo_vinculo", "autonomo"), ("tipo_vinculo", "empresario"), ("tipo_vinculo", "aposentado"),
                 ("tipo_vinculo", "assalariado")]:
    cands[f"{cat}=={val}"] = (lambda df, cat=cat, val=val: df[cat] == val)
keys = list(cands)
base = OLD.y_calote.mean()
res = []
for a, b in itertools.combinations(keys, 2):
    if a.split("<")[0].split(">")[0].split("=")[0] == b.split("<")[0].split(">")[0].split("=")[0]:
        continue
    mo = cands[a](OLD) & cands[b](OLD)
    if mo.sum() < 50:
        continue
    r_old = OLD.y_calote[mo].mean()
    if base * 0.4 < r_old < base * 2.5:
        continue
    mn = cands[a](NEW) & cands[b](NEW)
    # so os que acrescentam alem dos dois efeitos isolados
    res.append(dict(seg=f"{a} & {b}", n_old=int(mo.sum()), taxa_old=r_old, n_new=int(mn.sum()),
                    taxa_new=NEW.y_calote[mn].mean(),
                    taxa_a=OLD.y_calote[cands[a](OLD)].mean(), taxa_b=OLD.y_calote[cands[b](OLD)].mean()))
Z = pd.DataFrame(res)
Z["sinergia"] = Z.taxa_old - Z[["taxa_a", "taxa_b"]].max(axis=1).where(Z.taxa_old > base, Z[["taxa_a", "taxa_b"]].min(axis=1))
Z.to_csv("onda2_segmentos.csv", index=False)
print("\n=== pares ALTO risco com sinergia (taxa do par acima das duas isoladas), ordenado ===")
hi = Z[(Z.taxa_old > base)].sort_values("sinergia", ascending=False)
print(hi.head(25).round(3).to_string(index=False))
print("\n=== pares BAIXO risco ===")
lo = Z[(Z.taxa_old < base)].sort_values("taxa_old")
print(lo.head(20).round(3).to_string(index=False))
