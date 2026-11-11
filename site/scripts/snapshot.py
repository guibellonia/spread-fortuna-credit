"""Gera os dados do painel (site/src/data/dashboard.json) a partir do banco e da API do bureau.

O JSON vai para um site público, então só saem AGREGADOS: nenhum id de cliente ou de pedido, nenhuma linha
individual. O script confere isso antes de gravar e para se encontrar algum id.

Uso, da raiz do repositório, com o .env preenchido (modelo em .env.example):
    .venv/Scripts/python site/scripts/snapshot.py

O bureau é consultado com retry e cache em disco (data/cache/bureau/); rodar de novo só busca quem faltou.
"""
from __future__ import annotations


import json
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg
from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from bureau_client import LOG, ROOT, Bureau  # noqa: E402

SAIDA = AQUI.parent / "src" / "data" / "dashboard.json"
DECISOES = ROOT / "saida" / "decisoes_mescla.csv"          # src/politica_mescla.py: proposta, regras e faixa
COMPARACAO = ROOT / "saida" / "comparacao_mescla_{}.csv"   # src/politica_mescla.py --comparar
MADURO_ATE = pd.Timestamp("2025-09-30")  # 12+ meses de contrato na data de corte (30/09/2026)
JUROS = 0.03
TETO = 30000.0
DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
NOMES = {"atual": "Atual", "regras_bilosca": "Regras do time", "hibrida": "Proposta (híbrida)",
         "so_aperta": "Híbrida que só aperta", "mescla": "Híbrida que só aperta"}


def q(sql: str) -> pd.DataFrame:
    with psycopg.connect() as c:
        cur = c.execute(sql)
        return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def fator(prazo):
    """Valor emprestado por R$ 1 de parcela (tabela Price, 3% a.m.)."""
    return (1 - (1 + JUROS) ** (-prazo.astype(float))) / JUROS


def valor_cabe(cap, prazo):
    """Maior valor, em centavos, cuja parcela arredondada a centavos não passa de `cap` (como a política atual faz)."""
    f = fator(prazo)
    v = np.floor((cap + 0.005) * f * 100) / 100
    for _ in range(3):
        v = np.where(np.round(v / f, 2) > cap, np.round(v - 0.01, 2), v)
    return v


def carrega() -> tuple[pd.DataFrame, pd.DataFrame]:
    ped = q("""
        select p.id_pedido, p.id_cliente, p.data_pedido, p.valor_solicitado::float as valor_solicitado, p.prazo_meses,
               p.tipo_base, p.decisao, p.valor_aprovado::float as valor_aprovado, p.politica_aplicada, p.situacao_final,
               c.renda_declarada::float as renda, c.tipo_vinculo
        from hackathon.pedidos p join hackathon.clientes c using (id_cliente)""")
    ped["data_pedido"] = pd.to_datetime(ped.data_pedido)

    mov = q("""select id_cliente, mes_referencia, total_entradas::float as ent, total_saidas::float as sai,
                      dias_cheque_especial as cheq from hackathon.movimentacao_mensal""")
    mov["mes_referencia"] = pd.to_datetime(mov.mes_referencia)
    mov = mov.merge(ped[["id_cliente", "data_pedido"]], on="id_cliente")
    mov["lag"] = (mov.data_pedido.dt.year * 12 + mov.data_pedido.dt.month) - (
        mov.mes_referencia.dt.year * 12 + mov.mes_referencia.dt.month)  # 1 = mês anterior ao pedido
    mov = mov[(mov.lag >= 1) & (mov.lag <= 12)]
    f = pd.DataFrame({
        "ent_media": mov.groupby("id_cliente").ent.mean(),
        "ent_cv": mov.groupby("id_cliente").ent.std() / mov.groupby("id_cliente").ent.mean().replace(0, np.nan),
        "saida_maior_3m": mov[(mov.lag <= 3) & (mov.sai > mov.ent)].groupby("id_cliente").size() > 0,
        "cheque_2m": mov[(mov.lag <= 2) & (mov.cheq > 0)].groupby("id_cliente").size() > 0,
    })
    ped = ped.merge(f, left_on="id_cliente", right_index=True, how="left")
    ped[["saida_maior_3m", "cheque_2m"]] = ped[["saida_maior_3m", "cheque_2m"]].fillna(False).astype(bool)
    ped["apertada"] = ped.saida_maior_3m | ped.cheque_2m
    ped["renda_real"] = ped[["renda", "ent_media"]].min(axis=1)
    ped["parcela_sol"] = ped.valor_solicitado / fator(ped.prazo_meses)
    ped["parc_real"] = ped.parcela_sol / ped.renda_real

    hist_bureau = q("""select id_pedido, score, restricoes_ativas as restr, consultas_90_dias as consultas,
                              parcelas_outras_instituicoes::float as outras
                       from hackathon.bureau""")
    return ped, hist_bureau


