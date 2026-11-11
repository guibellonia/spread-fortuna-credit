"""Resultado esperado (R$) das políticas A, B, C, G e da política própria nos 2.000 novos."""
import os, sys, numpy as np, pandas as pd
import tool_risco as t

AQUI = t.AQUI
GRADE = os.path.join(AQUI, "grade_novos.pkl")
CEN = {"base": 1.0, "pessimista": 1.2, "otimista": 0.8}

def montar_grade(modelo):
    nov = t.carregar_pedidos("novo").reset_index(drop=True)
    assert nov["score"].notna().all(), "bureau faltando"
    linhas = []
    for _, r in nov.iterrows():
        for c in t.candidatos_valor(r["valor_solicitado"], r["renda"], r["prazo"], renda_max=None):
            linhas.append((r["id_pedido"], c))
    g = pd.DataFrame(linhas, columns=["id_pedido", "valor"])
    out = []
    for prazo, sub in g.merge(nov[["id_pedido", "prazo"]]).groupby("prazo"):
        for i in range(0, len(sub), 20000):
            ch = sub.iloc[i:i+20000]
            b = nov.set_index("id_pedido").loc[ch["id_pedido"]].reset_index()
            p = t.prever_df(b, ch["valor"].values, modelo)
            p["id_pedido"] = ch["id_pedido"].values
            out.append(p)
    grade = pd.concat(out, ignore_index=True)
    return nov, grade

def cenario(p_ok, p_d, v, f):
    pd_ = np.clip(p_d * f, 0, 1); pok = np.minimum(p_ok, 1 - pd_); pl = 1 - pd_ - pok
    return v * (0.15 * pok + 0.05 * pl - 0.60 * pd_)

def escolhe(grade, nov, filtro_ids, renda_max, pd_max, fator_obj=1.0):
    """Para cada pedido elegível, valor de maior ganho esperado (sob fator_obj) com
    parcela <= renda_max*renda e P(não paga) <= pd_max; nega se nada tem ganho > 0."""
    g = grade[grade["id_pedido"].isin(filtro_ids)].copy()
    if renda_max is not None:
        g = g[g["parcela_renda"] <= renda_max + 1e-12]
    eg = cenario(g["p_em_dia"].values, g["p_nao_paga"].values, g["valor"].values, fator_obj)
    pdx = np.clip(g["p_nao_paga"].values * fator_obj, 0, 1)
    g = g.assign(eg_obj=eg)
    if pd_max is not None:
        g = g[pdx <= pd_max + 1e-12]
    g = g[g["eg_obj"] > 0]
    best = g.loc[g.groupby("id_pedido")["eg_obj"].idxmax()]
    return dict(zip(best["id_pedido"], best["valor"]))

def avaliar(dec, nov, modelo):
    """dec: {id_pedido: valor}. Devolve ganho esperado por cenário, nº aprovados, volume."""
    ids = [i for i, v in dec.items() if v > 0]
    if not ids:
        return {"aprovados": 0}
    b = nov.set_index("id_pedido").loc[ids].reset_index()
    v = np.array([dec[i] for i in ids])
    p = t.prever_df(b, v, modelo)
    r = {"aprovados": len(ids), "volume": v.sum(), "pd_media_pond": (p["p_nao_paga"] * v).sum() / v.sum()}
    for c, f in CEN.items():
        r[c] = cenario(p["p_em_dia"].values, p["p_nao_paga"].values, v, f).sum()
    return r

def politica_A(nov):
    dec = {}
    for _, r in nov.iterrows():
        if r["score"] > 600 and r["renda"] > 2000 and r["restricoes_ativas"] == 0:
            v = min(r["valor_solicitado"], 30000.0)
            if t.parcela_price(v, r["prazo"]) > 0.30 * r["renda"]:
                v = np.floor(t.valor_max_por_parcela(0.30 * r["renda"], r["prazo"]) * 100) / 100
                while t.parcela_price(v, r["prazo"]) > 0.30 * r["renda"]:
                    v -= 0.01
            if v >= 500:
                dec[r["id_pedido"]] = round(v, 2)
    return dec

if __name__ == "__main__":
    modelo = t.carregar_modelo()
    if os.path.exists(GRADE) and "--refazer" not in sys.argv:
        nov, grade = pd.read_pickle(GRADE)
    else:
        nov, grade = montar_grade(modelo); pd.to_pickle((nov, grade), GRADE)
    filtroB = set(nov.loc[(nov["restricoes_ativas"] == 0) & (nov["meses_saldo_neg"] <= 1), "id_pedido"])
    filtroC = set(nov.loc[nov["id_pedido"].isin(filtroB) & (nov["score"] > 600), "id_pedido"])
    tudo = set(nov["id_pedido"])
    pols = {"A": politica_A(nov),
            "B": escolhe(grade, nov, filtroB, 0.20, 0.20),
            "C": escolhe(grade, nov, filtroC, 0.20, 0.20),
            "G": escolhe(grade, nov, filtroB, 0.20, 0.175)}
    # busca da política própria: objetivo = ganho no cenário PESSIMISTA (robustez)
    busca = []
    for nome_f, filt in [("sem_filtro", tudo), ("filtroB", filtroB),
                         ("so_restricao", set(nov.loc[nov["restricoes_ativas"] == 0, "id_pedido"]))]:
        for rm in [0.15, 0.20, 0.25, 0.30, 0.40, None]:
            for pm in [0.10, 0.125, 0.15, 0.175, 0.20, 0.25, None]:
                for fo in [1.0, 1.2]:
                    d = escolhe(grade, nov, filt, rm, pm, fo)
                    r = avaliar(d, nov, modelo)
                    busca.append({"filtro": nome_f, "renda_max": rm, "pd_max": pm, "fator_obj": fo, **r})
    bz = pd.DataFrame(busca).sort_values("pessimista", ascending=False)
    bz.to_csv(os.path.join(AQUI, "busca_politicas.csv"), index=False)
    print("Top 10 da busca (ordenado pelo cenário pessimista):")
    print(bz.head(10).round(0).to_string(index=False))
    res = {k: avaliar(v, nov, modelo) for k, v in pols.items()}
    print("\nResultado esperado (R$) nos 2.000 novos:")
    tab = pd.DataFrame(res).T
    print(tab.round(3).to_string())
    pd.to_pickle({"pols": pols, "nov": nov}, os.path.join(AQUI, "_pols.pkl"))
