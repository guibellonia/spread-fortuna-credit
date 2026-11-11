"""Estimadores comuns: inadimplência de vida inteira corrigida para censura, com IC 95%.

Por que não usar "parou / aprovados": 4.523 dos 6.033 contratos ainda estavam abertos no corte (30/09/2026).
Contratos novos ainda não tiveram tempo de parar; a taxa ingênua subestima o risco (10,4% vs ~15%).

km_vida(): Kaplan-Meier no tempo RELATIVO do contrato (parcela / prazo), para juntar prazos diferentes.
  evento  = parar de pagar na parcela k (t = k/prazo)
  censura = última parcela decidida (t = k_obs/prazo) de quem não parou
  PD vida = 1 - S(1). Variância de Greenwood -> IC 95% (normal, truncado em [0,1]).
  Hipótese: o risco no tempo relativo é o mesmo entre prazos (a parada observada vai até ~2/3 do prazo
  em 6, 12 e 18 meses; para 24 e 36 é extrapolada). Fica explícita no relatório.

km_em_dia(): mesmo método para "primeiro atraso OU parada" -> P(pagar tudo em dia) = S_any(1).
  P(atraso, mas paga) = 1 - P(em dia) - PD.

proj_w(): o estimador do time (analysis/censura-agregado.md), para comparação.
"""
import numpy as np
import pandas as pd

GANHO_EM_DIA, GANHO_ATRASO, PERDA = 0.15, 0.05, -0.60


def _km(t, e):
    t = np.asarray(t, float)
    e = np.asarray(e, bool)
    if len(t) == 0:
        return np.nan, np.nan
    ordem = np.argsort(t)
    t, e = t[ordem], e[ordem]
    tempos = np.unique(t[e])
    S, var_soma = 1.0, 0.0
    for u in tempos:
        n = (t >= u).sum()
        d = ((t == u) & e).sum()
        if n <= 0:
            continue
        S *= 1 - d / n
        if n > d:
            var_soma += d / (n * (n - d))
    se = S * np.sqrt(var_soma)
    return S, se


def km_vida(g: pd.DataFrame):
    """g precisa de: parou (bool), k_parada, k_obs, prazo_meses. Retorna (pd, li, ls)."""
    g = g[g.k_obs.fillna(0) > 0]
    t = np.where(g.parou, g.k_parada, g.k_obs) / g.prazo_meses
    S, se = _km(t, g.parou.values)
    pdv = 1 - S
    return pdv, max(0.0, pdv - 1.96 * se), min(1.0, pdv + 1.96 * se)


def km_em_dia(g: pd.DataFrame):
    g = g[g.k_obs.fillna(0) > 0]
    k_evt = np.fmin(g.k_parada.fillna(np.inf), g.k_1o_atraso.fillna(np.inf))
    evt = np.isfinite(k_evt)
    t = np.where(evt, k_evt, g.k_obs) / g.prazo_meses
    S, _ = _km(t, evt)
    return S


def proj_w(g: pd.DataFrame):
    g = g[g.k_obs.fillna(0) > 0]
    jan = np.ceil(g.prazo_meses * 2 / 3)
    w = np.where(g.parou, 1.0, np.minimum(g.n_decididas, jan) / jan)
    return g.parou.sum() / w.sum() if w.sum() else np.nan


def resumo_grupo(g: pd.DataFrame) -> dict:
    """Linha de tabela de risco para um grupo de contratos aprovados."""
    pdv, li, ls = km_vida(g)
    em_dia = km_em_dia(g)
    atraso = max(0.0, 1 - em_dia - pdv)
    margem = GANHO_EM_DIA * em_dia + GANHO_ATRASO * atraso + PERDA * pdv
    # fração do prazo já observada no contrato mais maduro do grupo; < 0,6 = KM não chega à janela de parada
    t_max = float((g.k_obs.fillna(0) / g.prazo_meses).max())
    return {
        "contratos": len(g), "pararam": int(g.parou.sum()), "ingenua": g.parou.mean(),
        "aviso": "" if t_max >= 0.6 else "censura pesada (truncado)",
        "pd_vida": pdv, "ic_inf": li, "ic_sup": ls, "proj_time": proj_w(g),
        "p_em_dia": em_dia, "p_atraso": atraso, "margem_R$": margem,
        "volume": g.valor_aprovado.sum(),
    }


def tabela(ap: pd.DataFrame, por, ordem=None, min_n=30) -> pd.DataFrame:
    linhas = []
    for k, g in ap.groupby(por, observed=True, dropna=False):
        if len(g) < min_n:
            r = {"contratos": len(g), "obs": f"n<{min_n}: não estimado"}
        else:
            r = resumo_grupo(g)
        r["grupo"] = k
        linhas.append(r)
    t = pd.DataFrame(linhas).set_index("grupo")
    if ordem is not None:
        t = t.reindex([o for o in ordem if o in t.index])
    return t


def fmt(t: pd.DataFrame) -> str:
    """Tabela em Markdown com % formatados."""
    t = t.copy()
    for c in ["ingenua", "pd_vida", "ic_inf", "ic_sup", "proj_time", "p_em_dia", "p_atraso"]:
        if c in t:
            t[c] = t[c].map(lambda v: "" if pd.isna(v) else f"{100 * v:.1f}%")
    if "margem_R$" in t:
        t["margem_R$"] = t["margem_R$"].map(lambda v: "" if pd.isna(v) else f"{v:+.3f}")
    if "volume" in t:
        t["volume"] = t["volume"].map(lambda v: "" if pd.isna(v) else f"{v / 1e6:.2f} mi")
    if "ic_inf" in t and "ic_sup" in t:
        t["IC95"] = t["ic_inf"].astype(str) + " – " + t["ic_sup"].astype(str)
        t = t.drop(columns=["ic_inf", "ic_sup"])
    return t.to_markdown()


def carregar():
    from pathlib import Path
    d = pd.read_pickle(Path(__file__).resolve().parent / "out" / "base.pkl")
    hist = d[d.tipo_base == "historico"].copy()
    ap = hist[hist.decisao == "aprovado"].copy()
    novos = d[d.tipo_base == "novo"].copy()
    return d, hist, ap, novos
