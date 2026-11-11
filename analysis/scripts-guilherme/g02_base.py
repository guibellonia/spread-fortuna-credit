"""Etapa 4.1/4.3 · Base analítica: uma linha por pedido, só com informação disponível NA DATA DO PEDIDO,
mais o desfecho observado (com censura) e uma tabela por parcela para o modelo de sobrevivência.

Saídas (analysis/scripts-guilherme/out/):
  base.pkl     uma linha por pedido (10.000 históricos + 2.000 novos; birô dos novos vem do cache da API)
  periodos.pkl uma linha por (contrato aprovado, parcela decidida até o corte) para os modelos de hazard

Definições (documentadas no relatório):
  - parcela "decidida": paga até o corte, ou vencida há 61+ dias sem pagamento (parcela paga nunca atrasou > 60 dias)
  - "parou" (não paga): primeira parcela vencida há 61+ dias sem pagamento; parar é definitivo na base
  - "atrasou": alguma parcela paga com dias_atraso > 0
  - renda estimada pela movimentação: mediana mensal de entradas_salario (assalariado/aposentado) ou de
    total_entradas (autônomo/empresário), porque nos dois últimos o "salário" é ~10% das entradas
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]
sys.path.insert(0, str(AQUI.parent))
from db import query  # noqa: E402

OUT = AQUI / "out"
CORTE = pd.Timestamp("2026-09-30")
DIAS_PARADA = 61
TAXA = 0.03


def pmt(valor, prazo):
    valor = np.asarray(valor, float)
    prazo = np.asarray(prazo, float)
    return valor * TAXA / (1 - (1 + TAXA) ** (-prazo))


def regiao_cep(cep: pd.Series) -> pd.Series:
    # 1º dígito do CEP = região postal dos Correios
    mapa = {"0": "SP capital/RM", "1": "SP interior", "2": "RJ/ES", "3": "MG", "4": "BA/SE",
            "5": "PE/AL/PB/RN", "6": "CE/PI/MA/PA/AM/AP/RR/AC", "7": "DF/GO/TO/MT/MS/RO", "8": "PR/SC", "9": "RS"}
    return cep.str[0].map(mapa)


def uf_cep(cep: pd.Series) -> pd.Series:
    p = cep.str[:5].astype(int)
    faixas = [(1000, 19999, "SP"), (20000, 28999, "RJ"), (29000, 29999, "ES"), (30000, 39999, "MG"),
              (40000, 48999, "BA"), (49000, 49999, "SE"), (50000, 56999, "PE"), (57000, 57999, "AL"),
              (58000, 58999, "PB"), (59000, 59999, "RN"), (60000, 63999, "CE"), (64000, 64999, "PI"),
              (65000, 65999, "MA"), (66000, 68899, "PA"), (68900, 68999, "AP"), (69000, 69299, "AM"),
              (69300, 69399, "RR"), (69400, 69899, "AM"), (69900, 69999, "AC"), (70000, 73699, "DF"),
              (72800, 76799, "GO"), (77000, 77999, "TO"), (78000, 78899, "MT"), (78900, 78999, "RO"),
              (79000, 79999, "MS"), (80000, 87999, "PR"), (88000, 89999, "SC"), (90000, 99999, "RS")]
    uf = pd.Series("?", index=cep.index)
    for a, b, s in faixas:
        uf[(p >= a) & (p <= b) & (uf == "?")] = s
    return uf


def bureau_novos() -> pd.DataFrame:
    linhas = [json.loads(f.read_text(encoding="utf-8")) for f in (ROOT / "data/cache/bureau").glob("*.json")]
    b = pd.DataFrame(linhas)
    return b


def cadastro() -> pd.DataFrame:
    d = query("""
        select p.*, c.renda_declarada, c.profissao, c.tipo_vinculo, c.data_abertura_conta,
               c.genero, c.data_nascimento, c.estado_civil, c.cep,
               b.score, b.restricoes_ativas, b.parcelas_outras_instituicoes, b.consultas_90_dias, b.meses_historico_bureau
        from hackathon.pedidos p join hackathon.clientes c using (id_cliente)
        left join hackathon.bureau b using (id_pedido)""")
    num = ["valor_solicitado", "valor_aprovado", "renda_declarada", "parcelas_outras_instituicoes"]
    d[num] = d[num].astype(float)
    for c in ["data_pedido", "data_abertura_conta", "data_nascimento"]:
        d[c] = pd.to_datetime(d[c])
    # birô dos 2.000 novos: cache da API (mesmo esquema)
    bn = bureau_novos().set_index("id_cliente")
    nov = d.tipo_base == "novo"
    for c in ["score", "restricoes_ativas", "parcelas_outras_instituicoes", "consultas_90_dias", "meses_historico_bureau"]:
        d.loc[nov, c] = d.loc[nov, "id_cliente"].map(bn[c]).values
    d["birô_ok"] = d["score"].notna()
    d["idade"] = (d.data_pedido - d.data_nascimento).dt.days / 365.25
    d["meses_conta"] = (d.data_pedido - d.data_abertura_conta).dt.days / 30.44
    d["regiao"] = regiao_cep(d.cep)
    d["uf"] = uf_cep(d.cep)
    d["safra"] = d.data_pedido.dt.to_period("Q").astype(str)
    d["parcela_solic"] = pmt(d.valor_solicitado, d.prazo_meses)
    d["parcela_aprov"] = np.where(d.valor_aprovado > 0, pmt(d.valor_aprovado.fillna(0), d.prazo_meses), np.nan)
    d["reduzido"] = (d.decisao == "aprovado") & (d.valor_aprovado < d.valor_solicitado - 0.01)
    return d


def movimentacao() -> pd.DataFrame:
    m = query("select * from hackathon.movimentacao_mensal")
    num = ["total_entradas", "entradas_salario", "total_saidas", "saldo_medio", "saldo_minimo"]
    m[num] = m[num].astype(float)
    m["mes_referencia"] = pd.to_datetime(m.mes_referencia)
    m = m.sort_values(["id_cliente", "mes_referencia"])
    m["k"] = m.groupby("id_cliente").cumcount(ascending=False)  # 0 = mês mais recente antes do pedido
    m["outras_entradas"] = m.total_entradas - m.entradas_salario
    m["saldo_mes"] = m.total_entradas - m.total_saidas
    m["deficit"] = (m.total_saidas > m.total_entradas).astype(int)
    m["cheque"] = (m.dias_cheque_especial > 0).astype(int)
    g = m.groupby("id_cliente")
    f = pd.DataFrame({
        "mov_meses": g.size(),
        "ent_media": g.total_entradas.mean(), "ent_mediana": g.total_entradas.median(),
        "ent_cv": g.total_entradas.std() / g.total_entradas.mean(),
        "sal_media": g.entradas_salario.mean(), "sal_mediana": g.entradas_salario.median(),
        "sal_cv": g.entradas_salario.std() / g.entradas_salario.mean(),
        "outras_ent_media": g.outras_entradas.mean(),
        "sai_media": g.total_saidas.mean(), "sai_mediana": g.total_saidas.median(),
        "sai_cv": g.total_saidas.std() / g.total_saidas.mean(),
        "sai_pico": g.total_saidas.max() / g.total_saidas.median(),  # despesa extraordinária
        "sobra_media": g.saldo_mes.mean(), "sobra_mediana": g.saldo_mes.median(), "sobra_min": g.saldo_mes.min(),
        "meses_deficit": g.deficit.sum(),
        "saldo_medio": g.saldo_medio.mean(), "saldo_min": g.saldo_minimo.min(),
        "cheq_dias_total": g.dias_cheque_especial.sum(), "cheq_dias_media": g.dias_cheque_especial.mean(),
        "cheq_meses": g.cheque.sum(), "cheq_dias_max": g.dias_cheque_especial.max(),
    })
    for n in (3, 6):
        r = m[m.k < n].groupby("id_cliente")
        f[f"deficit_{n}m"] = r.deficit.sum()
        f[f"cheq_meses_{n}m"] = r.cheque.sum()
        f[f"sai_ent_{n}m"] = r.total_saidas.sum() / r.total_entradas.sum()
    rec = m[m.k < 3].groupby("id_cliente")
    old = m[m.k >= 3].groupby("id_cliente")
    f["ent_tend"] = rec.total_entradas.mean() / old.total_entradas.mean()
    f["sai_tend"] = rec.total_saidas.mean() / old.total_saidas.mean()
    f["saldo_tend"] = rec.saldo_medio.mean() - old.saldo_medio.mean()
    f["sai_ent"] = f.sai_media / f.ent_media
    f["sal_share"] = f.sal_media / f.ent_media
    return f.reset_index()


def desfechos() -> tuple[pd.DataFrame, pd.DataFrame]:
    x = query("select id_pedido, numero_parcela, data_vencimento, data_pagamento, dias_atraso from hackathon.parcelas")
    x["data_vencimento"] = pd.to_datetime(x.data_vencimento)
    x["paga"] = x.data_pagamento.notna()
    x["parou"] = ~x.paga & (x.data_vencimento <= CORTE - pd.Timedelta(days=DIAS_PARADA))
    x["decidida"] = x.paga | x.parou
    x["atrasada"] = x.paga & (x.dias_atraso > 0)
    x = x.sort_values(["id_pedido", "numero_parcela"])
    g = x.groupby("id_pedido")
    o = pd.DataFrame({
        "n_decididas": g.decidida.sum(),
        "k_parada": x[x.parou].groupby("id_pedido").numero_parcela.min(),
        "k_1o_atraso": x[x.atrasada].groupby("id_pedido").numero_parcela.min(),
        "n_atrasadas": g.atrasada.sum(),
        "atraso_max_pago": x[x.paga].groupby("id_pedido").dias_atraso.max(),
    })
    o["parou"] = o.k_parada.notna()
    o["atrasou"] = o.k_1o_atraso.notna()
    # exposição observada (em nº de parcelas): até a parada, ou todas as decididas
    o["k_obs"] = np.where(o.parou, o.k_parada, o.n_decididas)
    # tabela por período (parcela decidida, até a parada inclusive) para o hazard
    x = x.merge(o[["k_parada"]], left_on="id_pedido", right_index=True, how="left")
    per = x[x.decidida & (x.k_parada.isna() | (x.numero_parcela <= x.k_parada))].copy()
    per["evento_parada"] = per.parou.astype(int)
    per["evento_atraso"] = per.atrasada.astype(int)
    return o.reset_index(), per[["id_pedido", "numero_parcela", "data_vencimento", "evento_parada", "evento_atraso"]]


def main():
    OUT.mkdir(exist_ok=True)
    d = cadastro().merge(movimentacao(), on="id_cliente", how="left")
    o, per = desfechos()
    d = d.merge(o, on="id_pedido", how="left")

    # renda estimada pela conta (robusta: mediana) e indicadores de comprometimento
    sal_like = d.tipo_vinculo.isin(["assalariado", "aposentado"])
    d["renda_mov"] = np.where(sal_like, d.sal_mediana, d.ent_mediana)
    d["renda_ratio"] = d.renda_mov / d.renda_declarada
    d["renda_est"] = np.minimum(d.renda_declarada, d.renda_mov)  # conservadora
    d["outras_parc"] = d.parcelas_outras_instituicoes
    for base, parc in (("solic", "parcela_solic"), ("aprov", "parcela_aprov")):
        d[f"comp_decl_{base}"] = d[parc] / d.renda_declarada
        d[f"comp_real_{base}"] = d[parc] / d.renda_est
        d[f"comp_total_{base}"] = (d[parc] + d.outras_parc) / d.renda_est
        d[f"sobra_pos_{base}"] = d.sobra_media - d[parc]  # renda disponível depois da nova parcela
        d[f"parc_sobre_sobra_{base}"] = np.where(d.sobra_media > 0, d[parc] / d.sobra_media, np.inf)
        val = d.valor_solicitado if base == "solic" else d.valor_aprovado
        d[f"endiv_{base}"] = val / d.renda_est  # estoque da dívida nova em meses de renda
    d["comp_antes"] = d.outras_parc / d.renda_est
    d["desp_sobre_renda"] = d.sai_media / d.renda_est
    d.to_pickle(OUT / "base.pkl")
    per = per.merge(d[["id_pedido", "prazo_meses", "data_pedido"]], on="id_pedido")
    per.to_pickle(OUT / "periodos.pkl")
    h = d[d.tipo_base == "historico"]
    print("base:", d.shape, "| periodos:", per.shape)
    print("novos com birô:", int(d.loc[d.tipo_base == "novo", "birô_ok"].sum()), "de", int((d.tipo_base == "novo").sum()))
    print(h[h.decisao == "aprovado"][["parou", "atrasou"]].mean())
    print(h[["renda_ratio", "comp_real_solic", "comp_total_solic", "sai_ent", "sobra_media", "ent_cv"]].describe().round(3).to_string())


if __name__ == "__main__":
    main()
