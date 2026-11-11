"""Gera os dados da página "Histórico" do painel (site/src/data/historico.json): a Proposta aplicada aos 10.000
pedidos do histórico, comparada com o que a Fortuna decidiu e com o desfecho observado.

Sem vazamento: cada trimestre é decidido por um modelo da Proposta (src/cenarios.treinar_corrigido, o mesmo da
entrega) treinado sem aquele trimestre. As barreiras e os parâmetros são os de src/politica.py.

Contas (regra da nota: +15% em dia, +5% com atraso, −60% sem pagar, sobre o valor aprovado):
- real: o que a Fortuna aprovou, com o desfecho observado;
- proposta, observado: pedidos que as duas aprovam, no valor da Proposta (nunca maior que o da Fortuna; supõe o
  mesmo desfecho com valor menor, o que é conservador para a Proposta);
- proposta, estimado: pedidos que a Fortuna negou e a Proposta aprova (sem desfecho), pelo ganho esperado do modelo.

Só saem agregados: nenhum id de cliente ou de pedido. Uso, da raiz do repositório, depois de
`cd src && python gerar_decisoes.py` (que grava saida/hist.pkl), com o banco no .env (PG*) ou FORTUNA_DSN:
    .venv/Scripts/python site/scripts/historico.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import roc_auc_score

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(ROOT / "src"))
from snapshot import sem_ids  # noqa: E402

SAIDA = AQUI.parent / "src" / "data" / "historico.json"
MADURO_ATE = pd.Timestamp("2025-09-30")  # 12+ meses de contrato no corte (30/09/2026), como no snapshot
FAIXAS = [0, 0.05, 0.10, 0.175, 0.25, 1.0]
ROTULOS = ["até 5%", "5% a 10%", "10% a 17,5%", "17,5% a 25%", "acima de 25%"]
AJUSTES = [  # motivo de src/politica.py (pelo início) -> rótulo; ordem em que a Proposta decide
    ("restrição ativa", "restricao", "Barreira · restrição ativa"),
    ("conta apertada", "apertada", "Barreira · conta apertada"),
    ("parcela acima de 28% da renda real", "parcela", "Barreira · parcela acima de 28% da renda real"),
    ("risco acima do limite", "risco", "Modelo · risco acima de 17,5%"),
]


def decide(h: pd.DataFrame) -> pd.DataFrame:
    """Proposta trimestre a trimestre, com o modelo treinado nos outros trimestres. Também devolve o risco estimado
    no valor que a Fortuna aprovou (para medir a estimativa contra o desfecho)."""
    from cenarios import m_wrap, treinar_corrigido
    from modelo import probabilidades
    from politica import politica_proposta

    tri = h.data_pedido.dt.to_period("Q")
    partes = []
    for q in sorted(tri.unique()):
        modelo = m_wrap(treinar_corrigido(h[tri != q])[0])
        t = h[tri == q].reset_index(drop=True)
        d = politica_proposta(t, modelo)
        ap = t.decisao.eq("aprovado").to_numpy()
        d["p_valor_fortuna"] = np.nan
        if ap.any():
            d.loc[ap, "p_valor_fortuna"] = probabilidades(modelo, t[ap], t.loc[ap, "valor_aprovado"])[:, 2]
        partes.append(d)
        print(f"  {q}: {int(d.aprova.sum())} de {len(d)} aprovados pela Proposta", file=sys.stderr)
    return pd.concat(partes).merge(h, on="id_pedido", validate="one_to_one")


def contas(d: pd.DataFrame) -> pd.DataFrame:
    from modelo import CLASSES, GANHO

    d = d.copy()
    d["A"] = d.decisao.eq("aprovado")
    d["P"] = d.aprova.astype(bool)
    d["vF"] = np.where(d.A, d.valor_aprovado.fillna(0), 0.0)
    d["vP"] = np.where(d.P, d.valor, 0.0)
    d["g"] = d.situacao_final.map(CLASSES).map(lambda c: GANHO[int(c)] if pd.notna(c) else 0.0)
    d["calote"] = d.situacao_final.eq("inadimplente")
    d["res_real"] = d.vF * d.g
    d["res_prop"] = np.where(d.A & d.P, d.vP * d.g, 0.0)
    d["res_est"] = np.where(~d.A & d.P, d.ganho_esperado, 0.0)
    if ((d.A & d.P) & (d.vP > d.vF + 0.005)).any():
        raise SystemExit("a Proposta deu valor maior que o da Fortuna em pedido com desfecho; revise a conta")
    return d


def taxa(calotes: int, n: int) -> float | None:
    return round(calotes / n, 4) if n else None


def resumo(d: pd.DataFrame) -> dict:
    A, P = d.A, d.P
    ambos, so_f, so_p = A & P, A & ~P, ~A & P
    reduz = ambos & (d.valor < d.vF - 0.005)

    matriz = []
    for f_ap, p_ap, m in [(True, True, ambos), (True, False, so_f), (False, True, so_p), (False, False, ~A & ~P)]:
        s = d[m]
        matriz.append({"fortuna": f_ap, "proposta": p_ap, "pedidos": int(len(s)),
                       "volumeReal": round(float(s.vF.sum())), "volumeProposta": round(float(s.vP.sum())),
                       "calotes": int(s.calote.sum()) if f_ap else None,
                       "taxa": taxa(int(s.calote.sum()), len(s)) if f_ap else None})

    ajustes, motivo = [], d.motivo.fillna("")
    for inicio, id_, rotulo in AJUSTES:
        s = d[so_f & motivo.str.startswith(inicio)]
        ajustes.append({"id": id_, "rotulo": rotulo, "pedidos": int(len(s)), "calotes": int(s.calote.sum()),
                        "taxa": taxa(int(s.calote.sum()), len(s)), "efeito": round(float(-s.res_real.sum())),
                        "estimado": False})
    s = d[reduz]
    ajustes.append({"id": "valor", "rotulo": "Valor · parcela até 28% e melhor valor do modelo", "pedidos": int(len(s)),
                    "calotes": int(s.calote.sum()), "taxa": taxa(int(s.calote.sum()), len(s)),
                    "efeito": round(float((d.res_prop - d.res_real)[ambos].sum())), "estimado": False})
    s = d[so_p]
    ajustes.append({"id": "novos", "rotulo": "Aprovações que a Fortuna negou", "pedidos": int(len(s)),
                    "calotes": None, "taxa": None, "pNaoPaga": round(float(np.average(s.p_nao_paga, weights=s.vP)), 4)
                    if len(s) else None, "efeito": round(float(s.res_est.sum())), "estimado": True})

    meses = []
    for m, s in d.groupby(d.data_pedido.dt.to_period("M")):
        meses.append({"mes": str(m), "maduro": bool(m.end_time.normalize() <= MADURO_ATE),
                      "real": round(float(s.res_real.sum())), "proposta": round(float(s.res_prop.sum())),
                      "estimado": round(float(s.res_est.sum())),
                      "aprovadosReal": int(s.A.sum()), "calotesReal": int((s.A & s.calote).sum()),
                      "calotesProposta": int((s.A & s.P & s.calote).sum())})

    return {
        "pedidos": int(len(d)),
        "periodo": [d.data_pedido.min().strftime("%Y-%m"), d.data_pedido.max().strftime("%Y-%m")],
        "real": {"aprovados": int(A.sum()), "volume": round(float(d.vF.sum())), "resultado": round(float(d.res_real.sum())),
                 "calotes": int((A & d.calote).sum()), "taxa": taxa(int((A & d.calote).sum()), int(A.sum()))},
        "proposta": {"aprovados": int(P.sum()), "comDesfecho": int(ambos.sum()),
                     "volume": round(float(d.vP[ambos].sum())), "resultado": round(float(d.res_prop.sum())),
                     "calotes": int((ambos & d.calote).sum()), "taxa": taxa(int((ambos & d.calote).sum()), int(ambos.sum())),
                     "novos": int(so_p.sum()), "volumeNovos": round(float(d.vP[so_p].sum())),
                     "resultadoNovos": round(float(d.res_est.sum()))},
        "matriz": matriz,
        "ajustes": ajustes,
        "meses": meses,
    }


def estimativa(d: pd.DataFrame) -> dict:
    """A estimativa de risco contra o desfecho, nos contratos maduros que a Fortuna aprovou."""
    m = d[d.A & (d.data_pedido <= MADURO_ATE)]
    faixa = pd.cut(m.p_valor_fortuna, FAIXAS, labels=ROTULOS, include_lowest=True)
    faixas = [{"faixa": f, "pedidos": int(len(s)), "estimada": round(float(s.p_valor_fortuna.mean()), 4),
               "observada": round(float(s.calote.mean()), 4)}
              for f, s in m.groupby(faixa, observed=True)]
    amb = m[m.P]
    return {
        "contratos": int(len(m)), "calotes": int(m.calote.sum()),
        "aucModelo": round(float(roc_auc_score(m.calote, m.p_valor_fortuna)), 3),
        "aucScore": round(float(roc_auc_score(m.calote, -m.score)), 3),
        "faixas": faixas,
        "ganhoEstimado": round(float(amb.ganho_esperado.sum())), "ganhoObservado": round(float(amb.res_prop.sum())),
        "aprovadosProposta": int(len(amb)),
    }


def piloto(d: pd.DataFrame) -> dict | None:
    """No piloto (out/25 a mar/26) a Fortuna aprovou pedidos que a regra atual nega: é o único desfecho observado de
    quem a regra atual negaria. Mostra como foram os que a Proposta também aprova e os que ela nega."""
    regra = (d.score > 600) & (d.renda_declarada > 2000) & (d.restricoes_ativas == 0)
    s = d[d.politica_aplicada.eq("piloto") & d.A & ~regra]
    if s.empty:
        return None
    sim, nao = s[s.P], s[~s.P]
    return {"aprovadosForaDaRegra": int(len(s)),
            "propostaAprova": int(len(sim)), "taxaAprova": taxa(int(sim.calote.sum()), len(sim)),
            "propostaNega": int(len(nao)), "taxaNega": taxa(int(nao.calote.sum()), len(nao))}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    load_dotenv(ROOT / ".env")
    if not os.environ.get("FORTUNA_DSN"):  # src/db.py usa FORTUNA_DSN; o libpq completa host, porta e senha pelos PG*
        os.environ["FORTUNA_DSN"] = f"dbname={os.environ.get('PGDATABASE', 'fortuna')}"
    arq = ROOT / "saida" / "hist.pkl"
    if not arq.exists():
        raise SystemExit("falta saida/hist.pkl: cd src && python gerar_decisoes.py")
    h = pd.read_pickle(arq).reset_index(drop=True)
    print(f"histórico: {len(h)} pedidos; decidindo cada trimestre sem ele no treino", file=sys.stderr)
    d = contas(decide(h))

    dados = {
        "geradoEm": datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "maduroAte": MADURO_ATE.strftime("%Y-%m-%d"),
        "bases": {"todos": resumo(d), "maduros": resumo(d[d.data_pedido <= MADURO_ATE])},
        "estimativa": estimativa(d),
        "piloto": piloto(d),
    }
    for nome, b in dados["bases"].items():
        dif = b["proposta"]["resultado"] - b["real"]["resultado"]
        soma = sum(a["efeito"] for a in b["ajustes"] if not a["estimado"])
        if abs(dif - soma) > len(b["ajustes"]):  # arredondamento de cada parcela
            raise SystemExit(f"{nome}: os ajustes ({soma}) não somam a diferença observada ({dif})")
        print(f"  {nome}: real R$ {b['real']['resultado']:,} · proposta R$ {b['proposta']['resultado']:,} "
              f"(observado, {dif:+,}) · novos estimados R$ {b['proposta']['resultadoNovos']:,}", file=sys.stderr)
    texto = json.dumps(dados, ensure_ascii=False, indent=1)
    sem_ids(texto)
    SAIDA.write_text(texto + "\n", encoding="utf-8")
    print(f"gravado {SAIDA.relative_to(ROOT)} ({len(texto) / 1024:.1f} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
