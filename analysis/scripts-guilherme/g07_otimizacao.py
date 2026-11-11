"""Etapas 7.2 e 8 · Otimização da política nos 2.000 pedidos novos + fronteira risco × resultado.

Para cada pedido, testa valores candidatos (100%, 95%, ..., 30% do pedido, múltiplos de R$100, >= R$500),
estima PD de vida, P(em dia) e P(atraso) com o modelo final (g05c, ensemble EM) e escolhe o valor de maior
resultado esperado dentro das restrições da política. Resultado por pedido = valor × (0,15·em dia + 0,05·atraso − 0,60·PD).

Para não repetir o erro de auto-avaliação apontado na auditoria (g06), toda política é medida por 3 avaliadores:
  1. modelo final (o mesmo que escolhe — otimista por construção)
  2. KM por célula (sem modelo; g06.AvaliadorKM)
  3. tool_risco (hazard do time, recalibrado por KM; validacao/tool_risco.py)
A escolha da política usa o PIOR ganho entre os avaliadores independentes (2 e 3), não o do modelo próprio.
Saídas: out/g07_otimizacao.md, out/g07_politicas.csv, out/g07_decisoes_melhor_da_grade.csv (formato do manual)
"""
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import g06_auditoria_cenarios as G6  # noqa: E402  (configura db/src/validacao no sys.path)
from g_util import carregar  # noqa: E402
from g05c_modelo_final import prever  # noqa: E402

OUT = AQUI / "out"
FRACOES = np.round(np.arange(1.0, 0.29, -0.05), 2)
L = []


def p(t=""):
    L.append(t)


# ------------------------------------------------------------------ regras de corte (etapas 4–5)
def regras(x: pd.DataFrame) -> pd.DataFrame:
    """Regras que não dependem do valor (as que dependem são tratadas pelo modelo/candidato)."""
    r = pd.DataFrame(index=x.index)
    r["deficit_3m"] = x.deficit_3m >= 1
    r["deficit_2m_12m"] = x.meses_deficit >= 2
    r["cheque_2m_12m"] = x.cheq_meses >= 2
    r["saidas_80pct"] = x.sai_ent >= 0.8
    r["renda_conta_60pct"] = x.renda_ratio < 0.6
    r["restricao"] = x.restricoes_ativas > 0
    r["outras_40pct"] = x.comp_antes >= 0.4
    return r


def candidatos(x, modelo):
    sol = np.minimum(x.valor_solicitado.to_numpy(float), 30000)
    linhas = []
    for f in FRACOES:
        v = np.floor(sol * f / 100) * 100
        v = np.where(f == 1.0, sol, v)
        ok = v >= 500
        pdv, em_dia, atraso = prever(modelo, x, np.where(ok, v, 500))
        g = v * (0.15 * em_dia + 0.05 * atraso - 0.60 * pdv)
        linhas.append(pd.DataFrame({"id_pedido": x.id_pedido.values, "fr": f, "valor": np.where(ok, v, 0), "pd": pdv,
                                    "em_dia": em_dia, "atraso": atraso, "ganho": np.where(ok, g, -np.inf)}))
    return pd.concat(linhas, ignore_index=True)


def politica(x, cand, pd_max=0.175, reduz=True, min_score=0, corta=(), comp_decl_max=None, max_red=None):
    c = cand[cand.valor > 0].copy()
    if not reduz:
        c = c[c.fr == 1.0]
    if max_red is not None:
        c = c[c.fr >= 1 - max_red]
    c = c[(c.pd <= pd_max) & (c.ganho > 0)]
    if comp_decl_max is not None:
        rd = x.set_index("id_pedido").renda_declarada
        parc = c.valor * 0.03 / (1 - 1.03 ** (-x.set_index("id_pedido").prazo_meses.loc[c.id_pedido].values))
        c = c[(parc.values / rd.loc[c.id_pedido].values) <= comp_decl_max]
    best = c.sort_values("ganho", ascending=False).drop_duplicates("id_pedido").set_index("id_pedido")
    dec = pd.DataFrame({"id_pedido": x.id_pedido.values})
    dec["valor"] = dec.id_pedido.map(best.valor).fillna(0.0)
    bloq = np.zeros(len(x), bool)
    if min_score:
        bloq |= (x.score <= min_score).values
    R = regras(x)
    for k in corta:
        bloq |= R[k].values
    dec.loc[bloq, "valor"] = 0.0
    dec["aprova"] = dec.valor > 0
    return dec


