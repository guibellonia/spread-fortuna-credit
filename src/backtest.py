"""Backtest: treina até set/2025 e compara as políticas em out/2025–mar/2026 (desfecho conhecido)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from modelo import base_treino, novo_modelo, GANHO, CLASSES
from politica import politica_atual, politica_proposta

def resultado(dec, teste):
    d = dec.merge(teste[["id_pedido", "classe", "decisao", "valor_aprovado"]], on="id_pedido")
    obs = d[d.decisao == "aprovado"]  # só aprovados históricos têm desfecho
    # desfecho observado vale para valor <= aprovado; acima disso, risco não observado -> limitamos ao aprovado
    v = np.minimum(obs["valor"], obs["valor_aprovado"])
    r = (v * GANHO[obs["classe"].to_numpy()]).sum()
    return dict(aprovados=int(d.aprova.sum()), aprov_com_desfecho=int((obs.valor > 0).sum()),
                volume=round(float(v.sum())), resultado=round(float(r)),
                nao_pagou_aprovados=int(((obs.valor > 0) & (obs.classe == 2)).sum()))

def rodar(params=None, verbose=True):
    h = pd.read_pickle(Path(__file__).resolve().parents[1] / "saida" / "hist.pkl")
    ap, X, y = base_treino(h)
    tr = ap.data_pedido <= "2025-09-30"
    m = novo_modelo().fit(X[tr], y[tr])
    teste = h[(h.data_pedido > "2025-09-30") & (h.data_pedido <= "2026-03-31")].copy()
    teste["classe"] = teste["situacao_final"].map(CLASSES).fillna(-1).astype(int)
    a = resultado(politica_atual(teste), teste)
    p = resultado(politica_proposta(teste, m, params), teste)
    if verbose:
        print("atual   ", a); print("proposta", p); print("ganho sobre atual:", p["resultado"] - a["resultado"])
    return a, p

if __name__ == "__main__":
    rodar()