def bureau_novos(novos: pd.DataFrame) -> pd.DataFrame:
    res = Bureau().consultar_varios(novos.id_cliente.tolist())
    falhas = [r for r in res if r.dados is None]
    if falhas:
        print(f"atenção: {len(falhas)} clientes sem bureau (ficam fora das políticas e aparecem no painel)", file=sys.stderr)
    b = pd.DataFrame([{**r.dados} for r in res if r.dados])
    b = b.rename(columns={"restricoes_ativas": "restr", "consultas_90_dias": "consultas",
                          "parcelas_outras_instituicoes": "outras"})
    return novos.merge(b[["id_cliente", "score", "restr", "consultas", "outras"]], on="id_cliente", how="left")


def confere_politica_atual(hist: pd.DataFrame) -> float:
    """Reproduz as decisões e valores da política atual no histórico; devolve a fração que bate."""
    a = hist[hist.politica_aplicada == "atual"].copy()
    aprova = (a.score > 600) & (a.renda > 2000) & (a.restr == 0)
    valor = np.minimum.reduce([a.valor_solicitado, np.full(len(a), TETO), valor_cabe(0.30 * a.renda, a.prazo_meses)])
    bate_dec = aprova == (a.decisao == "aprovado")
    bate_val = ~aprova | (np.abs(valor - a.valor_aprovado.fillna(0)) < 0.005)
    return float((bate_dec & bate_val).mean())


def valor_atual(n: pd.DataFrame) -> np.ndarray:
    return np.minimum.reduce([n.valor_solicitado, np.full(len(n), TETO), valor_cabe(0.30 * n.renda, n.prazo_meses)])


def funil(n: pd.DataFrame, passos: list) -> tuple[list[dict], pd.Series]:
    vivo = n.score.notna()
    out = [{"rotulo": "Pedidos", "restantes": int(len(n))}]
    for rotulo, cond in passos:
        vivo = vivo & cond.fillna(False)
        out.append({"rotulo": rotulo, "restantes": int(vivo.sum())})
    return out, vivo


# ordem em que src/politica.py decide: o motivo que fica é o do passo mais forte
PASSOS_PROPOSTA = [
    ("Sem restrição ativa", "restrição ativa no bureau"),
    ("Conta sem aperto nos 3 meses", "conta apertada"),
    ("Parcela até 28% da renda real", "parcela acima de 28% da renda real"),
]