def avaliar(dec, x, modelo, km_av, T, mod_tr, ped_novos, xsrc):
    d = dec[dec.valor > 0]
    if d.empty:
        return {}
    v = d.valor.to_numpy(float)
    xi = x.set_index("id_pedido").loc[d.id_pedido].reset_index()
    pdv, em, at = prever(modelo, xi, v)
    res_m = float((v * (0.15 * em + 0.05 * at - 0.60 * pdv)).sum())
    ds = xsrc.set_index("id_pedido").loc[d.id_pedido].reset_index()
    pk = km_av.prever(ds, v)
    res_km, pd_km = G6.avaliar_probs(v, pk[:, 0], pk[:, 1])
    pt = T.prever_df(ped_novos.loc[d.id_pedido].reset_index(), v, mod_tr)
    res_tr, pd_tr = G6.avaliar_probs(v, pt["p_nao_paga"].to_numpy(), pt["p_em_dia"].to_numpy())
    return {"aprovados": len(d), "volume": v.sum(), "ticket": v.mean(), "reduzidos": int((v < np.minimum(xi.valor_solicitado.to_numpy(float), 30000) - 0.01).sum()),
            "res_modelo": res_m, "pd_modelo": float((pdv * v).sum() / v.sum()),
            "res_km": res_km, "pd_km": pd_km, "res_tool": res_tr, "pd_tool": pd_tr}


