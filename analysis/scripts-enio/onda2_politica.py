"""Onda 2 / itens 5, 6, 7, 8: efeito do valor, erros da politica atual, piloto, sensiveis, simulacao financeira.
python analise/onda2_politica.py
Ganho por contrato (manual): em dia +15% do valor aprovado; atraso +5%; nao paga -60%; negado 0.
Contratos em andamento: so entram os MADUROS (pedido <= 30/09/2025, >=12 parcelas vencidas); 'em_atraso' conta como atraso.
"""
import numpy as np
import pandas as pd
import psycopg
from base import carregar, DSN, parcela_price
from util import extras

np.random.seed(42)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)

d = extras(carregar())
# flags de movimentacao mes a mes (lag 1 = mes anterior ao pedido)
with psycopg.connect(DSN) as c:
    mov = pd.DataFrame(c.execute("select id_cliente, mes_referencia, total_entradas, total_saidas, dias_cheque_especial "
                                 "from hackathon.movimentacao_mensal").fetchall(), columns=["id_cliente", "mes", "ent", "sai", "cheq"])
mov[["ent", "sai"]] = mov[["ent", "sai"]].astype(float)
mov["mes"] = pd.to_datetime(mov.mes)
mov = mov.merge(d[["id_cliente", "data_pedido"]], on="id_cliente")
mov["lag"] = (mov.data_pedido.dt.year * 12 + mov.data_pedido.dt.month) - (mov.mes.dt.year * 12 + mov.mes.dt.month)
m3 = mov[mov.lag <= 3]
fl = pd.DataFrame({"saque3": m3[m3.sai > m3.ent].groupby("id_cliente").size() > 0,
                   "cheq2": m3[(m3.lag <= 2) & (m3.cheq > 0)].groupby("id_cliente").size() > 0})
d = d.merge(fl, left_on="id_cliente", right_index=True, how="left")
d[["saque3", "cheq2"]] = d[["saque3", "cheq2"]].fillna(False).astype(bool)
d["S"] = d.saque3 | d.cheq2
d["renda_real"] = d[["renda_declarada", "ent_media"]].min(axis=1)
d["parc_aprov_real"] = d.parcela_aprov / d.renda_real
d["parc_sol_real"] = d.parcela_sol / d.renda_real

ap = d[d.decisao == "aprovado"].copy()
M = ap[ap.data_pedido <= "2025-09-30"].copy()
GAN = {"em_dia": 0.15, "atraso": 0.05, "nao_paga": -0.60}
M["ganho"] = M.valor_aprovado * M.classe.map(GAN)
print(f"maduros n={len(M)}  ganho real da politica atual = R$ {M.ganho.sum():,.0f}  (volume aprovado R$ {M.valor_aprovado.sum():,.0f})")

# ---------- 5. efeito do valor ----------
print("\n=== 5. VALOR: calote por parcela aprovada / renda real (min(renda declarada, entradas medias)), sem estresse ===")
N = M[~M.S]
b = [0, .1, .15, .2, .22, .24, .26, .28, .30, .32, .35, .4, 2]
for v in ["parc_aprov_real", "parc_aprov_ent", "parc_aprov_renda"]:
    t = N.groupby(pd.cut(N[v], b), observed=True).agg(n=("y_calote", "size"), cal=("y_calote", "mean"), atr=("y_atraso", "mean"))
    t["ganho_por_R$"] = 0.15 * (1 - t.cal - t.atr) + 0.05 * t.atr - 0.6 * t.cal
    print(v); print(t.round(3).T.to_string())

print("\n347 reduzidos: regra = teto de parcela em % da renda declarada")
r = ap[ap.reduzido]
print(r.groupby("politica_aplicada").parc_aprov_renda.describe().round(3).to_string())
rm = M[M.reduzido & ~M.S]
nr = N[(~N.reduzido) & (N.parc_aprov_renda.between(0.26, 0.305))]
print(f"reduzidos maduros sem estresse: n={len(rm)} calote={rm.y_calote.mean():.3f} | nao reduzidos com parcela 26-30% da renda: n={len(nr)} calote={nr.y_calote.mean():.3f}")
print("reduzidos por parcela/entradas:", rm.groupby(pd.cut(rm.parc_aprov_ent, [0, .25, .28, .3, .35, 2]), observed=True).y_calote.agg(["size", "mean"]).round(3).T.to_string())