def politicas(n: pd.DataFrame) -> list[dict]:
    """Atual: reprodução própria (bate 100% com o histórico). Regras e proposta: o CSV do src/politica_mescla.py,
    o mesmo que vai para o Teams (a proposta é idêntica ao saida/spread_final.csv)."""
    va = valor_atual(n)
    f_atual, ap_atual = funil(n, [("Score acima de 600", n.score > 600), ("Renda acima de R$ 2 mil", n.renda > 2000),
                                  ("Sem restrição ativa", n.restr == 0)])
    atual = pd.DataFrame({"aprovado": ap_atual, "valor": np.where(ap_atual, va, 0.0)}, index=n.index)

    parc_ref_real = (va / fator(n.prazo_meses)) / n.renda_real  # parcela do valor que a atual concederia
    f_regras, ap_regras = funil(n, [("Score acima de 600", n.score > 600), ("Renda acima de R$ 2 mil", n.renda > 2000),
                                    ("Sem restrição ativa", n.restr == 0),
                                    ("Conta sem aperto nos 3 meses", ~n.saida_maior_3m),
                                    ("Parcela até 28% da renda real", parc_ref_real <= 0.28)])
    csv_regras = n.regras_decisao.eq("APROVADO")
    if (csv_regras != ap_regras).any():
        print(f"atenção: o funil das regras difere do CSV em {(csv_regras != ap_regras).sum()} pedidos", file=sys.stderr)
    regras = pd.DataFrame({"aprovado": csv_regras, "valor": n.regras_valor.astype(float)}, index=n.index)

    motivo = n.motivo.fillna("")
    f_prop = [{"rotulo": "Pedidos", "restantes": int(len(n))}]
    restantes = len(n)
    for rotulo, inicio in PASSOS_PROPOSTA:
        restantes -= int(motivo.str.startswith(inicio).sum())
        f_prop.append({"rotulo": rotulo, "restantes": restantes})
    ap_prop = n.decisao.eq("APROVADO")
    f_prop.append({"rotulo": "Risco até 17,5% e ganho positivo", "restantes": int(ap_prop.sum())})
    prop = pd.DataFrame({"aprovado": ap_prop, "valor": n.valor_aprovado_ia.astype(float)}, index=n.index)

    return [
        resumo_politica(n, {"id": "atual", "nome": "Atual", "funil": f_atual}, atual, None),
        resumo_politica(n, {"id": "regras", "nome": "Regras do time", "funil": f_regras}, regras, atual),
        resumo_politica(n, {"id": "proposta", "nome": "Proposta", "funil": f_prop}, prop, atual),
    ]


def proposta_passos(n: pd.DataFrame) -> dict:
    """Parte 2 do painel (manual 5.1): a política proposta em passos, na ordem em que são aplicados."""
    motivo = n.motivo.fillna("")
    neg = lambda inicio: int(motivo.str.startswith(inicio).sum())  # noqa: E731
    risco = int((n.decisao.eq("NEGADO") & ~motivo.str.startswith(tuple(m for _, m in PASSOS_PROPOSTA))).sum())
    ap = n.decisao.eq("APROVADO")
    passos = [
        {"titulo": "Barreira · restrição", "texto": "Nega quem tem restrição ativa no bureau.",
         "negados": neg("restrição ativa no bureau")},
        {"titulo": "Barreira · conta apertada",
         "texto": "Nega quem teve saídas maiores que as entradas em algum dos 3 meses antes do pedido.",
         "negados": neg("conta apertada")},
        {"titulo": "Barreira · parcela pesada",
         "texto": "Nega quando a parcela do valor que a política atual concederia passa de 28% da renda real "
                  "(a menor entre a renda declarada e a média de entradas da conta).",
         "negados": neg("parcela acima de 28% da renda real")},
        {"titulo": "Risco e valor · modelo",
         "texto": "Um modelo treinado no histórico (corrigido para contratos ainda abertos) estima, para cada valor de "
                  "100% a 10% do solicitado, a chance de pagar em dia, com atraso ou não pagar. Aprova o valor de "
                  "maior ganho esperado (+15% em dia, +5% com atraso, −60% sem pagar) entre os que têm até 17,5% de "
                  "chance de não pagar. Se nenhum valor serve, nega.",
         "negados": risco},
        {"titulo": "Limites do valor",
         "texto": "Parcela até 28% da renda declarada, valor em múltiplos de R$ 100, entre R$ 500 e R$ 30 mil e "
                  "nunca acima do solicitado.",
         "reduzidos": int((ap & (n.valor_aprovado_ia < n.valor_solicitado - 0.005)).sum())},
        {"titulo": "Analista decide",
         "texto": "O score não é filtro: depois das barreiras ele não separa quem paga. A faixa de risco "
                  "(pontuação do Daniel) e a divergência com a política atual montam a fila de revisão; o analista "
                  "confirma, aprova com outro valor ou nega, com justificativa registrada.",
         "divergentes": int((n.decisao != n.atual_decisao).sum()), "laranja": int(n.faixa.eq("laranja").sum())},
    ]
    return {"passos": passos, "aprovados": int(ap.sum()), "volume": round(float(n.valor_aprovado_ia.sum()), 2),
            "faixas": {k: int(v) for k, v in n.faixa.value_counts().items()}}


