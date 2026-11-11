"""Ferramenta determinística: padrões de inadimplência no histórico, no formato do manual (seção 5.1).

Base: pedidos aprovados até 31/03/2026 (6+ meses até a data de corte), onde o desfecho já é observável.
Inadimplência = situacao_final 'inadimplente' (parcela vencida e não paga há 90+ dias).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, _tree

from features import parcela_price
from modelo import DATA_MATURIDADE

SAIDA = Path(__file__).resolve().parents[1] / "saida"


def base(hist: pd.DataFrame) -> pd.DataFrame:
    b = hist[(hist.decisao == "aprovado") & (hist.data_pedido <= DATA_MATURIDADE)].copy()
    b["inad"] = (b.situacao_final == "inadimplente").astype(int)
    b["atraso"] = b.situacao_final.isin(["em_atraso", "quitado_com_atraso"]).astype(int)
    b["comp_aprov"] = parcela_price(b.valor_aprovado, b.prazo_meses) / b.renda_declarada
    return b


# grupos candidatos: (descrição em linguagem de negócio, filtro)
GRUPOS = [
    ("parcela entre 25% e 30% da renda declarada", lambda b: (b.comp_aprov > 0.25) & (b.comp_aprov <= 0.30)),
    ("parcela acima de 20% da renda declarada", lambda b: b.comp_aprov > 0.20),
    ("parcela de até 10% da renda declarada", lambda b: b.comp_aprov <= 0.10),
    ("2 ou mais meses com saldo negativo na conta nos últimos 12 meses", lambda b: b.mov_meses_cheque >= 2),
    ("nenhum mês com saldo negativo na conta", lambda b: b.mov_meses_cheque == 0),
    ("saldo médio da conta abaixo de R$ 12 mil", lambda b: b.mov_saldo_medio < 12000),
    ("sobra mensal (entradas menos saídas) abaixo de R$ 1.750", lambda b: (b.mov_entradas_media - b.mov_saidas_media) < 1750),
    ("mais de 3 consultas ao CPF nos últimos 90 dias", lambda b: b.consultas_90_dias > 3),
    ("restrição ativa no bureau (aprovados no piloto)", lambda b: b.restricoes_ativas > 0),
    ("score do bureau até 600 (aprovados no piloto)", lambda b: b.score <= 600),
    ("score do bureau acima de 850", lambda b: b.score > 850),
    ("prazo de 6 meses", lambda b: b.prazo_meses == 6),
    ("prazo de 36 meses", lambda b: b.prazo_meses == 36),
    ("valor solicitado acima de R$ 12 mil", lambda b: b.valor_solicitado > 12000),
    ("vínculo empresário", lambda b: b.tipo_vinculo == "empresario"),
    ("vínculo aposentado", lambda b: b.tipo_vinculo == "aposentado"),
    ("renda declarada até R$ 2.000 (aprovados no piloto)", lambda b: b.renda_declarada <= 2000),
]


def padroes_por_grupo(b: pd.DataFrame, min_clientes=40) -> list[dict]:
    media = b.inad.mean()
    out = []
    for desc, f in GRUPOS:
        g = b[f(b)]
        if len(g) < min_clientes:
            continue
        taxa = g.inad.mean()
        out.append({
            "grupo": desc, "clientes": int(len(g)), "inadimplencia": round(float(taxa), 4),
            "media": round(float(media), 4), "atraso": round(float(g.atraso.mean()), 4),
            "risco_relativo": round(float(taxa / media), 2),
            "frase": f"Clientes com {desc} têm inadimplência de {taxa:.0%}, contra {media:.0%} da média. "
                     f"Afeta {len(g)} clientes.",
        })
    return sorted(out, key=lambda d: -abs(np.log(max(d["risco_relativo"], 0.01))))


NOMES = {"comp_aprov": "parcela/renda", "mov_meses_cheque": "meses com saldo negativo",
         "consultas_90_dias": "consultas ao CPF em 90 dias", "mov_saldo_medio": "saldo médio da conta",
         "sobra_mensal": "sobra mensal", "restricoes_ativas": "restrições ativas", "score": "score",
         "prazo_meses": "prazo", "renda_declarada": "renda declarada", "mov_entradas_cv": "variação das entradas"}


def combinacoes_arvore(b: pd.DataFrame, profundidade=3, min_folha=60) -> list[dict]:
    """Árvore de decisão rasa: encontra combinações de atributos com inadimplência muito diferente da média."""
    cols = list(NOMES)
    X = b[cols].fillna(0)
    t = DecisionTreeClassifier(max_depth=profundidade, min_samples_leaf=min_folha, random_state=0).fit(X, b.inad)
    tr, media, out = t.tree_, b.inad.mean(), []

    def fmt(c, v):
        if c == "comp_aprov":
            return f"{v:.0%}"
        if c in ("mov_saldo_medio", "sobra_mensal", "renda_declarada"):
            return f"R$ {v:,.0f}".replace(",", ".")
        return f"{v:.1f}"

    def anda(no, regras):
        if tr.feature[no] == _tree.TREE_UNDEFINED:
            mask = np.ones(len(X), bool)
            for c, op, v in regras:
                mask &= (X[c] <= v) if op == "<=" else (X[c] > v)
            g = b[mask]
            taxa = g.inad.mean()
            desc = " e ".join(f"{NOMES[c]} {'até' if op == '<=' else 'acima de'} {fmt(c, v)}" for c, op, v in regras)
            out.append({"grupo": desc, "clientes": int(len(g)), "inadimplencia": round(float(taxa), 4),
                        "media": round(float(media), 4), "risco_relativo": round(float(taxa / media), 2),
                        "frase": f"Clientes com {desc} têm inadimplência de {taxa:.0%}, contra {media:.0%} da média. "
                                 f"Afeta {len(g)} clientes."})
            return
        c, v = cols[tr.feature[no]], tr.threshold[no]
        anda(tr.children_left[no], regras + [(c, "<=", v)])
        anda(tr.children_right[no], regras + [(c, ">", v)])

    anda(0, [])
    return sorted(out, key=lambda d: -d["inadimplencia"])


def calcular(hist: pd.DataFrame) -> dict:
    b = base(hist)
    b["sobra_mensal"] = b.mov_entradas_media - b.mov_saidas_media
    res = {"base": {"clientes": int(len(b)), "inadimplencia_media": round(float(b.inad.mean()), 4),
                    "atraso_medio": round(float(b.atraso.mean()), 4), "ate": DATA_MATURIDADE},
           "padroes": padroes_por_grupo(b), "combinacoes": combinacoes_arvore(b)}
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / "padroes.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return res


if __name__ == "__main__":
    r = calcular(pd.read_pickle(SAIDA / "hist.pkl"))
    for p in r["padroes"] + r["combinacoes"]:
        print("-", p["frase"])
