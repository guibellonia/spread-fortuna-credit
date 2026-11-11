"""Ferramentas determinísticas para o agente LLM (Hermes via OmniRoute/Z.ai, ou qualquer cliente com function calling).

Princípio: o LLM interpreta, investiga e recomenda; TODO número sai destas funções.
Cada tool recebe argumentos simples e devolve um dict serializável em JSON.

Uso:
    from tools import TOOLS, executar
    executar("decidir_pedido", {"id_pedido": "P-00070"})
    python tools.py listar                       # lista as tools
    python tools.py decidir_pedido '{"id_pedido": "P-00070"}'

Guarda-corpos:
    - gerar_csv só grava o arquivo de entrega com confirmar=true (decisão humana). Sem isso, só simula.
    - Nenhuma tool altera os parâmetros padrão da política nem escreve no banco.
    - medir_grupo aceita só campos e operadores de uma lista fechada (sem SQL livre).
"""
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(RAIZ / "validacao"))  # tool_risco (modelo de sobrevivência)

from cenarios import R_ATRASO, m_wrap, pesos_censura, resultado, treinar_corrigido  # noqa: E402
from features import parcela_price  # noqa: E402
from modelo import SAIDA  # noqa: E402
from politica import PARAMS, politica_atual, politica_proposta  # noqa: E402

LIMITE_EQUILIBRIO = 0.175


