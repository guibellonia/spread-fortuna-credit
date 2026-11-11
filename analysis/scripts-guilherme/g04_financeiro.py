"""Etapas 4 e 5 · Reconstrução financeira, indicadores de endividamento e relação com a inadimplência.

Toda taxa é PD de vida inteira por Kaplan-Meier (g_util), com IC 95%, sobre contratos aprovados.
Saída: out/g04_financeiro.md
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent))
from g_util import carregar, fmt, km_vida, resumo_grupo, tabela  # noqa: E402
from db import query  # noqa: E402

OUT = AQUI / "out" / "g04_financeiro.md"
L = []


def h(t):
    L.append(f"\n## {t}\n")


def p(t=""):
    L.append(t)


def faixa(s, cortes, rot=None):
    return pd.cut(s, cortes, labels=rot, right=False)


def main():
    d, hist, ap, novos = carregar()
    ap["vinculo"] = ap.tipo_vinculo

    # ---------------------------------------------------------------- 4.1 reconstrução
    h("4.1 Reconstrução financeira (12 meses antes do pedido; todos os 10.000 históricos e 2.000 novos)")
    cols = {"renda_declarada": "Renda declarada", "renda_mov": "Renda identificada na conta (mediana)",
            "ent_media": "Entradas, média mensal", "ent_mediana": "Entradas, mediana mensal",
            "sal_media": "Entradas de salário, média", "outras_ent_media": "Outras entradas (não salário), média",
            "sai_media": "Saídas, média mensal", "sai_mediana": "Saídas, mediana mensal",
            "sobra_media": "Saldo do mês (entradas − saídas), média", "outras_parc": "Parcelas em outras instituições (birô)",
            "ent_cv": "Variação das entradas (CV)", "sai_pico": "Pico de saída / mediana (despesa extraordinária)",
            "renda_ratio": "Renda na conta / declarada", "comp_antes": "Comprometimento antes do pedido (outras / renda est.)"}
    t = d.groupby("tipo_base")[list(cols)].median().T
    t.index = [cols[c] for c in t.index]
    t2 = d.groupby("tipo_base")[list(cols)].quantile(0.9).T
    t2.index = t.index
    t = pd.concat({"mediana": t, "p90": t2}, axis=1).round(2)
    p(t.to_markdown())
    p("\nRenda identificada por vínculo (mediana de entradas de salário vs entradas totais, históricos):")
    v = hist.groupby("tipo_vinculo").agg(n=("id_pedido", "size"), renda_decl=("renda_declarada", "median"),
                                          salario=("sal_mediana", "median"), entradas=("ent_mediana", "median"),
                                          salario_share=("sal_share", "median"), ratio=("renda_ratio", "median"),
                                          cv=("ent_cv", "median")).round(2)
    p(v.to_markdown())

    # sazonalidade: entradas por mês-calendário, normalizadas pela média do cliente
    m = query("select id_cliente, mes_referencia, total_entradas::float te, entradas_salario::float sal, total_saidas::float ts from hackathon.movimentacao_mensal")
    m["mes"] = pd.to_datetime(m.mes_referencia).dt.month
    for c in ["te", "sal", "ts"]:
        m[c + "_n"] = m[c] / m.groupby("id_cliente")[c].transform("mean")
    saz = m.groupby("mes")[["te_n", "sal_n", "ts_n"]].mean().round(3)
    saz.columns = ["entradas (÷ média do cliente)", "salário", "saídas"]
    p("\nSazonalidade (índice médio por mês-calendário; 1,00 = mês típico do cliente):")
    p(saz.T.to_markdown())

    # ---------------------------------------------------------------- 4.3 indicadores
    h("4.3 Indicadores construídos (definições)")
    p("""| Indicador | Fórmula | Status |
|---|---|---|
| Renda estimada (renda_est) | min(renda declarada, renda identificada na conta) | estimado |
| Comprometimento da nova parcela | parcela Price(valor, prazo, 3%) / renda_est | observado (parcela) / estimado (renda) |
| Comprometimento total (fluxo) | (nova parcela + parcelas em outras instituições) / renda_est | estimado |
| Comprometimento antes do pedido | parcelas em outras instituições / renda_est | estimado |
| Endividamento (estoque da dívida nova) | valor aprovado / renda_est, em meses de renda | estimado; estoque das outras dívidas **indisponível** (birô só traz a parcela) |
| Renda disponível após a parcela | (entradas − saídas, média 12m) − nova parcela | estimado; despesas recorrentes ≈ saídas medianas |
| Parcela sobre a sobra | nova parcela / (entradas − saídas) | estimado |
| Exposição | valor aprovado (Fortuna); outras dívidas só em fluxo | parcial |

