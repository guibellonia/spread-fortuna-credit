"""Base analitica: 1 linha por pedido historico, features (so o que se sabe no pedido) + alvos (de parcelas).
Uso: from base import carregar; df = carregar()
"""
import os
import numpy as np
import pandas as pd
import psycopg

# lê PG* do .env da raiz (antes: DSN fixo na porta 5544, da máquina do Enio)
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
DSN = ""
CORTE = pd.Timestamp("2026-09-30")
CACHE = os.path.join(os.path.dirname(__file__), "_base.pkl")


def parcela_price(valor, prazo, i=0.03):
    return valor * i / (1 - (1 + i) ** (-prazo))


def _q(sql):
    with psycopg.connect(DSN) as c:
        cur = c.execute(sql)
        cols = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def carregar(refazer=False, tipo="historico"):
    cache = CACHE.replace(".pkl", f"_{tipo}.pkl")
    if os.path.exists(cache) and not refazer:
        return pd.read_pickle(cache)
    ped = _q(f"select p.*, c.* from hackathon.pedidos p join hackathon.clientes c using(id_cliente) where tipo_base='{tipo}'")
    ped = ped.loc[:, ~ped.columns.duplicated()]
    if tipo == "historico":
        bur = _q("select * from hackathon.bureau")
        ped = ped.merge(bur, on="id_pedido", how="left")
    mov = _q("select * from hackathon.movimentacao_mensal")
    for c in ped.columns:
        if ped[c].dtype == object:
            try:
                if c in ("cep", "id_pedido", "id_cliente"):
                    continue
                ped[c] = pd.to_numeric(ped[c])
            except (ValueError, TypeError):
                pass
    for c in ["data_pedido", "data_abertura_conta", "data_nascimento"]:
        ped[c] = pd.to_datetime(ped[c])
    num = ["total_entradas", "entradas_salario", "total_saidas", "saldo_medio", "saldo_minimo", "dias_cheque_especial"]
    for c in num:
        mov[c] = pd.to_numeric(mov[c])
    mov["mes_referencia"] = pd.to_datetime(mov["mes_referencia"])
    mov = mov.merge(ped[["id_cliente", "data_pedido"]], on="id_cliente")
    mesped = mov["data_pedido"].dt.to_period("M")
    mov["lag"] = (mesped - mov["mes_referencia"].dt.to_period("M")).apply(lambda x: x.n)  # 1 = mes anterior
    mov = mov[(mov.lag >= 1) & (mov.lag <= 12)]
    g = mov.groupby("id_cliente")
    f = pd.DataFrame({
        "mov_meses": g.size(),
        "ent_media": g.total_entradas.mean(),
        "sal_media": g.entradas_salario.mean(),
        "sai_media": g.total_saidas.mean(),
        "saldo_medio_med": g.saldo_medio.mean(),
        "saldo_min_min": g.saldo_minimo.min(),
        "saldo_min_med": g.saldo_minimo.mean(),
        "cheque_12m": g.dias_cheque_especial.sum(),
        "cheque_meses_12m": g.dias_cheque_especial.apply(lambda s: (s > 0).sum()),
        "meses_sem_salario": g.entradas_salario.apply(lambda s: (s <= 0).sum()),
        "cv_entradas": g.total_entradas.std() / g.total_entradas.mean().replace(0, np.nan),
        "meses_saida_maior": g.apply(lambda d: (d.total_saidas > d.total_entradas).sum()),
    })
    m3 = mov[mov.lag <= 3].groupby("id_cliente")
    f["cheque_3m"] = m3.dias_cheque_especial.sum()
    f["meses_saida_maior_3m"] = m3.apply(lambda d: (d.total_saidas > d.total_entradas).sum())
    f["ent_3m"] = m3.total_entradas.mean()
    f["sal_3m"] = m3.entradas_salario.mean()
    f["saldo_min_3m"] = m3.saldo_minimo.min()
    f["saldo_medio_3m"] = m3.saldo_medio.mean()
    f["sai_3m"] = m3.total_saidas.mean()
    old = mov[mov.lag >= 10].groupby("id_cliente")
    f["ent_antigo"] = old.total_entradas.mean()
    f["sal_antigo"] = old.entradas_salario.mean()
    # inclinacao das entradas (R$/mes, positivo = crescendo)
    def slope(d):
        if len(d) < 3:
            return np.nan
        x = -d.lag.values.astype(float)
        return np.polyfit(x, d.total_entradas.values, 1)[0]
    f["tend_entradas"] = g.apply(slope)
    ped = ped.merge(f, left_on="id_cliente", right_index=True, how="left")

    # derivadas
    ped["idade"] = (ped.data_pedido - ped.data_nascimento).dt.days / 365.25
    ped["tempo_conta_meses"] = (ped.data_pedido - ped.data_abertura_conta).dt.days / 30.44
    ped["parcela_sol"] = parcela_price(ped.valor_solicitado, ped.prazo_meses)
    ped["parc_renda"] = ped.parcela_sol / ped.renda_declarada
    ped["parc_sal"] = ped.parcela_sol / ped.sal_media.replace(0, np.nan)
    ped["parc_ent"] = ped.parcela_sol / ped.ent_media.replace(0, np.nan)
    ped["sal_renda"] = ped.sal_media / ped.renda_declarada
    ped["ent_renda"] = ped.ent_media / ped.renda_declarada
    ped["valor_renda"] = ped.valor_solicitado / ped.renda_declarada
    ped["queda_entradas"] = ped.ent_3m / ped.ent_antigo.replace(0, np.nan)
    ped["queda_salario"] = ped.sal_3m / ped.sal_antigo.replace(0, np.nan)
    ped["saida_ent"] = ped.sai_media / ped.ent_media.replace(0, np.nan)
    ped["saida_ent_3m"] = ped.sai_3m / ped.ent_3m.replace(0, np.nan)
    ped["dia_pedido"] = ped.data_pedido.dt.day
    ped["dow_pedido"] = ped.data_pedido.dt.dayofweek
    ped["safra"] = ped.data_pedido.dt.to_period("M").astype(str)
    ped["uf_cep1"] = ped.cep.str[:1]
    if "parcelas_outras_instituicoes" in ped:
        ped["outras_renda"] = ped.parcelas_outras_instituicoes / ped.renda_declarada
        ped["outras_mais_parc_renda"] = (ped.parcelas_outras_instituicoes + ped.parcela_sol) / ped.renda_declarada
        ped["regra_atual"] = ((ped.score > 600) & (ped.renda_declarada > 2000) & (ped.restricoes_ativas == 0)
                              & (ped.parc_renda <= 0.30))

    if tipo == "historico":
        par = _q("select * from hackathon.parcelas")
        for c in ["valor_parcela", "dias_atraso", "numero_parcela"]:
            par[c] = pd.to_numeric(par[c])
        par["data_vencimento"] = pd.to_datetime(par.data_vencimento)
        par["data_pagamento"] = pd.to_datetime(par.data_pagamento)
        par["vencida"] = par.data_vencimento <= CORTE
        pv = par[par.vencida]
        gp = pv.groupby("id_pedido")
        a = pd.DataFrame({
            "n_vencidas": gp.size(),
            "atraso_max": gp.dias_atraso.max(),
            "n_atrasos": gp.dias_atraso.apply(lambda s: (s > 0).sum()),
            "n_nao_pagas": gp.data_pagamento.apply(lambda s: s.isna().sum()),
        })
        # primeira parcela em que o atraso chegou a 90 (para maturacao)
        p90 = pv[pv.dias_atraso >= 90].groupby("id_pedido").numero_parcela.min()
        a["parc_1o_90"] = p90
        # valor da parcela efetiva (aprovada)
        a["parcela_aprov"] = par.groupby("id_pedido").valor_parcela.first()
        a["n_total_parc"] = par.groupby("id_pedido").size()
        ped = ped.merge(a, left_on="id_pedido", right_index=True, how="left")
        ap = ped.decisao == "aprovado"
        ped["meses_obs"] = np.where(ap, ped.n_vencidas, np.nan)
        ped["y_calote"] = np.where(ap, (ped.atraso_max >= 90).astype(float), np.nan)
        ped["y_atraso"] = np.where(ap, ((ped.atraso_max > 0) & (ped.atraso_max < 90)).astype(float), np.nan)
        ped["classe"] = np.select([~ap, ped.atraso_max >= 90, ped.atraso_max > 0], ["negado", "nao_paga", "atraso"], "em_dia")
        ped["parc_aprov_renda"] = ped.parcela_aprov / ped.renda_declarada
        ped["parc_aprov_sal"] = ped.parcela_aprov / ped.sal_media.replace(0, np.nan)
        ped["reduzido"] = ap & (ped.valor_aprovado < ped.valor_solicitado)
    ped.to_pickle(cache)
    return ped


if __name__ == "__main__":
    d = carregar(refazer=True)
    print(d.shape)
    print(d.classe.value_counts())