def comparacao() -> list[dict]:
    """Resultado de cada política pelos três avaliadores e fora da amostra (src/politica_mescla.py --comparar)."""
    arq_nov, arq_obs = Path(str(COMPARACAO).format("novos")), Path(str(COMPARACAO).format("observado"))
    if not (arq_nov.exists() and arq_obs.exists()):
        print("atenção: sem saida/comparacao_mescla_*.csv; rode src/politica_mescla.py --comparar", file=sys.stderr)
        return []
    nov, obs = pd.read_csv(arq_nov, index_col=0), pd.read_csv(arq_obs, index_col=0)
    out = []
    for nome, r in nov.iterrows():
        ganhos = [r[f"ganho_{c}"] for c in ("gbm_corrigido", "sobrevivencia", "logistico")]
        out.append({"id": nome, "nome": NOMES.get(nome, nome), "aprovados": int(r.aprovados), "volume": float(r.volume),
                    "ganhoMin": round(float(min(ganhos))), "ganhoMax": round(float(max(ganhos))),
                    "foraAmostra": round(float(obs.loc[nome, "ganho_vs_atual"])) if nome in obs.index else None,
                    "calotesForaAmostra": int(obs.loc[nome, "nao_pagaram"]) if nome in obs.index else None})
    return out


FAIXAS_RISCO = ([0, 0.05, 0.10, 0.175], ["até 5%", "5% a 10%", "10% a 17,5%"])
HISTORICO = AQUI.parent / "src" / "data" / "historico.json"  # site/scripts/historico.py


def resultado_ia(n: pd.DataFrame) -> dict:
    """Lucro e prejuízo esperados das decisões da IA (Proposta) nos 2.000 novos, pelo modelo que decidiu.
    Prejuízo = 60% do valor vezes a chance de não pagar; lucro = o resto do ganho esperado (+15% em dia, +5% atraso)."""
    a = n[n.decisao.eq("APROVADO")].copy()
    a["v"] = a.valor_aprovado_ia.astype(float)
    a["p"] = a.p_nao_paga.astype(float)
    a["prejuizo"] = 0.60 * a.v * a.p
    a["lucro"] = a.ganho_esperado.astype(float) + a.prejuizo

    def soma(s: pd.DataFrame) -> dict:
        return {"aprovados": int(len(s)), "volume": round(float(s.v.sum())), "lucro": round(float(s.lucro.sum())),
                "prejuizo": round(float(s.prejuizo.sum())), "resultado": round(float(s.ganho_esperado.sum())),
                "calotes": round(float(s.p.sum()), 1)}

    cortes, rotulos = FAIXAS_RISCO
    risco = pd.cut(a.p, cortes, labels=rotulos, include_lowest=True)
    if risco.isna().any():
        print(f"atenção: {int(risco.isna().sum())} aprovados com risco acima de 17,5%", file=sys.stderr)
    out = {**soma(a),
           "porRisco": [{"faixa": f, **soma(a[risco == f])} for f in rotulos],
           "porFaixa": [{"faixa": f, **soma(a[a.faixa == f])} for f in ("verde", "amarela", "laranja") if (a.faixa == f).any()],
           "calibracao": None, "atual": None}

    if HISTORICO.exists():  # no histórico, o ganho observado ficou abaixo do que o modelo estimou
        e = json.loads(HISTORICO.read_text(encoding="utf-8"))["estimativa"]
        fator = e["ganhoObservado"] / e["ganhoEstimado"]
        out["calibracao"] = {"fator": round(fator, 4), "resultado": round(out["resultado"] * fator)}
    arq = Path(str(COMPARACAO).format("novos"))
    if arq.exists():
        nov = pd.read_csv(arq, index_col=0)
        if "hibrida" in nov.index and abs(nov.loc["hibrida", "gbm_corrigido"] - out["resultado"]) > 1:
            print(f"atenção: resultado da IA ({out['resultado']:,}) difere do comparativo "
                  f"({nov.loc['hibrida', 'gbm_corrigido']:,.0f})", file=sys.stderr)
        if "atual" in nov.index:
            r = nov.loc["atual"]
            out["atual"] = {"aprovados": int(r.aprovados), "volume": round(float(r.volume)),
                            "resultado": round(float(r.gbm_corrigido))}
    return out