# ---------- 6a. quem a atual aprova e nao paga ----------
print("\n=== 6a. calotes da politica atual (maduros): o que os denuncia ===")
cal = M[M.y_calote == 1]
print(f"calotes {len(cal)}: estresse de conta {cal.S.mean():.1%} | parcela>28% renda real {(cal.parc_aprov_real>0.28).mean():.1%} | "
      f"um dos dois {((cal.S)|(cal.parc_aprov_real>0.28)).mean():.1%} | nenhum {(~cal.S & (cal.parc_aprov_real<=0.28)).mean():.1%}")
ok = M[~M.S & (M.parc_aprov_real <= 0.28)]
print(f"aprovados sem nenhum dos dois: n={len(ok)} calote={ok.y_calote.mean():.3f} atraso={ok.y_atraso.mean():.3f}")

# ---------- 6b. piloto: quem a atual negaria ----------
ap["cal3"] = np.where(ap.n_vencidas >= 6, (ap.parc_1o_90 <= 3).astype(float), np.nan)
W = ap[(ap.data_pedido >= "2025-10-01") & (ap.data_pedido <= "2026-03-31")].copy()
fator = M.y_calote.mean() / ap[ap.data_pedido <= "2025-09-30"].cal3.mean()
print(f"\n=== 6b. piloto (out/25-mar/26; alvo cal3 = 90+ dias ja na parcela 1-3; nos maduros cal3 x {fator:.2f} = calote final) ===")
W["grupo"] = np.select([W.politica_aplicada == "atual", W.regra_atual], ["atual", "piloto_passa_atual"], "piloto_atual_negaria")
W["limpo"] = ~W.S & (W.parc_aprov_real <= 0.28)
t = W.groupby(["grupo", "limpo"]).agg(n=("cal3", "size"), cal3=("cal3", "mean"), atraso_ate_hoje=("atraso_max", lambda s: ((s > 0) & (s < 90)).mean()))
t["calote_final_estimado"] = t.cal3 * fator
print(t.round(3).to_string())
P = W[(W.grupo == "piloto_atual_negaria") & W.limpo]
P = P.assign(motivo=np.select([P.restricoes_ativas > 0, P.score <= 600, P.renda_declarada <= 2000, P.parc_renda > 0.30],
                              ["restricao=1", "score<=600", "renda<=2000", "parcela>30% renda"], "outro"))
t = P.groupby("motivo").agg(n=("cal3", "size"), cal3=("cal3", "mean"))
t["calote_final_estimado"] = t.cal3 * fator
print("piloto 'atual negaria' e limpo, por motivo:"); print(t.round(3).to_string())
print("score (piloto limpo, todos):", W[W.limpo & (W.politica_aplicada == "piloto")].groupby(pd.cut(W.score, [0, 500, 550, 600, 700, 800, 1001]), observed=True).cal3.agg(["size", "mean"]).round(3).T.to_string())

# ---------- 7. sensiveis / estranhos, com conferencia temporal ----------
print("\n=== 7. atributos sensiveis/estranhos (maduros limpos; antigos <=mar/25 x novos abr-set/25) ===")
ok = ok.assign(per=np.where(ok.data_pedido <= "2025-03-31", "antigo", "novo"))
for c in ["genero", "estado_civil", "uf_cep1", "tipo_vinculo", "profissao"]:
    t = ok.groupby([c, "per"]).y_calote.agg(["size", "mean"]).unstack()
    t = t[(t[("size", "antigo")] >= 25) & (t[("size", "novo")] >= 25)]
    print(c); print(t.round(3).to_string())
