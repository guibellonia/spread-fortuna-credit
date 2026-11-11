"""Monta uma linha de atributos por pedido: cadastro, pedido, movimentação e bureau."""
import numpy as np
import pandas as pd

from db import consulta

TAXA = 0.03
CORTE = pd.Timestamp("2026-09-30")


def parcela_price(valor, prazo):
    valor = np.asarray(valor, dtype=float)
    prazo = np.asarray(prazo, dtype=float)
    return np.round(valor * TAXA / (1 - (1 + TAXA) ** (-prazo)), 2)


def pedidos_base() -> pd.DataFrame:
    df = consulta("""
        SELECT p.*, c.renda_declarada, c.profissao, c.tipo_vinculo, c.data_abertura_conta,
               c.genero, c.data_nascimento, c.estado_civil, c.cep
        FROM hackathon.pedidos p JOIN hackathon.clientes c USING (id_cliente)
    """)
    for c in ["valor_solicitado", "valor_aprovado", "renda_declarada"]:
        df[c] = df[c].astype(float)
    for c in ["data_pedido", "data_abertura_conta", "data_nascimento"]:
        df[c] = pd.to_datetime(df[c])
    return df


def movimentacao_agregada() -> pd.DataFrame:
    m = consulta("SELECT * FROM hackathon.movimentacao_mensal")
    for c in ["total_entradas", "entradas_salario", "total_saidas", "saldo_medio", "saldo_minimo"]:
        m[c] = m[c].astype(float)
    m["mes_referencia"] = pd.to_datetime(m["mes_referencia"])
    m = m.sort_values(["id_cliente", "mes_referencia"])
    m["mes_negativo"] = (m["saldo_minimo"] < 0).astype(int)
    m["saidas_maior_entradas"] = (m["total_saidas"] > m["total_entradas"]).astype(int)
    g = m.groupby("id_cliente")
    ag = pd.DataFrame({
        "mov_meses": g.size(),
        "mov_entradas_media": g["total_entradas"].mean(),
        "mov_salario_media": g["entradas_salario"].mean(),
        "mov_saidas_media": g["total_saidas"].mean(),
        "mov_saldo_medio": g["saldo_medio"].mean(),
        "mov_saldo_minimo_min": g["saldo_minimo"].min(),
        "mov_dias_cheque_total": g["dias_cheque_especial"].sum(),
        "mov_meses_cheque": g["mes_negativo"].sum(),
        "mov_meses_saida_maior": g["saidas_maior_entradas"].sum(),
        "mov_entradas_cv": g["total_entradas"].std() / g["total_entradas"].mean().replace(0, np.nan),
        "mov_meses_sem_salario": g["entradas_salario"].apply(lambda s: int((s <= 0).sum())),
    })
    # tendência: últimos 3 meses vs média
    ult3 = m.groupby("id_cliente").tail(3).groupby("id_cliente")
    ag["mov_saldo_ult3"] = ult3["saldo_medio"].mean()
    ag["mov_cheque_ult3"] = ult3["dias_cheque_especial"].sum()
    ag["mov_entradas_ult3"] = ult3["total_entradas"].mean()
    # conta apertada (filtro do Bilosca): meses, dos 3 antes do pedido, com saídas > entradas
    ag["mov_meses_saida_maior_3m"] = ult3["saidas_maior_entradas"].sum()
    return ag.reset_index()


def bureau_historico() -> pd.DataFrame:
    b = consulta("SELECT * FROM hackathon.bureau")
    b["parcelas_outras_instituicoes"] = b["parcelas_outras_instituicoes"].astype(float)
    return b


def montar(df: pd.DataFrame, mov: pd.DataFrame, bureau: pd.DataFrame, chave_bureau="id_pedido") -> pd.DataFrame:
    """bureau precisa ter a coluna chave_bureau (id_pedido no histórico, id_cliente nos novos)."""
    x = df.merge(mov, on="id_cliente", how="left").merge(bureau, on=chave_bureau, how="left")
    x["idade"] = (x["data_pedido"] - x["data_nascimento"]).dt.days / 365.25
    x["meses_conta"] = (x["data_pedido"] - x["data_abertura_conta"]).dt.days / 30.44
    x["parcela_solicitada"] = parcela_price(x["valor_solicitado"], x["prazo_meses"])
    x["comprometimento"] = x["parcela_solicitada"] / x["renda_declarada"]
    x["comprometimento_total"] = (x["parcela_solicitada"] + x["parcelas_outras_instituicoes"]) / x["renda_declarada"]
    x["salario_sobre_renda"] = x["mov_salario_media"] / x["renda_declarada"]
    x["entradas_sobre_renda"] = x["mov_entradas_media"] / x["renda_declarada"]
    x["comprometimento_real"] = (x["parcela_solicitada"] + x["parcelas_outras_instituicoes"]) / x["mov_entradas_media"].clip(lower=1)
    x["sobra_mensal"] = x["mov_entradas_media"] - x["mov_saidas_media"]
    x["valor_sobre_renda"] = x["valor_solicitado"] / x["renda_declarada"]
    x["uf_regiao"] = x["cep"].str[0]
    return x


def politica_atual(x: pd.DataFrame) -> pd.Series:
    """Regras fixas da Fortuna (manual, seção 3). Aprova o valor solicitado."""
    return (
        (x["score"] > 600)
        & (x["renda_declarada"] > 2000)
        & (x["restricoes_ativas"] == 0)
        & (x["parcela_solicitada"] <= 0.30 * x["renda_declarada"])
    )