Fluxo (parcela/mês), estoque (saldo devedor) e valor contratado não são somados entre si. Não há como separar
transferências entre contas, estornos, empréstimos recebidos ou reembolsos: a movimentação é agregada por mês, só com
`entradas_salario` destacado. "Outras entradas" (total − salário) é o único proxy de entrada não-renda.""")

    # ---------------------------------------------------------------- 5 relação com inadimplência
    h("5. Endividamento e inadimplência (aprovados, PD de vida inteira por KM)")
    base = resumo_grupo(ap)
    p(f"Referência: {base['contratos']:,} aprovados, PD vida {100*base['pd_vida']:.1f}% "
      f"[{100*base['ic_inf']:.1f}–{100*base['ic_sup']:.1f}], margem {base['margem_R$']:+.3f} por R$.\n")

    blocos = [
        ("5.1/5.2 Comprometimento da nova parcela sobre a renda estimada (valor aprovado)", "comp_real_aprov",
         [0, .05, .10, .15, .20, .25, .28, .30, .35, .40, .50, 10]),
        ("Comprometimento da nova parcela sobre a renda DECLARADA (regra atual usa esta)", "comp_decl_aprov",
         [0, .10, .20, .25, .28, .30, .3001, 10]),
        ("Comprometimento total (nova + outras instituições) / renda estimada", "comp_total_aprov",
         [0, .10, .20, .30, .40, .50, .60, .80, 100]),
        ("Comprometimento ANTES do pedido (outras instituições / renda estimada)", "comp_antes",
         [0, .0001, .10, .20, .30, .40, .60, 100]),
        ("Endividamento: valor aprovado em meses de renda estimada", "endiv_aprov",
         [0, 1, 2, 3, 4, 6, 8, 100]),
        ("5.7 Renda disponível após a nova parcela (R$/mês)", "sobra_pos_aprov",
         [-1e9, 0, 500, 1000, 2000, 3000, 5000, 1e9]),
        ("Nova parcela / sobra mensal (entradas − saídas)", "parc_sobre_sobra_aprov",
         [-1, .1, .2, .3, .5, .75, 1.0, np.inf]),
        ("5.9 Renda identificada na conta / renda declarada", "renda_ratio",
         [0, .6, .7, .8, .9, 1.0, 1.1, 10]),
        ("5.4 Variabilidade das entradas (CV mensal)", "ent_cv", [0, .05, .10, .20, .30, .40, 10]),
        ("5.7 Saídas / entradas (12 meses)", "sai_ent", [0, .3, .4, .5, .6, .7, .8, 10]),
        ("5.7 Meses com saídas > entradas (12 meses)", "meses_deficit", [0, 1, 2, 3, 13]),
        ("5.7 Meses com cheque especial (12 meses)", "cheq_meses", [0, 1, 2, 3, 6, 13]),
        ("5.7 Saldo mínimo do período (R$)", "saldo_min", [-1e9, -2000, -500, 0, 1000, 5000, 1e9]),
        ("5.6 Tendência das saídas (últimos 3m ÷ anteriores)", "sai_tend", [0, .9, 1.0, 1.1, 1.25, 1.5, 100]),
        ("Tendência das entradas (últimos 3m ÷ anteriores)", "ent_tend", [0, .7, .9, 1.1, 1.3, 100]),
        ("5.8 Valor da nova parcela (R$)", "parcela_aprov", [0, 200, 400, 600, 1000, 1500, 2500, 1e9]),
        ("5.5 Consultas ao CPF em 90 dias (busca por crédito)", "consultas_90_dias", [0, 1, 2, 4, 6, 100]),
        ("Restrições ativas no birô", "restricoes_ativas", [0, 1, 2, 100]),
        ("Score do birô", "score", [0, 500, 600, 650, 700, 800, 900, 2000]),
        ("Meses de histórico no birô", "meses_historico_bureau", [0, 12, 24, 60, 120, 1000]),
        ("Prazo (meses)", "prazo_meses", [0, 7, 13, 19, 25, 37]),
    ]
    for titulo, col, cortes in blocos:
        ap["_f"] = faixa(ap[col], cortes)
        p(f"\n### {titulo}\n")
        p(fmt(tabela(ap, "_f", min_n=30).drop(columns=["proj_time"], errors="ignore")))

    # ---------------------------------------------------------------- ponto de corte fino
    h("5.2 Onde o risco muda de patamar: comprometimento da nova parcela / renda estimada, passos de 2 p.p.")
    ap["_f"] = faixa(ap.comp_real_aprov, [0] + list(np.round(np.arange(.10, .41, .02), 2)) + [10])
    t = tabela(ap, "_f", min_n=20)
    p(fmt(t[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup", "margem_R$"]]))
    p("\nMesmo recorte, só sobre a renda declarada:")
    ap["_f"] = faixa(ap.comp_decl_aprov, [0] + list(np.round(np.arange(.10, .31, .02), 2)) + [.3001, 10])
    p(fmt(tabela(ap, "_f", min_n=20)[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup", "margem_R$"]]))

    # ---------------------------------------------------------------- 5.3 renda alta + muitas parcelas
    h("5.3 Renda alta com muitas parcelas em outras instituições")
    ap["_r"] = np.where(ap.renda_est >= 8000, "renda est. ≥ 8 mil", "renda est. < 8 mil")
    ap["_c"] = faixa(ap.comp_antes, [0, .0001, .20, .40, 100], ["sem outras", "<20%", "20–40%", "≥40%"])
    p(fmt(tabela(ap, ["_r", "_c"], min_n=30)[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup", "margem_R$"]]))

    # ---------------------------------------------------------------- reduzidos: valor aprovado x pedido
    h("Valor reduzido pela regra dos 30%: o risco segue o valor aprovado ou o pedido?")
    ap["_g"] = np.select(
        [ap.reduzido, (~ap.reduzido) & (ap.comp_decl_aprov >= .27) & (ap.comp_decl_aprov <= .30),
         (~ap.reduzido) & (ap.comp_decl_aprov >= .20) & (ap.comp_decl_aprov < .27), ~ap.reduzido],
        ["reduzido p/ 30% (pediu mais)", "não reduzido, parcela 27–30% da renda decl.",
         "não reduzido, 20–27%", "não reduzido, <20%"], "?")
    t = tabela(ap, "_g", min_n=20)
    t["comp_decl_solic_mediana"] = ap.groupby("_g").comp_decl_solic.median()
    t["comp_real_aprov_mediana"] = ap.groupby("_g").comp_real_aprov.median()
    p(fmt(t[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup", "margem_R$", "comp_decl_solic_mediana", "comp_real_aprov_mediana"]].round(3)))
    red = ap[ap.reduzido]
    red_f = faixa(red.comp_decl_solic, [0, .35, .45, .60, 100])
    p("\nReduzidos por quanto o pedido passava da regra (parcela pedida / renda declarada):")
    p(fmt(tabela(red.assign(_f=red_f), "_f", min_n=20)[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup"]]))
    nr = ap[~ap.reduzido]
    nr_f = faixa(nr.comp_real_aprov, [0, .28, .32, .36, .40, 10])
    p("\nNão reduzidos, mesma escala (parcela aprovada / renda estimada):")
    p(fmt(tabela(nr.assign(_f=nr_f), "_f", min_n=20)[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup"]]))
    red_f2 = faixa(red.comp_real_aprov, [0, .28, .32, .36, .40, 10])
    p("\nReduzidos, mesma escala (parcela aprovada / renda estimada):")
    p(fmt(tabela(red.assign(_f=red_f2), "_f", min_n=15)[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup"]]))

    # ---------------------------------------------------------------- deterioração antes do atraso
    h("Sinais de deterioração nos 3 meses antes do pedido")
    ap["_d"] = np.select([ap.deficit_3m >= 1, ap.cheq_meses_3m >= 1], ["saídas > entradas em algum dos 3 meses", "cheque especial nos 3 meses (sem déficit)"], "nenhum dos dois")
    p(fmt(tabela(ap, "_d")[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup", "margem_R$"]]))

    # ---------------------------------------------------------------- novos: distribuição dos indicadores
    h("Os 2.000 pedidos novos nesses indicadores (valor solicitado)")
    nv = novos.copy()
    nv["comp_real"] = faixa(nv.comp_real_solic, [0, .20, .28, .35, 10])
    nv["deficit3"] = nv.deficit_3m >= 1
    nv["restr"] = nv.restricoes_ativas > 0
    nv["score600"] = nv.score > 600
    tb = nv.groupby(["comp_real"], observed=True).agg(pedidos=("id_pedido", "size"), deficit_3m=("deficit3", "sum"),
                                                     com_restricao=("restr", "sum"), score_acima_600=("score600", "sum"),
                                                     valor_medio=("valor_solicitado", "mean")).round(0)
    p(tb.to_markdown())

    OUT.write_text("# Saída de g04_financeiro.py\n" + "\n".join(L), encoding="utf-8")
    print("ok", OUT)


if __name__ == "__main__":
    main()