ok["dia"] = ok.data_pedido.dt.day
print("dia do mes:", ok.groupby(pd.cut(ok.dia, [0, 5, 10, 15, 20, 25, 31])).y_calote.agg(["size", "mean"]).round(3).T.to_string())
ok["ano_conta"] = ok.data_abertura_conta.dt.year
print("ano abertura conta:", ok.groupby("ano_conta").y_calote.agg(["size", "mean"]).round(3).T.to_string())
print("idade:", ok.groupby(pd.cut(ok.idade, [0, 25, 30, 40, 50, 60, 70, 100])).y_calote.agg(["size", "mean"]).round(3).T.to_string())

# ---------- 8. simulacao financeira no historico maduro ----------
print("\n=== 8. SIMULACAO (maduros, politica atual como referencia) ===")


def simula(nome, aprova, df=M):
    g = df[aprova(df)]
    out = dict(politica=nome, aprovados=len(g), volume=g.valor_aprovado.sum(), ganho=g.ganho.sum(),
               calote=g.y_calote.mean(), atraso=g.y_atraso.mean())
    out["delta_vs_atual"] = out["ganho"] - df.ganho.sum()
    return out


R = [simula("atual (real)", lambda x: x.decisao == "aprovado"),
     simula("atual - estresse de conta", lambda x: ~x.S),
     simula("atual - parcela>28% renda real", lambda x: x.parc_aprov_real <= 0.28),
     simula("atual - estresse - parc>28% renda real", lambda x: ~x.S & (x.parc_aprov_real <= 0.28)),
     simula("atual - estresse - parc>25% renda real", lambda x: ~x.S & (x.parc_aprov_real <= 0.25)),
     simula("atual - estresse - parc>30% entradas", lambda x: ~x.S & (x.parc_aprov_ent <= 0.30)),
     simula("atual - estresse - parc>28% entradas", lambda x: ~x.S & (x.parc_aprov_ent <= 0.28)),
     simula("atual - estresse - parc>25% renda decl.", lambda x: ~x.S & (x.parc_aprov_renda <= 0.25))]
for X in [0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32]:
    R.append(simula(f"  varre teto renda real {X:.2f}", lambda x, X=X: ~x.S & (x.parc_aprov_real <= X)))
T = pd.DataFrame(R)
print(T.round(3).to_string(index=False))
# conferencia temporal do ganho
for per, sub in [("antigos <=mar/25", M[M.data_pedido <= "2025-03-31"]), ("novos abr-set/25", M[M.data_pedido > "2025-03-31"])]:
    a = simula("atual", lambda x: x.decisao == "aprovado", sub)
    b_ = simula("proposta", lambda x: ~x.S & (x.parc_aprov_real <= 0.28), sub)
    print(f"{per}: atual R$ {a['ganho']:,.0f} | proposta (negar) R$ {b_['ganho']:,.0f} | delta R$ {b_['delta_vs_atual']:,.0f}")

# reduzir em vez de negar: quem passa do teto recebe valor com parcela = teto; risco estimado pela curva
cap = 0.25
Mx = M[~M.S].copy()
exced = Mx.parc_aprov_real > 0.28
v_cap = (cap * Mx.renda_real * (1 - 1.03 ** (-Mx.prazo_meses)) / 0.03).clip(upper=Mx.valor_aprovado)
v_cap = np.floor(v_cap / 100) * 100
ref = Mx[(Mx.parc_aprov_real > 0.20) & (Mx.parc_aprov_real <= 0.28)]
pc, pa = ref.y_calote.mean(), ref.y_atraso.mean()
g_red = (v_cap[exced] * (0.15 * (1 - pc - pa) + 0.05 * pa - 0.6 * pc)).sum()
g_ok = Mx[~exced].ganho.sum()
print(f"\nREDUZIR (nao negar) os {exced.sum()} acima de 28%: valor com parcela={cap:.0%} da renda real; risco assumido = faixa 20-28% "
      f"(calote {pc:.3f}, atraso {pa:.3f}, n={len(ref)}) -> ganho extra R$ {g_red:,.0f}; total R$ {g_ok+g_red:,.0f} vs atual R$ {M.ganho.sum():,.0f}")
print("  ATENCAO: os reduzidos pela atual ao teto de 30% da renda declarada pagaram mal (ver item 5); reduzir so e seguro abaixo de ~25%.")

d.to_pickle("_base_flags.pkl")
