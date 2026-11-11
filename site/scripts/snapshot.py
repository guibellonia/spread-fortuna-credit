"""Gera os dados do painel (site/src/data/dashboard.json) a partir do banco e da API do bureau.

O JSON vai para um site público, então só saem AGREGADOS: nenhum id de cliente ou de pedido, nenhuma linha
individual. O script confere isso antes de gravar e para se encontrar algum id.

Uso, da raiz do repositório, com o .env preenchido (modelo em .env.example):
    .venv/Scripts/python site/scripts/snapshot.py

O bureau é consultado com retry e cache em disco (data/cache/bureau/); rodar de novo só busca quem faltou.
"""
from __future__ import annotations

import csv
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
PADROES = ROOT / "analysis" / "out" / "patterns.csv"
MADURO_ATE = pd.Timestamp("2025-09-30")  # 12+ meses de contrato na data de corte (30/09/2026)
JUROS = 0.03
TETO = 30000.0
DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

# Padrões em destaque no painel, no formato do manual. Os números vêm de analysis/out/patterns.csv.
DESTAQUES = [
    ("Saídas / entradas", "100%+", "saídas maiores que as entradas no ano antes do pedido"),
    ("Meses com cheque especial (12m)", "3-5", "3 a 5 meses de cheque especial no ano antes do pedido"),
    ("Renda real / declarada", "<60%", "renda na conta abaixo de 60% da declarada"),
    ("Parcela / renda declarada", "30%+", "parcela acima de 30% da renda declarada"),
    ("Restrições ativas", "1", "1 restrição ativa no bureau"),
    ("Consultas ao CPF em 90 dias", "4+", "4 ou mais consultas ao CPF em 90 dias"),
    ("Prazo (meses)", "6", "prazo de 6 meses"),
    ("Tipo de vínculo", "aposentado", "vínculo de aposentado"),
]


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
        "saida_maior_3m": mov[(mov.lag <= 3) & (mov.sai > mov.ent)].groupby("id_cliente").size() > 0,
        "cheque_2m": mov[(mov.lag <= 2) & (mov.cheq > 0)].groupby("id_cliente").size() > 0,
    })
    ped = ped.merge(f, left_on="id_cliente", right_index=True, how="left")
    ped[["saida_maior_3m", "cheque_2m"]] = ped[["saida_maior_3m", "cheque_2m"]].fillna(False).astype(bool)
    ped["apertada"] = ped.saida_maior_3m | ped.cheque_2m
    ped["renda_real"] = ped[["renda", "ent_media"]].min(axis=1)
    ped["parcela_sol"] = ped.valor_solicitado / fator(ped.prazo_meses)
    ped["parc_real"] = ped.parcela_sol / ped.renda_real

    hist_bureau = q("""select id_pedido, score, restricoes_ativas as restr, consultas_90_dias as consultas
                       from hackathon.bureau""")
    return ped, hist_bureau


def bureau_novos(novos: pd.DataFrame) -> pd.DataFrame:
    res = Bureau().consultar_varios(novos.id_cliente.tolist())
    falhas = [r for r in res if r.dados is None]
    if falhas:
        print(f"atenção: {len(falhas)} clientes sem bureau (ficam fora das políticas e aparecem no painel)", file=sys.stderr)
    b = pd.DataFrame([{**r.dados} for r in res if r.dados])
    b = b.rename(columns={"restricoes_ativas": "restr", "consultas_90_dias": "consultas"})
    return novos.merge(b[["id_cliente", "score", "restr", "consultas"]], on="id_cliente", how="left")


def confere_politica_atual(hist: pd.DataFrame) -> float:
    """Reproduz as decisões e valores da política atual no histórico; devolve a fração que bate."""
    a = hist[hist.politica_aplicada == "atual"].copy()
    aprova = (a.score > 600) & (a.renda > 2000) & (a.restr == 0)
    valor = np.minimum.reduce([a.valor_solicitado, np.full(len(a), TETO), valor_cabe(0.30 * a.renda, a.prazo_meses)])
    bate_dec = aprova == (a.decisao == "aprovado")
    bate_val = ~aprova | (np.abs(valor - a.valor_aprovado.fillna(0)) < 0.005)
    return float((bate_dec & bate_val).mean())


def politicas(n: pd.DataFrame) -> tuple[list[dict], pd.Series]:
    valor_atual = np.minimum.reduce([n.valor_solicitado, np.full(len(n), TETO), valor_cabe(0.30 * n.renda, n.prazo_meses)])
    tem_bureau = n.score.notna()
    conta = ("Conta sem aperto nos 3 meses", ~n.apertada)
    parcela = ("Parcela até 28% da renda real", n.parc_real <= 0.28)
    return [
        dict(id="atual", nome="Atual", valor=valor_atual, passos=[
            ("Score acima de 600", n.score > 600),
            ("Renda acima de R$ 2 mil", n.renda > 2000),
            ("Sem restrição ativa", n.restr == 0)]),
        dict(id="piso", nome="Piso seguro", valor=valor_atual, passos=[
            ("Score acima de 600", n.score > 600),
            ("Renda acima de R$ 2 mil", n.renda > 2000),
            ("Sem restrição ativa", n.restr == 0), conta, parcela]),
        dict(id="ampliada", nome="Ampliada", valor=valor_atual, passos=[
            ("Score a partir de 450", n.score >= 450),
            ("Renda acima de R$ 2 mil", n.renda > 2000),
            ("Até 1 restrição", n.restr <= 1), conta, parcela]),
    ], tem_bureau


def aplica(n: pd.DataFrame, pol: dict, tem_bureau) -> pd.DataFrame:
    vivo = tem_bureau.copy()
    funil = [{"rotulo": "Pedidos", "restantes": int(len(n))}]
    for rotulo, cond in pol["passos"]:
        vivo &= cond.fillna(False)
        funil.append({"rotulo": rotulo, "restantes": int(vivo.sum())})
    pol["funil"] = funil
    return pd.DataFrame({"aprovado": vivo, "valor": np.where(vivo, pol["valor"], 0.0)}, index=n.index)


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


def padroes() -> dict:
    with PADROES.open(encoding="utf-8") as f:
        linhas = {(r["variavel"], r["grupo"]): r for r in csv.DictReader(f)}
    itens, medias = [], []
    for var, grupo, texto in DESTAQUES:
        r = linhas.get((var, grupo))
        if not r:
            print(f"atenção: padrão {var} / {grupo} não está em {PADROES.name}", file=sys.stderr)
            continue
        taxa, vs = float(r["inad_proj"]), float(r["vs_media"])
        medias.append(taxa / vs)
        itens.append({"grupo": texto, "taxa": round(min(taxa, 1.0), 4), "aprox": taxa >= 0.995,
                      "clientes": int(r["clientes"]), "vsMedia": round(vs, 2)})
    return {"media": round(statistics.mean(medias), 4) if medias else None, "itens": itens,
            "fonte": "analysis/out/patterns.csv"}


def sem_ids(texto: str) -> None:
    achou = re.findall(r"\b[CP]-\d{3,}\b", texto)
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
    pols, tem_bureau = politicas(n)
    decs = [aplica(n, p, tem_bureau) for p in pols]
    resumo = [resumo_politica(n, p, d, None if i == 0 else decs[0]) for i, (p, d) in enumerate(zip(pols, decs))]
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
        "padroes": padroes(),
    }
    texto = json.dumps(dados, ensure_ascii=False, indent=1)
    sem_ids(texto)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(texto + "\n", encoding="utf-8")
    print(f"gravado {SAIDA.relative_to(ROOT)} ({len(texto) / 1024:.1f} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
