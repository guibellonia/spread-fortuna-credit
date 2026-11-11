"""Onda 2: tabela final de padroes com conferencia temporal e no piloto. Rodar depois de onda2_politica.py.
python analise/onda2_frases.py -> onda2_frases.csv
"""
import numpy as np
import pandas as pd

d = pd.read_pickle("_base_flags.pkl")
nov = pd.read_csv("novos_flags.csv").merge(pd.read_pickle("_base_novo.pkl"), on="id_pedido")
ap = d[d.decisao == "aprovado"].copy()
ap["cal3"] = np.where(ap.n_vencidas >= 6, (ap.parc_1o_90 <= 3).astype(float), np.nan)
M = ap[ap.data_pedido <= "2025-09-30"]
W = ap[(ap.data_pedido >= "2025-10-01") & (ap.data_pedido <= "2026-03-31")]
old = M.data_pedido <= "2025-03-31"
media = M.y_calote.mean()
limpo = lambda x: ~x.S & (x.parc_aprov_real <= 0.28)

P = [
    ("saidas maiores que as entradas em algum dos 3 meses antes do pedido E cheque especial nos 2 meses antes",
     lambda x: x.saque3 & x.cheq2, lambda x: x.saque3 & x.cheq2),
    ("cheque especial nos 2 meses antes do pedido, sem a saida grande",
     lambda x: x.cheq2 & ~x.saque3, lambda x: x.cheq2 & ~x.saque3),
    ("parcela aprovada acima de 28% da renda real (menor entre renda declarada e entradas medias da conta), sem estresse",
     lambda x: ~x.S & (x.parc_aprov_real > 0.28), lambda x: ~x.S & (x.parc_sol_real > 0.28)),
    ("pedido reduzido pela politica ao teto de 30% da renda declarada, sem estresse",
     lambda x: ~x.S & x.reduzido & (x.politica_aplicada == "atual"), None),
    ("parcela + dividas em outras instituicoes acima de 42% das entradas medias (ja limpos)",
     lambda x: limpo(x) & (x.comprom_ent > 0.42), None),
    ("entradas da conta oscilando (coef. de variacao > 0,35) (ja limpos)",
     lambda x: limpo(x) & (x.cv_entradas > 0.35), lambda x: ~x.S & (x.parc_sol_real <= 0.28) & (x.cv_entradas > 0.35)),
    ("historico no bureau de ate 30 meses (ja limpos)",
     lambda x: limpo(x) & (x.meses_historico_bureau <= 30), None),
    ("idade acima de 70 anos (ja limpos)",
     lambda x: limpo(x) & (x.idade > 70), lambda x: ~x.S & (x.parc_sol_real <= 0.28) & (x.idade > 70)),
    ("vinculo aposentado (ja limpos)",
     lambda x: limpo(x) & (x.tipo_vinculo == "aposentado"), lambda x: ~x.S & (x.parc_sol_real <= 0.28) & (x.tipo_vinculo == "aposentado")),
    ("score do bureau entre 450 e 600 (so piloto aprovou; ja limpos)", None, None),
]
rows = []
for nome, f, fn in P:
    if f is None:
        g = W[limpo(W) & (W.politica_aplicada == "piloto") & W.score.between(450, 600)]
        rows.append(dict(padrao=nome, n=len(g), taxa=np.nan, n_old=np.nan, taxa_old=np.nan, n_new=np.nan, taxa_new=np.nan,
                         n_janela_piloto=len(g), cal3_grupo=g.cal3.mean(),
                         cal3_resto=W[limpo(W) & (W.score > 600)].cal3.mean(), n_hist=int((d.score.between(450, 600)).sum()), n_novos=np.nan))
        continue
    m = f(M)
    w = f(W)
    rows.append(dict(padrao=nome, n=int(m.sum()), taxa=M[m].y_calote.mean(), atraso=M[m].y_atraso.mean(),
                     n_old=int((m & old).sum()), taxa_old=M[m & old].y_calote.mean(),
                     n_new=int((m & ~old).sum()), taxa_new=M[m & ~old].y_calote.mean(),
                     n_janela_piloto=int(w.sum()), cal3_grupo=W[w].cal3.mean(), cal3_resto=W[~w].cal3.mean(),
                     n_hist=int(f(d.assign(parc_aprov_real=d.parc_sol_real, reduzido=d.reduzido.fillna(False))).sum()),
                     n_novos=int(fn(nov).sum()) if fn else np.nan))
R = pd.DataFrame(rows)
R["media"] = media
R.to_csv("onda2_frases.csv", index=False)
pd.set_option("display.width", 250)
print(R.round(3).to_string(index=False))
