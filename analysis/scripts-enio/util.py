"""Funcoes comuns de varredura."""
import numpy as np
import pandas as pd


def arred(x):
    """numero 'redondo' mais proximo (1,2,2.5,5 x 10^k)"""
    if x == 0 or not np.isfinite(x):
        return x
    s = np.sign(x)
    x = abs(x)
    k = 10 ** np.floor(np.log10(x))
    cands = np.array([1, 2, 2.5, 5, 10]) * k
    cands = np.concatenate([cands, np.arange(1, 10) * k, np.arange(1, 20) * k / 2])
    return s * cands[np.argmin(abs(cands - x))]


def varre(df, var, y="y_calote", minn=50):
    s = df[[var, y]].dropna()
    if s[var].nunique() < 2:
        return None
    vals = np.unique(s[var].quantile(np.linspace(0.02, 0.98, 97)).values)
    base = s[y].mean()
    best = None
    for c in vals:
        lo = s[s[var] <= c]
        hi = s[s[var] > c]
        if len(lo) < minn or len(hi) < minn:
            continue
        # ganho: estatistica qui-quadrado 2x2
        p1, p2, n1, n2 = lo[y].mean(), hi[y].mean(), len(lo), len(hi)
        chi = (p1 - p2) ** 2 / (base * (1 - base) * (1 / n1 + 1 / n2))
        if best is None or chi > best[0]:
            best = (chi, c, p1, p2, n1, n2)
    if best is None:
        return None
    chi, c, p1, p2, n1, n2 = best
    # degrau: taxa na faixa estreita logo abaixo e logo acima do corte (5% dos dados de cada lado, min 40)
    w = max(40, int(0.05 * len(s)))
    srt = s.sort_values(var)
    below = srt[srt[var] <= c].tail(w)
    above = srt[srt[var] > c].head(w)
    return dict(var=var, corte=c, corte_redondo=arred(c), taxa_le=p1, taxa_gt=p2, n_le=n1, n_gt=n2, chi2=chi,
                taxa_logo_abaixo=below[y].mean(), taxa_logo_acima=above[y].mean(),
                degrau=abs(below[y].mean() - above[y].mean()), base=base, n=len(s))


def extras(ap):
    """derivadas que dependem do valor aprovado / outras dividas"""
    ap = ap.copy()
    ap["parc_aprov_ent"] = ap.parcela_aprov / ap.ent_media
    ap["parc_aprov_ent3"] = ap.parcela_aprov / ap.ent_3m
    ap["parc_ent3"] = ap.parcela_sol / ap.ent_3m
    ap["comprom_ent"] = (ap.parcela_aprov + ap.parcelas_outras_instituicoes) / ap.ent_media
    ap["comprom_renda"] = (ap.parcela_aprov + ap.parcelas_outras_instituicoes) / ap.renda_declarada
    ap["valor_aprov_renda"] = ap.valor_aprovado / ap.renda_declarada
    ap["valor_aprov_ent"] = ap.valor_aprovado / ap.ent_media
    return ap
