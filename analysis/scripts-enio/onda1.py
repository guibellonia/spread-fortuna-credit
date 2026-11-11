"""Onda 1: alvo + varredura de uma variavel. Reprodutivel: python analise/onda1.py
Saida: analise/onda1_varredura.csv, analise/onda1_categ.csv, stdout.
"""
import numpy as np
import pandas as pd
from base import carregar
from util import arred, varre, extras

np.random.seed(42)
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_columns", 30)

d = carregar()
ap = d[d.decisao == "aprovado"].copy()
M = ap[ap.data_pedido <= "2025-09-30"].copy()   # maduros: >=12 parcelas vencidas
print("maduros", len(M), "calote", M.y_calote.mean().round(4), "atraso", M.y_atraso.mean().round(4))

NUM = ["renda_declarada", "score", "restricoes_ativas", "parcelas_outras_instituicoes", "consultas_90_dias",
       "meses_historico_bureau", "valor_solicitado", "prazo_meses", "valor_aprovado", "idade", "tempo_conta_meses",
       "parc_renda", "parc_aprov_renda", "parc_sal", "parc_aprov_sal", "parc_ent", "sal_renda", "ent_renda", "valor_renda",
       "outras_renda", "outras_mais_parc_renda", "mov_meses", "ent_media", "sal_media", "sai_media", "saldo_medio_med",
       "saldo_min_min", "saldo_min_med", "saldo_min_3m", "saldo_medio_3m", "cheque_12m", "cheque_3m", "cheque_meses_12m",
       "meses_sem_salario", "cv_entradas", "meses_saida_maior", "tend_entradas", "queda_entradas", "queda_salario",
       "saida_ent", "saida_ent_3m", "dia_pedido", "dow_pedido"]
CAT = ["tipo_vinculo", "genero", "estado_civil", "profissao", "uf_cep1", "prazo_meses", "dow_pedido"]


rows = [r for v in NUM if (r := varre(M, v)) is not None]
R = pd.DataFrame(rows).sort_values("chi2", ascending=False)
R.to_csv("onda1_varredura.csv", index=False)
print("\n=== Varredura 1 variavel (maduros, alvo = calote 90+) ===")
print(R.round(3).to_string(index=False))

# mesmo com alvo 'qualquer atraso' (classe atraso ou calote)
M["y_ruim"] = (M.atraso_max > 0).astype(float)
rows = [r for v in NUM if (r := varre(M, v, "y_ruim")) is not None]
R2 = pd.DataFrame(rows).sort_values("chi2", ascending=False)
R2.to_csv("onda1_varredura_qualquer_atraso.csv", index=False)
print("\n=== Varredura (alvo = qualquer atraso) top 15 ===")
print(R2.head(15).round(3).to_string(index=False))

print("\n=== Categoricas (maduros) ===")
out = []
for c in CAT:
    t = M.groupby(c).agg(n=("y_calote", "size"), calote=("y_calote", "mean"), atraso=("y_atraso", "mean"))
    t = t[t.n >= 30]
    t["var"] = c
    out.append(t.reset_index().rename(columns={c: "nivel"}))
    print(t.round(3).sort_values("calote").to_string())
pd.concat(out).to_csv("onda1_categ.csv", index=False)
