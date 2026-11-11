"""Validação fora do tempo do modelo de hazard (tool_risco)."""
import os, numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import tool_risco as t

CORTE = pd.Timestamp("2026-09-30")

def horizonte_e_obs(par, ids, corte):
    """Para cada contrato: h = nº de parcelas com desfecho de inadimplência conhecido no corte,
    obs_inad (inadimplência observada até o corte) e obs_atraso (qualquer atraso observado)."""
    p = par[par["id_pedido"].isin(ids)]
    det = p["data_vencimento"] <= corte - pd.Timedelta(days=t.DIAS_DETERMINACAO)
    g = p.assign(det=det, inad=p["status"].eq("inad"),
                 atr=p["status"].isin(["atraso", "inad"]) | p["atraso_certo"]).groupby("id_pedido")
    return pd.DataFrame({"h": g["det"].sum(), "obs_inad": g["inad"].any().astype(int),
                         "obs_atraso": g["atr"].any().astype(int)})

def calib(pred, obs, nome, q=5):
    df = pd.DataFrame({"p": pred, "y": obs})
    df["faixa"] = pd.qcut(df["p"].rank(method="first"), q, labels=False)
    tab = df.groupby("faixa").agg(n=("y", "size"), previsto=("p", "mean"), observado=("y", "mean"))
    print(f"  calibração {nome} (quintis de risco previsto):")
    print((tab.assign(previsto=lambda x: (100*x.previsto).round(1), observado=lambda x: (100*x.observado).round(1))).to_string())

def avalia(modelo, ped, par, corte, titulo):
    ho = horizonte_e_obs(par, ped["id_pedido"], corte)
    b = ped.set_index("id_pedido").join(ho, how="inner")
    b = b[b["h"] > 0].reset_index()
    pr = t.prever_df(b, b["valor_aprovado"].values, modelo, ate_k=b["h"].values)
    p_atr_any = 1 - pr["p_em_dia"]
    print(f"\n== {titulo}: n={len(b)} contratos, horizonte médio {b['h'].mean():.1f} parcelas")
    print(f"  AUC inadimplência: {roc_auc_score(b['obs_inad'], pr['p_nao_paga']):.3f} | "
          f"AUC qualquer atraso: {roc_auc_score(b['obs_atraso'], p_atr_any):.3f}")
    print(f"  inad prevista no horizonte {100*pr['p_nao_paga'].mean():.2f}% vs observada {100*b['obs_inad'].mean():.2f}%")
    print(f"  qualquer atraso previsto {100*p_atr_any.mean():.2f}% vs observado {100*b['obs_atraso'].mean():.2f}%")
    calib(pr["p_nao_paga"].values, b["obs_inad"].values, "inadimplência")
    # vida inteira (projeção) para o mesmo grupo
    lt = t.prever_df(b, b["valor_aprovado"].values, modelo)
    print(f"  projeção vida inteira: inad {100*lt['p_nao_paga'].mean():.2f}% | atraso {100*lt['p_atraso'].mean():.2f}% | em dia {100*lt['p_em_dia'].mean():.2f}%")
    return b, pr

# V1: corte simulado em 30/09/2025 -> treina só com o que se sabia então; testa o que
# aconteceu depois com OS MESMOS contratos (valida a projeção além do horizonte = censura)
cam1 = os.path.join(t.AQUI, "_val_corte2025.joblib")
print(t.treinar(cam1, corte="2025-09-30"))
m1 = t.carregar_modelo(cam1)
_, _, ped_all, par_real = t.painel_parcelas("2026-09-30")
_, _, ped_25, par_25 = t.painel_parcelas("2025-09-30")
h25 = horizonte_e_obs(par_25, ped_25["id_pedido"], pd.Timestamp("2025-09-30"))["h"]
ped_v1 = ped_all[ped_all["id_pedido"].isin(ped_25["id_pedido"])]
b, pr = avalia(m1, ped_v1, par_real, CORTE, "V1 corte simulado 30/09/2025, desfecho em 30/09/2026 (mesmos contratos)")
b["h25"] = b["id_pedido"].map(h25).fillna(0)
ext = b["h"] > b["h25"]
pr25 = t.prever_df(b, b["valor_aprovado"].values, m1, ate_k=b["h25"].clip(lower=0).values)
# inadimplências novas surgidas depois do corte simulado vs previstas (condicional não modelada: aproximação)
print(f"  horizonte médio no corte simulado {b['h25'].mean():.1f} -> real {b['h'].mean():.1f} parcelas")

# V2: treina com pedidos até 30/09/2025 (desfecho até o corte real) e testa nos pedidos
# out/2025-set/2026 (fora do tempo)
cam2 = os.path.join(t.AQUI, "_val_oot.joblib")
print(t.treinar(cam2, corte="2026-09-30", ate_data_pedido="2025-09-30"))
m2 = t.carregar_modelo(cam2)
ped_oot = ped_all[pd.to_datetime(ped_all["data_pedido"]) > pd.Timestamp("2025-09-30")]
avalia(m2, ped_oot, par_real, CORTE, "V2 fora do tempo: treino pedidos <=09/2025, teste pedidos 10/2025-09/2026")
for f in (cam1, cam2):
    os.remove(f)

# V3: calibração de VIDA INTEIRA (corrigida p/ censura) do modelo final, fora da dobra
m = t.carregar_modelo()
print("\n== V3 calibração vida inteira, previsões fora da dobra (5-fold) vs Kaplan-Meier estratificado, quintis")
for col, nome in (("pd", "P(não paga)"), ("pa", "P(algum atraso ou não paga)")):
    c = m["calibracao"][col]
    x, y = np.array(c["x"]), np.array(c["y_km"])
    print(f"  {nome}: " + " | ".join(f"Q{i+1} prev {100*x[4*i:4*i+4].mean():.1f}% KM {100*y[4*i:4*i+4].mean():.1f}%" for i in range(5)))
