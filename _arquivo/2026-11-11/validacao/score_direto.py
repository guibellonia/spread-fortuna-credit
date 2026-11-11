"""Tarefa 4: inadimplência medida direto nos dados (sem modelo), com correção de censura por
Kaplan-Meier em tempo de contrato (nº da parcela), IC 95% por bootstrap de contratos."""
import numpy as np, pandas as pd
import tool_risco as t

d, a, ped, par = t.painel_parcelas()   # d: linhas parcela-risco de inadimplência (censura já tratada)
ped = t.com_valor(ped, ped["valor_aprovado"].values)
K = 22   # inadimplências ocorrem até ~60% do prazo; k<=22 cobre ~toda a vida (ver validar_modelo)
rng = np.random.default_rng(42)

def _km1(dsub, K):
    h = dsub.groupby("k")["y"].agg(["sum", "size"]).reindex(range(1, K + 1)).fillna(0)
    haz = np.where(h["size"] > 0, h["sum"] / h["size"].replace(0, 1), 0)
    return 1 - np.prod(1 - haz)

def km(dsub, K=K):
    """KM estratificado por prazo (contrato que termina sem inadimplir não é censura),
    horizonte min(prazo, K), média ponderada pelo nº de contratos de cada prazo."""
    w = dsub.groupby("prazo")["id_pedido"].nunique()
    return float(sum(w[p] * _km1(dsub[dsub["prazo"] == p], min(int(p), K)) for p in w.index) / w.sum())

def km_boot(ids, B=1000):
    dd = d[d["id_pedido"].isin(ids)]
    grp = {i: g for i, g in dd.groupby("id_pedido")}
    ids = np.array(list(grp))
    est = km(dd)
    # bootstrap: soma de eventos/riscos por k em cada contrato
    mat_e = np.zeros((len(ids), K)); mat_n = np.zeros((len(ids), K))
    for j, i in enumerate(ids):
        g = grp[i]; kk = g["k"].values - 1; m = kk < K
        mat_e[j, kk[m]] = g["y"].values[m]; mat_n[j, kk[m]] = 1
    prz = np.array([int(grp[i]["prazo"].iloc[0]) for i in ids])
    bs = []
    for _ in range(B):
        s = rng.integers(0, len(ids), len(ids))
        tot = 0.0
        for p in np.unique(prz[s]):
            ss = s[prz[s] == p]; kk = min(int(p), K)
            e, n = mat_e[ss, :kk].sum(0), mat_n[ss, :kk].sum(0)
            tot += len(ss) * (1 - np.prod(1 - np.where(n > 0, e / np.maximum(n, 1), 0)))
        bs.append(tot / len(s))
    return est, np.array(bs), len(ids)

def grupo(mask, nome):
    est, bs, n = km_boot(ped.loc[mask, "id_pedido"])
    print(f"{nome:55s} n={n:5d}  inad KM vida = {100*est:5.1f}%  IC95 [{100*np.percentile(bs,2.5):.1f}; {100*np.percentile(bs,97.5):.1f}]"
          f"  (bruto observado {100*(ped.loc[mask,'situacao_final']=='inadimplente').mean():.1f}%)")
    return est, bs

filt = (ped["restricoes_ativas"] == 0) & (ped["meses_saldo_neg"] <= 1) & (ped["parcela_renda"] <= 0.20 + 1e-9)
print("== Filtros B (restrição 0, <=1 mês saldo negativo, parcela <= 20% renda), aprovados históricos")
e1, b1 = grupo(filt & (ped["score"] <= 600), "score <= 600")
e2, b2 = grupo(filt & (ped["score"] > 600), "score > 600")
e3, b3 = grupo(filt & (ped["score"] > 600) & (ped["politica_aplicada"] == "piloto"), "score > 600, só piloto (mesma safra/política)")
diff = b1 - b2; diff3 = b1 - b3
print(f"diferença (<=600) - (>600): {100*(e1-e2):.1f} p.p. IC95 [{100*np.percentile(diff,2.5):.1f}; {100*np.percentile(diff,97.5):.1f}]")
print(f"diferença (<=600) - (>600 piloto): {100*(e1-e3):.1f} p.p. IC95 [{100*np.percentile(diff3,2.5):.1f}; {100*np.percentile(diff3,97.5):.1f}]")
# ganho esperado por R$ emprestado implicado (supondo atraso ~ igual entre grupos: usa só PD)
for e, nm in [(e1, "<=600"), (e2, ">600")]:
    print(f"  ponto de equilíbrio: com PD {100*e:.1f}% o ganho por R$ é no máx. {0.15*(1-e)-0.60*e:+.3f} (se todos os demais pagassem em dia)")
for lo, hi in [(0, 500), (500, 550), (550, 600), (600, 650), (650, 700), (700, 1001)]:
    m = filt & (ped["score"] > lo) & (ped["score"] <= hi)
    if m.sum() > 20:
        grupo(m, f"   score ({lo},{hi}]")
print("\n== Grupos com pouco suporte (aprovados históricos, sem filtro de parcela)")
grupo(ped["restricoes_ativas"] > 0, "restrição ativa >= 1 (só piloto)")
grupo((ped["restricoes_ativas"] == 0) & (ped["politica_aplicada"] == "piloto"), "restrição 0, piloto")
grupo(ped["meses_saldo_neg"] >= 2, "2+ meses com saldo mínimo negativo")
grupo(ped["meses_saldo_neg"] <= 1, "<=1 mês com saldo mínimo negativo")
grupo(ped.index == ped.index, "todos os aprovados")