# ----------------------------------------------------------------------------- estado (carregado uma vez)
def _j(o):
    """Converte tipos numpy/pandas para JSON."""
    if isinstance(o, dict):
        return {str(k): _j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_j(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if (isinstance(o, float) and math.isnan(o)) or np.isnan(o) else round(float(o), 4)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.date().isoformat()
    return o


@lru_cache(maxsize=1)
def _hist():
    p = SAIDA / "hist.pkl"
    if not p.exists():
        raise RuntimeError("rode src/gerar_decisoes.py uma vez para montar saida/hist.pkl e saida/novos.pkl")
    return pd.read_pickle(p)


@lru_cache(maxsize=1)
def _novos():
    return pd.read_pickle(SAIDA / "novos.pkl").reset_index(drop=True)


@lru_cache(maxsize=1)
def _modelo():
    m, meta = treinar_corrigido(_hist())
    return m, meta


def _politica_modelo():
    return m_wrap(_modelo()[0])


@lru_cache(maxsize=1)
def _aprovados_com_peso():
    ap = _hist()[_hist().decisao == "aprovado"].reset_index(drop=True)
    w, ap = pesos_censura(ap)
    ap["w"] = w.values
    ap["inad"] = (ap.situacao_final == "inadimplente").astype(int)
    ap["comp_aprov"] = parcela_price(ap.valor_aprovado, ap.prazo_meses) / ap.renda_declarada
    ap["r_saidas"] = ap.mov_saidas_media / ap.mov_entradas_media.clip(lower=1)
    ap["sobra_mensal"] = ap.mov_entradas_media - ap.mov_saidas_media
    return ap


@lru_cache(maxsize=1)
def _conselho():
    from conselho import Conselho
    return Conselho().treinar(_hist())


@lru_cache(maxsize=1)
def _base_sobrev():
    import tool_risco
    return tool_risco.carregar_pedidos("novo")


def _params(p):
    p = dict(p or {})
    desconhecidos = set(p) - set(PARAMS)
    if desconhecidos:
        raise ValueError(f"parâmetros desconhecidos: {sorted(desconhecidos)}. Válidos: {sorted(PARAMS)}")
    return {**PARAMS, **p}


def _pedido(id_pedido):
    x = _novos()
    r = x[x.id_pedido == id_pedido]
    if r.empty:
        raise ValueError(f"{id_pedido} não está na base de novos pedidos")
    return r


# ----------------------------------------------------------------------------- tools
def politica_vigente() -> dict:
    """Parâmetros da política proposta (cenário G) e a descrição dos passos."""
    p = PARAMS
    passos = []
    if p["min_score"]:
        passos.append(f"nega score até {p['min_score']}")
    passos += [
        f"nega com mais de {p['max_restricoes']} restrição(ões) ativa(s) no bureau",
        f"nega com mais de {p['max_meses_negativos']} mês(es) de saldo negativo nos últimos 12",
        f"parcela limitada a {p['max_comprometimento']:.0%} da renda declarada (reduz o valor)",
        "modelo corrigido para censura estima P(não paga) de vida inteira para valores de 100% a 10% do solicitado",
        f"aprova o valor de maior ganho esperado com P(não paga) <= {p['risco_max']:.1%} e ganho > {p['ganho_min']}",
        "limites do produto: R$ 500 a R$ 30.000, nunca acima do solicitado",
    ]
    return _j({"params": p, "passos": passos, "modelo": _modelo()[1],
               "ganho_por_real": {"em_dia": 0.15, "atraso": 0.05, "nao_paga": -0.60},
               "fracao_pagadores_com_atraso": R_ATRASO, "ponto_equilibrio_p_nao_paga": LIMITE_EQUILIBRIO})


def listar_padroes(min_clientes: int = 40, limite: int = 30) -> dict:
    """Padrões de inadimplência por grupo e combinações da árvore, no formato do manual."""
    import padroes
    r = padroes.calcular(_hist())
    pad = [p for p in r["padroes"] if p["clientes"] >= min_clientes][:limite]
    comb = [p for p in r["combinacoes"] if p["clientes"] >= min_clientes][:limite]
    return _j({"base": r["base"], "padroes": pad, "combinacoes_arvore": comb,
               "aviso": "taxas observadas em contratos com 6+ meses; para taxa corrigida de censura use medir_grupo"})


CAMPOS_GRUPO = {
    "score": "score do bureau", "restricoes_ativas": "restrições ativas", "consultas_90_dias": "consultas ao CPF em 90 dias",
    "meses_historico_bureau": "meses de histórico no bureau", "parcelas_outras_instituicoes": "dívidas em outras instituições (R$/mês)",
    "renda_declarada": "renda declarada", "comp_aprov": "parcela/renda declarada (valor aprovado)",
    "comprometimento_real": "parcela+dívidas / entradas", "entradas_sobre_renda": "entradas na conta / renda declarada",
    "r_saidas": "saídas / entradas", "sobra_mensal": "sobra mensal (R$)", "mov_meses_cheque": "meses com saldo negativo (12m)",
    "mov_dias_cheque_total": "dias de cheque especial (12m)", "mov_saldo_medio": "saldo médio", "mov_entradas_cv": "variação das entradas",
    "prazo_meses": "prazo", "valor_aprovado": "valor aprovado", "meses_conta": "meses de conta", "idade": "idade",
    "tipo_vinculo": "vínculo", "politica_aplicada": "política que aprovou (atual/piloto)",
}
OPS = {"<": np.less, "<=": np.less_equal, ">": np.greater, ">=": np.greater_equal, "==": np.equal, "!=": np.not_equal}


def medir_grupo(condicoes: list) -> dict:
    """Inadimplência projetada (corrigida de censura) de um grupo do histórico de aprovados.

    condicoes: lista de {"campo": ..., "op": "<|<=|>|>=|==|!=|in", "valor": ...}, combinadas com E.
    """
    ap = _aprovados_com_peso()
    m = np.ones(len(ap), bool)
    desc = []
    for c in condicoes:
        campo, op, val = c["campo"], c["op"], c["valor"]
        if campo not in CAMPOS_GRUPO:
            raise ValueError(f"campo '{campo}' não permitido. Use: {sorted(CAMPOS_GRUPO)}")
        if op == "in":
            m &= ap[campo].isin(val).to_numpy()
        elif op in OPS:
            m &= OPS[op](ap[campo].to_numpy(), val)
        else:
            raise ValueError(f"operador '{op}' inválido")
        desc.append(f"{CAMPOS_GRUPO[campo]} {op} {val}")
    g = ap[m]
    media = ap.inad.sum() / ap.w.sum()
    d, e = int(g.inad.sum()), float(g.w.sum())
    if e <= 0:
        return {"grupo": " e ".join(desc), "clientes": int(len(g)), "erro": "sem exposição suficiente"}
    taxa = d / e
    # IC 95% aproximado (Poisson, Wilson-Hilferty)
    lo = 0.0 if d == 0 else d * (1 - 1 / (9 * d) - 1.96 / (3 * math.sqrt(d))) ** 3 / e
    hi = (d + 1) * (1 - 1 / (9 * (d + 1)) + 1.96 / (3 * math.sqrt(d + 1))) ** 3 / e
    return _j({
        "grupo": " e ".join(desc), "clientes": len(g), "paradas": d, "exposicao": round(e, 1),
        "inadimplencia_projetada": taxa, "ic95": [lo, hi], "media": media, "risco_relativo": taxa / media,
        "acima_do_equilibrio": taxa > LIMITE_EQUILIBRIO,
        "frase": f"Clientes com {' e '.join(desc)} têm inadimplência projetada de {taxa:.0%}, contra {media:.0%} da média. Afeta {len(g)} clientes.",
        "aviso": "amostra pequena: IC largo" if d < 20 else None,
    })


def consultar_pedido(id_pedido: str) -> dict:
    """Dados de um pedido novo: pedido, cadastro, bureau e resumo da movimentação."""
    r = _pedido(id_pedido).iloc[0]
    campos = ["id_pedido", "id_cliente", "data_pedido", "valor_solicitado", "prazo_meses", "renda_declarada", "profissao",
              "tipo_vinculo", "idade", "meses_conta", "score", "restricoes_ativas", "parcelas_outras_instituicoes",
              "consultas_90_dias", "meses_historico_bureau", "mov_meses", "mov_entradas_media", "mov_salario_media",
              "mov_saidas_media", "mov_saldo_medio", "mov_saldo_minimo_min", "mov_meses_cheque", "mov_dias_cheque_total",
              "parcela_solicitada", "comprometimento", "comprometimento_real", "entradas_sobre_renda", "sobra_mensal"]
    return _j({c: r[c] for c in campos})


def decidir_pedido(id_pedido: str, params: dict | None = None) -> dict:
    """Decisão da política proposta (padrão = cenário G) para um pedido, com motivo e probabilidades,
    e a decisão que a política atual da Fortuna daria."""
    x = _pedido(id_pedido)
    d = politica_proposta(x, _politica_modelo(), _params(params)).iloc[0]
    a = politica_atual(x).iloc[0]
    return _j({"id_pedido": id_pedido, "decisao": "APROVADO" if d.aprova else "NEGADO", "valor_aprovado": d.valor,
               "valor_solicitado": x.valor_solicitado.iloc[0], "motivo": d.motivo,
               "p_em_dia": d.p_em_dia, "p_atraso": d.p_atraso, "p_nao_paga": d.p_nao_paga,
               "ganho_esperado_rs": d.ganho_esperado,
               "politica_atual": {"decisao": "APROVADO" if a.aprova else "NEGADO", "valor": a.valor}})


def avaliar_pedido(id_pedido: str, valor: float) -> dict:
    """Conselho de 4 modelos para um pedido e valor: opinião de cada um, mediana, divergência e veredito,
    mais os 5 fatores que mais pesam (modelo de sobrevivência)."""
    import tool_risco
    x = _pedido(id_pedido)
    op = _conselho().opinar(x, [valor], _base_sobrev()).iloc[0]
    try:
        fatores = tool_risco.prever_risco(id_pedido, valor).get("fatores")
    except Exception as e:  # modelo salvo ausente
        fatores = f"indisponível: {e}"
    return _j({"id_pedido": id_pedido, "valor": valor,
               "opinioes_p_nao_paga": {k: op[k] for k in ["gbm_corrigido", "sobrevivencia", "logistico", "tabela"]},
               "p_mediana": op.p_mediana, "divergencia_pp": op.divergencia_pp, "veredito": op.veredito,
               "votos_contra": op.votos_contra, "limite": LIMITE_EQUILIBRIO, "fatores": fatores})


def simular_politica(params: dict | None = None, nome: str = "proposta") -> dict:
    """Resultado esperado de longo prazo nos 2.000 novos (base, pessimista +20% risco, otimista -20%) vs política atual."""
    x = _novos()
    m = _modelo()[0]
    dec = politica_proposta(x, _politica_modelo(), _params(params))
    atual = politica_atual(x)
    base, ref = resultado(dec, x, m), resultado(atual, x, m)
    mot = dec.motivo.value_counts().to_dict()
    return _j({"nome": nome, "params": _params(params), **base,
               "pessimista": resultado(dec, x, m, 1.2)["resultado"], "otimista": resultado(dec, x, m, 0.8)["resultado"],
               "politica_atual": ref, "ganho_vs_atual": base["resultado"] - ref["resultado"],
               "difere_da_atual": int((dec.aprova.values != atual.aprova.values).sum()), "motivos": mot})


def comparar_politicas(politicas: list) -> dict:
    """Compara várias configurações. politicas: lista de {"nome": ..., "params": {...}}."""
    linhas = [simular_politica(p.get("params"), p.get("nome", f"p{i}")) for i, p in enumerate(politicas)]
    cols = ["nome", "aprovados", "volume", "inad_esperada", "resultado", "pessimista", "otimista", "ganho_vs_atual"]
    return _j({"comparacao": [{c: l[c] for c in cols} for l in linhas],
               "melhor": max(linhas, key=lambda l: l["resultado"])["nome"],
               "aviso": "decisão e avaliação usam o mesmo modelo: ganhos tendem a ser otimistas; compare o cenário pessimista"})


def backtest_politica(params: dict | None = None) -> dict:
    """Teste fora da amostra com desfecho observado (treino até set/25, teste out/25-mar/26)."""
    import backtest
    a, p = backtest.rodar(_params(params), verbose=False)
    return _j({"politica_atual": a, "proposta": p, "ganho": p["resultado"] - a["resultado"],
               "aviso": "usa o modelo original de 3 classes e desfecho observado até o corte; aprovações sem desfecho contam zero"})


def pedidos_em_divergencia(limite: int = 20, params: dict | None = None) -> dict:
    """Fila para o analista: pedidos em que o conselho de modelos discorda, no valor que a política propõe."""
    x = _novos()
    dec = politica_proposta(x, _politica_modelo(), _params(params))
    valor = np.where(dec.valor > 0, dec.valor, np.minimum(x.valor_solicitado, 30000))
    op = _conselho().opinar(x, valor, _base_sobrev())
    op["decisao_politica"] = np.where(dec.aprova, "APROVADO", "NEGADO")
    op["motivo"] = dec.motivo.values
    div = op[op.veredito == "divergência"].sort_values("divergencia_pp", ascending=False)
    cols = ["id_pedido", "valor", "decisao_politica", "motivo", "gbm_corrigido", "sobrevivencia", "logistico",
            "tabela", "p_mediana", "divergencia_pp", "votos_contra"]
    return _j({"resumo": op.veredito.value_counts().to_dict(),
               "aprovados_pela_politica_em_divergencia": int(((op.veredito == "divergência") & dec.aprova.values).sum()),
               "pedidos": div[cols].head(limite).to_dict("records")})


def gerar_csv(params: dict | None = None, confirmar: bool = False) -> dict:
    """Gera o arquivo de decisões. Sem confirmar=true só simula (dry-run). Com confirmar=true grava
    saida/spread_final.csv (substitui o anterior, guardando cópia) e valida. Exige aprovação humana."""
    import shutil
    import validar_csv as vc
    x = _novos()
    dec = politica_proposta(x, _politica_modelo(), _params(params))
    resumo = {"aprovados": int(dec.aprova.sum()), "negados": int((~dec.aprova).sum()),
              "valor_total": round(float(dec.valor.sum()), 2), "params": _params(params)}
    if not confirmar:
        return _j({"dry_run": True, **resumo, "aviso": "nada gravado; repita com confirmar=true após aprovação do analista"})
    out = pd.DataFrame({"id_pedido": dec.id_pedido, "decisao": np.where(dec.aprova, "APROVADO", "NEGADO"),
                        "valor_aprovado": [f"{v:.2f}" for v in dec.valor]})
    destino = SAIDA / "spread_final.csv"
    if destino.exists():
        shutil.copy(destino, SAIDA / "spread_final_anterior.csv")
    with open(destino, "w", encoding="utf-8", newline="") as f:
        out.to_csv(f, index=False, lineterminator="\n")
    erros, avisos, rel = vc.validar(destino)
    return _j({"gravado": str(destino), **resumo, "valido": not erros, "erros": erros[:10], "composicao": rel})


def validar_arquivo(caminho: str = "") -> dict:
    """Valida um CSV de decisões nas regras do manual (padrão: saida/spread_final.csv)."""
    import validar_csv as vc
    erros, avisos, rel = vc.validar(caminho or SAIDA / "spread_final.csv")
    return _j({"valido": not erros, "erros": erros[:20], "avisos": avisos, "composicao": rel})


# ----------------------------------------------------------------------------- schemas (function calling)
_PARAMS_SCHEMA = {"type": "object", "description": "Sobrescreve parâmetros da política. Omitido = cenário G.",
                  "properties": {
                      "min_score": {"type": "number", "description": "nega score <= este valor (0 = sem corte)"},
                      "max_restricoes": {"type": "integer"}, "max_meses_negativos": {"type": "integer"},
                      "max_comprometimento": {"type": "number", "description": "teto parcela/renda, ex. 0.20"},
                      "risco_max": {"type": "number", "description": "P(não paga) máxima, ex. 0.175"},
                      "ganho_min": {"type": "number"}}}


def _f(nome, desc, props=None, req=None):
    return {"type": "function", "function": {"name": nome, "description": desc,
            "parameters": {"type": "object", "properties": props or {}, "required": req or []}}}


TOOLS = [
    _f("politica_vigente", "Mostra os parâmetros e os passos da política proposta (cenário G)."),
    _f("listar_padroes", "Lista padrões de inadimplência já calculados (grupos e combinações da árvore).",
       {"min_clientes": {"type": "integer"}, "limite": {"type": "integer"}}),
    _f("medir_grupo", "Mede a inadimplência projetada (corrigida de censura) de um grupo do histórico. Use para testar hipóteses.",
       {"condicoes": {"type": "array", "items": {"type": "object", "properties": {
           "campo": {"type": "string", "enum": sorted(CAMPOS_GRUPO)},
           "op": {"type": "string", "enum": ["<", "<=", ">", ">=", "==", "!=", "in"]},
           "valor": {}}, "required": ["campo", "op", "valor"]}}}, ["condicoes"]),
    _f("consultar_pedido", "Dados de um pedido novo (cadastro, bureau, movimentação).",
       {"id_pedido": {"type": "string"}}, ["id_pedido"]),
    _f("decidir_pedido", "Decisão da política para um pedido novo, com motivo, probabilidades e a decisão da política atual.",
       {"id_pedido": {"type": "string"}, "params": _PARAMS_SCHEMA}, ["id_pedido"]),
    _f("avaliar_pedido", "Conselho de 4 modelos para um pedido e valor: opiniões, divergência, veredito e fatores.",
       {"id_pedido": {"type": "string"}, "valor": {"type": "number"}}, ["id_pedido", "valor"]),
    _f("simular_politica", "Resultado esperado de longo prazo de uma configuração nos 2.000 pedidos novos, vs política atual.",
       {"params": _PARAMS_SCHEMA, "nome": {"type": "string"}}),
    _f("comparar_politicas", "Compara várias configurações de política lado a lado.",
       {"politicas": {"type": "array", "items": {"type": "object", "properties": {
           "nome": {"type": "string"}, "params": _PARAMS_SCHEMA}}}}, ["politicas"]),
    _f("backtest_politica", "Teste fora da amostra com desfecho observado (out/25 a mar/26).", {"params": _PARAMS_SCHEMA}),
    _f("pedidos_em_divergencia", "Fila de pedidos em que os modelos discordam, para revisão do analista.",
       {"limite": {"type": "integer"}, "params": _PARAMS_SCHEMA}),
    _f("gerar_csv", "Gera o CSV de entrega. Só grava com confirmar=true, e só depois de aprovação explícita do analista humano.",
       {"params": _PARAMS_SCHEMA, "confirmar": {"type": "boolean"}}),
    _f("validar_arquivo", "Valida um CSV de decisões nas regras do manual.", {"caminho": {"type": "string"}}),
]

_FUNCS = {t["function"]["name"]: globals()[t["function"]["name"]] for t in TOOLS}


def executar(nome: str, argumentos: dict | str | None = None) -> dict:
    """Despachante: chamado pelo loop do agente com o nome da tool e os argumentos (dict ou JSON)."""
    if nome not in _FUNCS:
        return {"erro": f"tool '{nome}' não existe", "tools": sorted(_FUNCS)}
    args = json.loads(argumentos) if isinstance(argumentos, str) else (argumentos or {})
    try:
        return _FUNCS[nome](**args)
    except Exception as e:  # o agente recebe o erro e pode corrigir a chamada
        return {"erro": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "listar":
        for t in TOOLS:
            print(f"- {t['function']['name']}: {t['function']['description']}")
    elif sys.argv[1] == "schemas":
        print(json.dumps(TOOLS, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(executar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), ensure_ascii=False, indent=2))