def resumo_politica(n: pd.DataFrame, pol: dict, dec: pd.DataFrame, base: pd.DataFrame | None) -> dict:
    ap = dec.aprovado
    vol = n.assign(v=dec.valor)[ap].groupby("tipo_vinculo").agg(volume=("v", "sum"), pedidos=("v", "size"))
    out = {
        "id": pol["id"], "nome": pol["nome"],
        "funil": pol["funil"],
        "aprovados": int(ap.sum()),
        "volume": round(float(dec.valor.sum()), 2),
        "reduzidos": int((ap & (dec.valor < n.valor_solicitado - 0.005)).sum()),
        "porVinculo": [{"vinculo": k, "volume": round(float(r.volume), 2), "pedidos": int(r.pedidos)}
                       for k, r in vol.sort_values("volume", ascending=False).iterrows()],
    }
    if base is not None:
        a, b = base.aprovado, ap
        out["vsAtual"] = {
            "aprovaAMais": int((b & ~a).sum()), "volumeAMais": round(float(dec.valor[b & ~a].sum()), 2),
            "negaAMais": int((a & ~b).sum()), "volumeAMenos": round(float(base.valor[a & ~b].sum()), 2),
            "valorMudou": int((a & b & (np.abs(dec.valor - base.valor) > 0.005)).sum()),
            "iguais": int(((a == b) & (np.abs(dec.valor - base.valor) <= 0.005)).sum()),
        }
    return out


def safras(hist: pd.DataFrame) -> dict:
    ap = hist[hist.decisao == "aprovado"].copy()
    ap["mes"] = ap.data_pedido.dt.to_period("M")
    ap["inad"] = ap.situacao_final == "inadimplente"
    g = ap.groupby("mes").agg(aprovados=("inad", "size"), inadimplentes=("inad", "sum"))
    madura = ap[ap.data_pedido <= MADURO_ATE]
    return {
        "mediaMadura": round(float(madura.inad.mean()), 4),
        "contratosMaduros": int(len(madura)),
        "meses": [{"mes": str(m), "aprovados": int(r.aprovados), "inadimplentes": int(r.inadimplentes),
                   "taxa": round(r.inadimplentes / r.aprovados, 4),
                   "maduro": bool(m.end_time.normalize() <= MADURO_ATE)} for m, r in g.iterrows()],
    }


def faixas(serie: pd.Series, cortes: list, rotulos: list[str]) -> list[dict]:
    c = pd.cut(serie, cortes, labels=rotulos, right=False).value_counts().reindex(rotulos, fill_value=0)
    return [{"faixa": k, "n": int(v)} for k, v in c.items()]


def pct(x: list[float], p: float) -> float:
    s = sorted(x)
    return round(s[min(len(s) - 1, int(p * len(s)))], 3)


