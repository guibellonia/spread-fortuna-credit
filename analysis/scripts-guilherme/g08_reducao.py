"""Teste decisivo: quanto do ganho das políticas depende de "reduzir o valor baixa o risco"?

No histórico, os 347 contratos reduzidos (todos pela regra dos 30% da renda declarada) têm PD de vida 61% [55–68],
contra ~10% dos não reduzidos com o mesmo comprometimento aprovado (g04). Nenhum modelo consegue medir o efeito de
reduções para outros níveis, porque elas não existem na base.

Avaliador conservador: para pedidos aprovados com valor reduzido, a PD é a do valor PEDIDO (a redução não alivia o
risco) e o resultado incide sobre o valor APROVADO (a redução só diminui a exposição). Aplicado com KM por célula e
com tool_risco. Pedidos não reduzidos são avaliados normalmente.
Saída: out/g08_reducao.md
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
import g06_auditoria_cenarios as G6  # noqa: E402
import g07_otimizacao as G7  # noqa: E402
from g_util import carregar, km_vida  # noqa: E402

OUT = AQUI / "out"


def main():
    d, hist, ap, novos = carregar()
    x = novos.reset_index(drop=True)
    modelo = joblib.load(OUT / "modelo_final.joblib")
    cand = G7.candidatos(x, modelo)
    hist_src, xsrc = G6.bases_src()
    import tool_risco as T
    mod_tr = T.carregar_modelo(str(G6.SAIDA_G06 / "tool_risco_full.joblib"))
    ped = T.carregar_pedidos("novo")
    bc = G6.bureau_cache().set_index("id_cliente")
    for c in ["score", "restricoes_ativas", "parcelas_outras_instituicoes", "consultas_90_dias", "meses_historico_bureau"]:
        ped[c] = ped["id_cliente"].map(bc[c]).astype(float)
    ped["outras_renda"] = ped["parcelas_outras_instituicoes"] / ped["renda"]
    ped = ped.set_index("id_pedido")
    ap_hist = hist_src[hist_src.decisao == "aprovado"].reset_index(drop=True)
    ap_out = ap_hist[["id_pedido"]].merge(ap[["id_pedido", "parou", "k_parada", "k_obs", "prazo_meses", "n_decididas",
                                              "k_1o_atraso", "valor_aprovado"]], on="id_pedido", how="left")
    km_av = G6.AvaliadorKM(ap_hist, ap_out.drop(columns=["id_pedido"]))
    xs = xsrc.set_index("id_pedido")
    xa = x.set_index("id_pedido")

    def avaliar(dec, conservador):
        dd = dec[dec.valor > 0]
        v = dd.valor.to_numpy(float)
        sol = np.minimum(xa.loc[dd.id_pedido, "valor_solicitado"].to_numpy(float), 30000)
        v_risco = np.where(conservador, sol, v)  # valor usado para estimar o risco
        ds = xs.loc[dd.id_pedido].reset_index()
        pk = km_av.prever(ds, v_risco)
        r_km, _ = G6.avaliar_probs(v, pk[:, 0], pk[:, 1])
        pt = T.prever_df(ped.loc[dd.id_pedido].reset_index(), v_risco, mod_tr)
        r_tr, _ = G6.avaliar_probs(v, pt["p_nao_paga"].to_numpy(), pt["p_em_dia"].to_numpy())
        red = v < sol - 0.01
        return {"aprovados": len(dd), "volume": v.sum(), "reduzidos": int(red.sum()),
                "pedido>30% renda decl.": int((xa.loc[dd.id_pedido, "comp_decl_solic"].to_numpy() > 0.30).sum()),
                "res_km": r_km, "res_tool": r_tr}

    cen = pd.read_pickle(G6.SAIDA_G06 / "cenarios.pkl")["cen"]
    pols = {k: cen[k][["id_pedido", "valor"]] for k in ["A", "B", "C", "G", "H"]}
    # G sem reduções: (a) reduzidos recebem o valor pedido; (b) reduzidos são negados
    Gd = cen["G"][["id_pedido", "valor"]].copy()
    sol = np.minimum(xa.loc[Gd.id_pedido, "valor_solicitado"].to_numpy(float), 30000)
    red = (Gd.valor.to_numpy() > 0) & (Gd.valor.to_numpy() < sol - 0.01)
    Ga = Gd.copy(); Ga.loc[red, "valor"] = sol[red]
    Gb = Gd.copy(); Gb.loc[red, "valor"] = 0.0
    pols["G, reduzidos negados"] = Gb
    pols["G, reduzidos com valor pedido"] = Ga
    acima30 = xa.loc[Gd.id_pedido, "comp_decl_solic"].to_numpy() > 0.30
    Gh = Gd.copy(); Gh.loc[red & acima30, "valor"] = 0.0
    pols["G, nega só reduções de pedidos > 30% da renda"] = Gh
    pss = np.where(xa.sobra_media.to_numpy() > 0,
                   (xa.parcela_solic / xa.sobra_media).to_numpy(), np.inf)
    pss = pd.Series(pss, index=xa.index).loc[Gd.id_pedido].to_numpy()
    Gs = Gd.copy(); Gs.loc[red & ((pss >= 0.5) | acima30), "valor"] = 0.0
    pols["G, nega reduções (pedido > 30% renda ou parcela ≥ 50% da sobra)"] = Gs
    for pdm in [0.12, 0.16, 0.20]:
        pols[f"próprio: pd≤{pdm} sem reduzir, só modelo"] = G7.politica(x, cand, pdm, False, 0, ())
        pols[f"próprio: pd≤{pdm} com redução, só modelo"] = G7.politica(x, cand, pdm, True, 0, ())
    pols["próprio: pd≤0.16 sem reduzir + regras saídas"] = G7.politica(
        x, cand, 0.16, False, 0, ("deficit_3m", "deficit_2m_12m", "saidas_80pct", "renda_conta_60pct"))

    linhas = []
    for nome, dec in pols.items():
        dec = dec.merge(x[["id_pedido"]], on="id_pedido")
        for cons in [False, True]:
            r = avaliar(dec, cons)
            r.update({"politica": nome, "avaliador": "conservador p/ redução" if cons else "padrão"})
            linhas.append(r)
    R = pd.DataFrame(linhas)
    base = R[R.politica == "A"].set_index("avaliador")[["res_km", "res_tool"]]
    R["ganho_km"] = R.apply(lambda r: r.res_km - base.loc[r.avaliador, "res_km"], axis=1)
    R["ganho_tool"] = R.apply(lambda r: r.res_tool - base.loc[r.avaliador, "res_tool"], axis=1)
    R["ganho_min"] = R[["ganho_km", "ganho_tool"]].min(axis=1)
    piv = R.pivot_table(index="politica", columns="avaliador", values=["ganho_km", "ganho_tool", "ganho_min"])
    piv = (piv / 1e3).round(0)
    info = R[R.avaliador == "padrão"].set_index("politica")[["aprovados", "volume", "reduzidos", "pedido>30% renda decl."]]
    info["volume"] = (info.volume / 1e6).round(2)
    piv.columns = [f"{a} · {b}" for a, b in piv.columns]
    t = info.join(piv)
    t = t.sort_values("ganho_min · conservador p/ redução", ascending=False)
    # reduzidos do G: o que eles pediam
    gx = xa.loc[Gd.id_pedido[red]]
    L = ["# Saída de g08_reducao.py\n",
         "Ganho sobre a política atual (R$ mil) no mesmo avaliador. 'conservador p/ redução' = PD do valor pedido, "
         "resultado sobre o valor aprovado (o que o histórico mostrou nos 347 reduzidos).\n",
         t.to_markdown(),
         f"\nReduções do G: {red.sum()} pedidos; parcela pedida / renda declarada: mediana {gx.comp_decl_solic.median():.2f}, "
         f"{(gx.comp_decl_solic > 0.30).sum()} acima de 30%; redução mediana {(1 - Gd.valor[red].to_numpy() / sol[red]).mean():.0%} do valor.",
         f"Resultado absoluto de A (R$ mil): padrão KM {base.loc['padrão','res_km']/1e3:.0f} / tool {base.loc['padrão','res_tool']/1e3:.0f}; "
         f"conservador KM {base.loc['conservador p/ redução','res_km']/1e3:.0f} / tool {base.loc['conservador p/ redução','res_tool']/1e3:.0f}."]
    (OUT / "g08_reducao.md").write_text("\n".join(L), encoding="utf-8")
    R.to_csv(OUT / "g08_reducao.csv", index=False, encoding="utf-8")
    # decisões da política recomendada (G do time + negar reduções de pedidos acima da capacidade)
    rec = pols["G, nega reduções (pedido > 30% renda ou parcela ≥ 50% da sobra)"].merge(
        x[["id_pedido", "valor_solicitado"]], on="id_pedido")
    assert len(rec) == 2000 and rec.id_pedido.is_unique
    assert (rec.valor <= np.minimum(rec.valor_solicitado, 30000) + 0.001).all()
    out = pd.DataFrame({"id_pedido": rec.id_pedido, "decisao": np.where(rec.valor > 0, "APROVADO", "NEGADO"),
                        "valor_aprovado": rec.valor.map(lambda v: f"{v:.2f}")})
    with open(OUT / "g08_decisoes_recomendadas.csv", "w", encoding="utf-8", newline="") as f:
        out.to_csv(f, index=False, lineterminator="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
