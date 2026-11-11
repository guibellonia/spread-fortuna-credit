"""Onda 1: os 10 padroes de uma variavel no formato do manual. python analise/onda1_frases.py"""
import pandas as pd
from base import carregar
from util import extras

d = carregar()
nov = carregar(tipo="novo")
ap = extras(d[d.decisao == "aprovado"])
M = ap[ap.data_pedido <= "2025-09-30"]
base = M.y_calote.mean()


def nov_ok(f):
    try:
        return int(f(nov).sum())
    except Exception:
        return None


P = [
    ("saidas maiores que as entradas em pelo menos 1 dos 12 meses antes do pedido", lambda x: x.meses_saida_maior > 0),
    ("mais de 6 dias de cheque especial nos 3 meses antes do pedido", lambda x: x.cheque_3m > 6),
    ("saldo minimo abaixo de -R$300 nos 3 meses antes do pedido", lambda x: x.saldo_min_3m < -300),
    ("parcela pedida acima de 30% das entradas medias da conta", lambda x: x.parc_ent > 0.30),
    ("parcela pedida acima de 25% da renda declarada", lambda x: x.parc_renda > 0.25),
    ("valor pedido acima de 4x a renda declarada", lambda x: x.valor_renda > 4),
    ("saldo medio abaixo de R$7.500 nos 3 meses antes do pedido", lambda x: x.saldo_medio_3m < 7500),
    ("mais de 6 consultas ao CPF nos ultimos 90 dias", lambda x: x.consultas_90_dias > 6),
    ("parcela pedida + dividas em outras instituicoes acima de 45% da renda declarada", lambda x: x.outras_mais_parc_renda > 0.45),
    ("prazo de 6 meses", lambda x: x.prazo_meses == 6),
    ("entradas da conta oscilando muito (coef. de variacao > 0,35)", lambda x: x.cv_entradas > 0.35),
    ("vinculo aposentado", lambda x: x.tipo_vinculo == "aposentado"),
    ("prazo de 36 meses", lambda x: x.prazo_meses == 36),
]
rows = []
for nome, f in P:
    g = M[f(M)]
    rows.append(dict(padrao=nome, taxa_calote=g.y_calote.mean(), taxa_atraso=g.y_atraso.mean(), n_maduros=len(g),
                     taxa_media=base, n_hist_todos=int(f(d).sum()), n_aprov_todos=int(f(ap).sum()),
                     n_novos=nov_ok(f)))
R = pd.DataFrame(rows)
R.to_csv("onda1_frases.csv", index=False)
pd.set_option("display.width", 250)
print(R.round(3).to_string(index=False))
for r in R.itertuples():
    print(f"- Clientes com {r.padrao} tem inadimplencia de {100*r.taxa_calote:.0f}%, contra {100*r.taxa_media:.0f}% da media. "
          f"Afeta {r.n_hist_todos} clientes da base historica ({r.n_maduros} aprovados maduros; {r.n_novos} dos 2.000 novos).")
