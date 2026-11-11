"""Monta uma linha por pedido com variáveis explicativas e o desfecho observado.

Saída: analysis/out/dataset.pkl (histórico + novos; os novos ficam sem bureau e sem desfecho).
"""
from pathlib import Path

import numpy as np
import pandas as pd

from db import query

OUT = Path(__file__).parent / "out"
CUTOFF = pd.Timestamp("2026-09-30")
STOP_DAYS = 61  # parcela paga nunca atrasou mais de 60 dias: 61+ sem pagar = parou de pagar


def pmt(valor, prazo, i=0.03):
    return valor * i / (1 - (1 + i) ** (-prazo))


def load_base() -> pd.DataFrame:
    d = query("""
        select p.*, c.renda_declarada, c.profissao, c.tipo_vinculo, c.data_abertura_conta,
               c.genero, c.data_nascimento, c.estado_civil, c.cep,
               b.score, b.restricoes_ativas, b.parcelas_outras_instituicoes,
               b.consultas_90_dias, b.meses_historico_bureau
        from hackathon.pedidos p
        join hackathon.clientes c using (id_cliente)
        left join hackathon.bureau b using (id_pedido)
    """)
    num = ["valor_solicitado", "valor_aprovado", "renda_declarada", "parcelas_outras_instituicoes"]
    d[num] = d[num].astype(float)
    for c in ["data_pedido", "data_abertura_conta", "data_nascimento"]:
        d[c] = pd.to_datetime(d[c])
    d["idade"] = (d.data_pedido - d.data_nascimento).dt.days / 365.25
    d["meses_conta"] = (d.data_pedido - d.data_abertura_conta).dt.days / 30.44
    d["regiao_cep"] = d.cep.str[0]
    d["parcela_solic"] = pmt(d.valor_solicitado, d.prazo_meses)
    d["comp_decl"] = d.parcela_solic / d.renda_declarada
    return d


def movement_features() -> pd.DataFrame:
    m = query("select * from hackathon.movimentacao_mensal")
    num = ["total_entradas", "entradas_salario", "total_saidas", "saldo_medio", "saldo_minimo"]
    m[num] = m[num].astype(float)
    m["mes_referencia"] = pd.to_datetime(m.mes_referencia)
    m = m.sort_values(["id_cliente", "mes_referencia"])
    m["rank_desc"] = m.groupby("id_cliente").cumcount(ascending=False)  # 0 = mês mais recente
    g = m.groupby("id_cliente")
    f = pd.DataFrame({
        "mov_meses": g.size(),
        "ent_media": g.total_entradas.mean(),
        "ent_cv": g.total_entradas.std() / g.total_entradas.mean(),
        "sal_media": g.entradas_salario.mean(),
        "sai_media": g.total_saidas.mean(),
        "saldo_medio": g.saldo_medio.mean(),
        "saldo_min": g.saldo_minimo.min(),
        "cheq_dias_media": g.dias_cheque_especial.mean(),
        "cheq_meses": g.dias_cheque_especial.apply(lambda s: (s > 0).sum()),
        "cheq_dias_max": g.dias_cheque_especial.max(),
    })
    rec = m[m.rank_desc < 3].groupby("id_cliente")
    old = m[m.rank_desc >= 3].groupby("id_cliente")
    f["ent_tend"] = rec.total_entradas.mean() / old.total_entradas.mean()  # últimos 3 m vs anteriores
    f["cheq_dias_rec"] = rec.dias_cheque_especial.mean()
    f["saldo_rec"] = rec.saldo_medio.mean()
    f["sai_ent"] = f.sai_media / f.ent_media
    return f.reset_index()


def outcomes() -> pd.DataFrame:
    x = query("""
        select x.id_pedido, x.numero_parcela, x.data_vencimento, x.data_pagamento, x.dias_atraso
        from hackathon.parcelas x
    """)
    x["data_vencimento"] = pd.to_datetime(x.data_vencimento)
    x["paga"] = x.data_pagamento.notna()
    x["parou"] = ~x.paga & (x.dias_atraso >= STOP_DAYS)
    # parcela "decidida": paga, ou vencida há 61+ dias (já dá para saber se parou)
    x["decidida"] = x.paga | (x.data_vencimento <= CUTOFF - pd.Timedelta(days=STOP_DAYS))
    g = x.groupby("id_pedido")
    o = pd.DataFrame({
        "n_parcelas": g.size(),
        "n_decididas": g.decidida.sum(),
        "parada_k": x[x.parou].groupby("id_pedido").numero_parcela.min(),
        "atrasou": x[x.paga].groupby("id_pedido").dias_atraso.apply(lambda s: (s > 0).any()),
        "atraso_max_pago": x[x.paga].groupby("id_pedido").dias_atraso.max(),
    })
    o["parou"] = o.parada_k.notna()
    # exposição observada: parcelas até a parada (inclusive) ou todas as decididas
    o["expo"] = np.where(o.parou, o.parada_k, o.n_decididas)
    o["atrasou"] = o.atrasou.fillna(False).astype(bool)
    return o.reset_index()


def main():
    OUT.mkdir(exist_ok=True)
    d = load_base().merge(movement_features(), on="id_cliente", how="left")
    d = d.merge(outcomes(), on="id_pedido", how="left")
    d["renda_real"] = np.where(d.tipo_vinculo.isin(["assalariado", "aposentado"]), d.sal_media, d.ent_media)
    d["renda_ratio"] = d.renda_real / d.renda_declarada
    d.to_pickle(OUT / "dataset.pkl")
    print(d.shape)
    print(d[d.tipo_base == "historico"][["renda_ratio", "ent_tend", "cheq_dias_media", "saldo_min", "meses_conta"]].describe().round(2).to_string())


if __name__ == "__main__":
    main()