def api_bureau(n: pd.DataFrame) -> dict:
    linhas = [json.loads(x) for x in LOG.read_text(encoding="utf-8").splitlines() if x.strip()] if LOG.exists() else []
    lat = [x["segundos"] for x in linhas]
    status: dict[str, int] = {}
    for x in linhas:
        status[str(x["status"])] = status.get(str(x["status"]), 0) + 1
    por_cliente: dict[str, int] = {}
    for x in linhas:
        por_cliente[x["id_cliente"]] = max(por_cliente.get(x["id_cliente"], 0), x["tentativa"])
    cortes = [0, 0.25, 0.5, 1, 2, 5, float("inf")]
    rot = ["< 0,25 s", "0,25–0,5 s", "0,5–1 s", "1–2 s", "2–5 s", "≥ 5 s"]
    hist = faixas(pd.Series(lat, dtype=float), cortes, rot) if lat else []
    return {
        "clientes": int(len(n)),
        "comBureau": int(n.score.notna().sum()),
        "chamadas": len(linhas),
        "status": status,
        "clientesComRetry": sum(v > 1 for v in por_cliente.values()),
        "maxTentativas": max(por_cliente.values(), default=0),
        "latencia": {"p50": pct(lat, .5), "p90": pct(lat, .9), "p95": pct(lat, .95), "p99": pct(lat, .99),
                     "max": round(max(lat), 3), "media": round(statistics.mean(lat), 3)} if lat else None,
        "histograma": hist,
        "desde": linhas[0]["em"] if linhas else None,
        "ate": linhas[-1]["em"] if linhas else None,
        "config": {"timeoutSeg": 10, "tentativas": 6, "esperaBaseSeg": 0.5, "paralelo": 10},
    }


def bureau_perfil(n: pd.DataFrame) -> dict:
    b = n[n.score.notna()]
    return {
        "scoreMediano": int(b.score.median()),
        "scoreFaixas": faixas(b.score, [0, 500, 600, 700, 800, 900, 1001],
                              ["< 500", "500–599", "600–699", "700–799", "800–899", "900+"]),
        "comRestricao": int((b.restr > 0).sum()),
        "consultas4mais": int((b.consultas >= 4).sum()),
        "total": int(len(b)),
    }


def pedidos_novos(n: pd.DataFrame, hist: pd.DataFrame) -> dict:
    dow = n.data_pedido.dt.day_of_week.value_counts().reindex(range(7), fill_value=0)
    meses_hist = hist.data_pedido.dt.to_period("M").nunique()
    return {
        "total": int(len(n)),
        "periodo": [n.data_pedido.min().strftime("%Y-%m-%d"), n.data_pedido.max().strftime("%Y-%m-%d")],
        "porDiaSemana": [{"dia": DIAS[i], "n": int(v)} for i, v in dow.items()],
        "mediaMensalHistorico": round(len(hist) / meses_hist),
        "valorSolicitado": round(float(n.valor_solicitado.sum()), 2),
        "valorMediano": round(float(n.valor_solicitado.median()), 2),
        "comContaApertada": int(n.apertada.sum()),
        "parcelaAcima28Real": int((n.parc_real > 0.28).sum()),
    }


def sinais(d: pd.DataFrame, valor: pd.Series) -> dict[str, pd.Series]:
    """Os sinais que a análise do time encontrou, medidos do mesmo jeito no histórico e nos novos.
    `valor` é o valor aprovado (histórico) ou o que a política atual concederia (novos)."""
    parcela = valor / fator(d.prazo_meses)
    real = parcela / d.renda_real
    comprom = (parcela + d.outras.fillna(0)) / d.renda_real
    vinc = d.tipo_vinculo
    return {
        "saídas maiores que as entradas em algum dos 3 meses antes do pedido": d.saida_maior_3m,
        "parcela acima de 28% da renda real": real > 0.28,
        "parcela mais dívidas em outras instituições acima de 35% da renda real": comprom >= 0.35,
        "entradas da conta instáveis (variação de 16% ou mais)": d.ent_cv >= 0.16,
        "prazo de 6 ou 12 meses": d.prazo_meses.isin([6, 12]),
        "prazo de 36 meses": d.prazo_meses == 36,
        "vínculo de autônomo ou empresário": vinc.isin(["autonomo", "empresario"]),
        "vínculo de aposentado": vinc == "aposentado",
        "1 restrição ativa no bureau": d.restr >= 1,
        "score até 600": d.score <= 600,
        "score de 601 a 700": d.score.between(601, 700),
        "score acima de 800": d.score > 800,
        "nenhuma das duas barreiras (conta folgada e parcela até 28% da renda real)": ~d.saida_maior_3m & (real <= 0.28),
    }


