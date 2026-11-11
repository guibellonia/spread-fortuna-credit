"""Tabela final por política (3 cenários) e arquivo de decisões da política própria."""
import pandas as pd, numpy as np, tool_risco as t
from politicas import escolhe, avaliar, politica_A, GRADE
nov, grade = pd.read_pickle(GRADE); m = t.carregar_modelo()
ok = lambda mask: set(nov.loc[mask, "id_pedido"])
fB = ok((nov.restricoes_ativas == 0) & (nov.meses_saldo_neg <= 1))
fC = fB & ok(nov.score > 600)
fR1 = ok((nov.restricoes_ativas <= 1) & (nov.meses_saldo_neg <= 1))
pols = {"A": politica_A(nov), "B": escolhe(grade, nov, fB, 0.20, 0.20), "C": escolhe(grade, nov, fC, 0.20, 0.20),
        "G": escolhe(grade, nov, fB, 0.20, 0.175),
        "PROPRIA": escolhe(grade, nov, fB, 0.30, 0.20, 1.2),
        "PROPRIA_restr<=1": escolhe(grade, nov, fR1, 0.30, 0.20, 1.2),
        "PROPRIA_sem_filtros": escolhe(grade, nov, ok(nov.id_pedido.notna()), 0.30, 0.20, 1.2)}
tab = pd.DataFrame({k: avaliar(v, nov, m) for k, v in pols.items()}).T
for c in ["base", "pessimista", "otimista"]:
    tab[f"{c}_vs_A"] = tab[c] - tab.loc["A", c]
pd.set_option("display.width", 250)
print((tab.astype(float) / [1, 1e6, 0.01] + [0]*0 if False else tab).astype(float).round(3).to_string())
dec = pols["PROPRIA"]
out = nov[["id_pedido"]].copy()
out["valor_aprovado"] = out["id_pedido"].map(dec).fillna(0.0)
out["decisao"] = np.where(out["valor_aprovado"] > 0, "APROVADO", "NEGADO")
assert (out.valor_aprovado <= nov.valor_solicitado.clip(upper=30000) + 1e-9).all()
assert ((out.valor_aprovado == 0) | (out.valor_aprovado >= 500)).all()
out = out.sort_values("id_pedido")
with open(t.os.path.join(t.AQUI, "decisoes_PROPRIA.csv"), "w", encoding="utf-8", newline="\n") as f:
    f.write("id_pedido,decisao,valor_aprovado\n")
    for r in out.itertuples():
        f.write(f"{r.id_pedido},{r.decisao},{r.valor_aprovado:.2f}\n")
# concordância de decisões com B
b = pols["B"]
print("aprovados PROPRIA:", len(dec), "| mesmos ids que B:", len(set(dec) & set(b)),
      "| valor médio aprovado PROPRIA vs B:", round(np.mean(list(dec.values()))), round(np.mean(list(b.values()))))