def main():
    d, hist, ap, novos = carregar()
    x = novos.reset_index(drop=True)
    modelo = joblib.load(OUT / "modelo_final.joblib")
    cand = candidatos(x, modelo)

    # avaliadores independentes (montados como em g06)
    hist_src, xsrc = G6.bases_src()
    import tool_risco as T
    mod_tr = T.carregar_modelo(str(G6.SAIDA_G06 / "tool_risco_full.joblib"))
    ped_novos = T.carregar_pedidos("novo")
    bc = G6.bureau_cache().set_index("id_cliente")
    for c in ["score", "restricoes_ativas", "parcelas_outras_instituicoes", "consultas_90_dias", "meses_historico_bureau"]:
        ped_novos[c] = ped_novos["id_cliente"].map(bc[c]).astype(float)
    ped_novos["outras_renda"] = ped_novos["parcelas_outras_instituicoes"] / ped_novos["renda"]
    ped_novos = ped_novos.set_index("id_pedido")
    ap_hist = hist_src[hist_src.decisao == "aprovado"].reset_index(drop=True)
    ap_out = ap_hist[["id_pedido"]].merge(ap[["id_pedido", "parou", "k_parada", "k_obs", "prazo_meses", "n_decididas",
                                              "k_1o_atraso", "valor_aprovado"]], on="id_pedido", how="left")
    km_av = G6.AvaliadorKM(ap_hist, ap_out.drop(columns=["id_pedido"]))

    aval = lambda dec: avaliar(dec, x, modelo, km_av, T, mod_tr, ped_novos, xsrc)  # noqa: E731

    # política atual e cenários do time (decisões reproduzidas em g06)
    cen = pd.read_pickle(G6.SAIDA_G06 / "cenarios.pkl")["cen"]
    pol = {}
    for k in ["A", "C", "G"]:
        dd = cen[k][["id_pedido", "valor"]].copy()
        pol[f"{k} (time)"] = dd
    corta_todas = ("deficit_3m", "deficit_2m_12m", "cheque_2m_12m", "saidas_80pct", "renda_conta_60pct", "restricao", "outras_40pct")
    grade = []
    for pdm in [0.08, 0.10, 0.12, 0.14, 0.16, 0.175, 0.20, 0.25]:
        for reduz in [True, False]:
            for corta in [(), corta_todas]:
                for ms in [0, 600]:
                    nome = f"pd≤{pdm:.3f} | {'reduz' if reduz else 'sem reduzir'} | {'regras' if corta else 'só modelo'} | score>{ms}"
                    pol[nome] = politica(x, cand, pdm, reduz, ms, corta)
                    grade.append(nome)
    linhas = []
    for nome, dec in pol.items():
        r = aval(dec)
        r["politica"] = nome
        linhas.append(r)
    R = pd.DataFrame(linhas).set_index("politica")
    for c in ["res_modelo", "res_km", "res_tool"]:
        R["ganho_" + c[4:]] = R[c] - R.loc["A (time)", c]
    R["ganho_min_indep"] = R[["ganho_km", "ganho_tool"]].min(axis=1)
    R["ganho_med_indep"] = R[["ganho_km", "ganho_tool"]].mean(axis=1)
    R.to_csv(OUT / "g07_politicas.csv", encoding="utf-8")

    melhor = R.loc[grade].sort_values("ganho_min_indep", ascending=False)
    p("# Saída de g07_otimizacao.py\n")
    p("## 7.2 Grade de políticas (2.000 novos) — ordenada pelo pior ganho entre os avaliadores independentes\n")
    cols = ["aprovados", "volume", "reduzidos", "pd_modelo", "pd_km", "pd_tool", "ganho_modelo", "ganho_km", "ganho_tool", "ganho_min_indep"]
    fm = R[cols].copy()
    for c in ["pd_modelo", "pd_km", "pd_tool"]:
        fm[c] = (100 * fm[c]).round(1)
    for c in ["volume", "ganho_modelo", "ganho_km", "ganho_tool", "ganho_min_indep"]:
        fm[c] = (fm[c] / 1e3).round(0)
    p("Volume e ganhos em R$ mil; PD em % do volume. Ganho = resultado − resultado da política atual (A) no MESMO avaliador.\n")
    p(fm.loc[["A (time)", "C (time)", "G (time)"]].to_markdown())
    p("")
    p(fm.loc[melhor.index[:20]].to_markdown())
    p("\nResultado absoluto da política atual por avaliador (R$ mil): " +
      ", ".join(f"{c[4:]} {R.loc['A (time)', c] / 1e3:.0f}" for c in ["res_modelo", "res_km", "res_tool"]))

    # fronteira: só modelo/regras, reduz, score>0, variando pd_max
    p("\n## Fronteira de eficiência (regras + modelo, com redução de valor, sem corte de score)\n")
    fr = [n for n in grade if "| reduz |" in n and "regras" in n and "score>0" in n]
    p(fm.loc[fr, ["aprovados", "volume", "pd_km", "pd_tool", "ganho_km", "ganho_tool", "ganho_modelo"]].to_markdown())
    fr2 = [n for n in grade if "sem reduzir" in n and "regras" in n and "score>0" in n]
    p("\nMesma fronteira, SEM reduzir valor (aprova o pedido inteiro ou nega):\n")
    p(fm.loc[fr2, ["aprovados", "volume", "pd_km", "pd_tool", "ganho_km", "ganho_tool", "ganho_modelo"]].to_markdown())

    # política recomendada = maior ganho mínimo independente
    rec = melhor.index[0]
    dec = pol[rec].merge(x[["id_pedido", "valor_solicitado"]], on="id_pedido")
    out = pd.DataFrame({"id_pedido": dec.id_pedido,
                        "decisao": np.where(dec.valor > 0, "APROVADO", "NEGADO"),
                        "valor_aprovado": dec.valor.map(lambda v: f"{v:.2f}")})
    assert (dec.valor <= np.minimum(dec.valor_solicitado, 30000) + 0.001).all()
    with open(OUT / "g07_decisoes_melhor_da_grade.csv", "w", encoding="utf-8", newline="") as f:
        out.to_csv(f, index=False, lineterminator="\n")
    p(f"\n**Melhor da grade pelo avaliador padrão (não é a recomendação final; ver g08):** `{rec}` → {OUT.name}/g07_decisoes_melhor_da_grade.csv")

    # comparação de decisões com A e G
    A = pol["A (time)"].set_index("id_pedido").valor
    Gt = pol["G (time)"].set_index("id_pedido").valor
    Rc = pol[rec].set_index("id_pedido").valor
    p("\n### Onde a recomendada difere da atual (A) e do G do time\n")
    tab = pd.DataFrame({
        "aprova A e recomendada": [int(((A > 0) & (Rc > 0)).sum())],
        "só A aprova": [int(((A > 0) & (Rc == 0)).sum())],
        "só recomendada aprova": [int(((A == 0) & (Rc > 0)).sum())],
        "aprova G e recomendada": [int(((Gt > 0) & (Rc > 0)).sum())],
        "só G aprova": [int(((Gt > 0) & (Rc == 0)).sum())],
        "só recomendada (vs G)": [int(((Gt == 0) & (Rc > 0)).sum())],
    })
    p(tab.to_markdown(index=False))
    # motivo dos negados pela recomendada que A aprova
    xa = x.set_index("id_pedido")
    neg = xa.loc[(A > 0) & (Rc == 0)]
    Rg = regras(neg)
    motivos = Rg.sum().sort_values(ascending=False)
    p(f"\nDos {len(neg)} que só A aprova, quantos caem em cada regra (um pedido pode cair em várias):")
    p(motivos.to_frame("pedidos").to_markdown())
    red_A = xa.loc[A.index][(A > 0) & (A < np.minimum(xa.valor_solicitado, 30000) - 0.01)]
    p(f"\nA política atual reduz o valor de {len(red_A)} pedidos aprovados; a recomendada aprova "
      f"{int((Rc.loc[red_A.index] > 0).sum())} deles.")

    # rentabilidade (etapa 8)
    p("\n## 8. Rentabilidade (regra do desafio: +15% em dia, +5% atraso, −60% não paga)\n")
    rr = R.loc[["A (time)", "G (time)", rec]].copy()
    for c, nome in [("res_km", "KM"), ("res_tool", "tool_risco"), ("res_modelo", "modelo próprio")]:
        rr[f"resultado {nome} (R$ mil)"] = (rr[c] / 1e3).round(0)
        rr[f"por R$ concedido ({nome})"] = (rr[c] / rr.volume).round(4)
        rr[f"por cliente aprovado ({nome}, R$)"] = (rr[c] / rr.aprovados).round(0)
    p(rr[[c for c in rr.columns if "R$" in c or "por" in c]].T.to_markdown())
    (OUT / "g07_otimizacao.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