def padroes(hist: pd.DataFrame, n: pd.DataFrame) -> dict:
    """Parte 1 do painel (manual 5.1): padrões no formato do manual, medidos nos contratos maduros (12+ meses)."""
    m = hist[(hist.decisao == "aprovado") & (hist.data_pedido <= MADURO_ATE)].copy()
    m["inad"] = m.situacao_final == "inadimplente"
    media = float(m.inad.mean())
    s_hist, s_novos = sinais(m, m.valor_aprovado), sinais(n, pd.Series(valor_atual(n), index=n.index))
    itens = []
    for grupo, mascara in s_hist.items():
        mascara = mascara.fillna(False).astype(bool)
        k = int(mascara.sum())
        if k < 30:
            continue
        taxa = float(m.inad[mascara].mean())
        itens.append({"grupo": grupo, "taxa": round(taxa, 4), "aprox": False, "clientes": k,
                      "vsMedia": round(taxa / media, 2),
                      "novos": int(s_novos[grupo].fillna(False).astype(bool).sum())})
    itens.sort(key=lambda i: -i["vsMedia"])
    return {"media": round(media, 4), "itens": itens, "base": int(len(m)),
            "fonte": f"histórico maduro: {len(m):,} contratos aprovados com 12+ meses".replace(",", ".")}


def sem_ids(texto: str) -> None:
    achou = re.findall(r"\b[CP]-\d{5}\b", texto)  # formato dos ids do kit
    if achou:
        raise SystemExit(f"o JSON tem {len(achou)} id(s) de cliente/pedido; nada foi gravado")


def main() -> None:
    sys.stderr.reconfigure(encoding="utf-8")
    load_dotenv(ROOT / ".env")
    ped, hist_bureau = carrega()
    hist = ped[ped.tipo_base == "historico"].merge(hist_bureau, on="id_pedido", how="left")
    conf = confere_politica_atual(hist)
    print(f"política atual reproduzida em {conf:.2%} das decisões do histórico", file=sys.stderr)

    n = bureau_novos(ped[ped.tipo_base == "novo"].reset_index(drop=True))
    if not DECISOES.exists():
        raise SystemExit("falta saida/decisoes_mescla.csv: cd src && python gerar_decisoes.py && python politica_mescla.py")
    dec = pd.read_csv(DECISOES, dtype={"id_pedido": str}).rename(columns={"valor_aprovado": "valor_aprovado_ia"})
    n = n.drop(columns=["decisao", "valor_aprovado"]).merge(dec, on="id_pedido", how="left")
    if n.decisao.isna().any():
        raise SystemExit("decisoes_mescla.csv não cobre os 2.000 pedidos novos")
    resumo = politicas(n)
    for r in resumo:
        print(f"  {r['nome']}: {r['aprovados']} aprovados · R$ {r['volume']:,.2f}", file=sys.stderr)

    dados = {
        "geradoEm": datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "corte": "2026-09-30",
        "reproducaoAtual": round(conf, 4),
        "pedidos": pedidos_novos(n, hist),
        "politicas": resumo,
        "safras": safras(hist),
        "bureau": bureau_perfil(n),
        "api": api_bureau(n),
        "padroes": padroes(hist, n),
        "proposta": proposta_passos(n),
        "resultadoIA": resultado_ia(n),
        "comparacao": comparacao(),
    }
    texto = json.dumps(dados, ensure_ascii=False, indent=1)
    sem_ids(texto)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(texto + "\n", encoding="utf-8")
    print(f"gravado {SAIDA.relative_to(ROOT)} ({len(texto) / 1024:.1f} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
