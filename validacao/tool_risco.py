"""Ferramenta de risco de crédito (validação independente) - Desafio Fortuna Crédito.

Modelo de sobrevivência em tempo discreto (hazard por parcela) que corrige a censura
da data de corte. Para um pedido e um VALOR candidato estima, para a vida inteira do
contrato:
    p_em_dia, p_atraso, p_nao_paga  e o ganho esperado (R$) pela regra do hackathon
    (+15% em dia, +5% atraso, -60% não paga).

Funções públicas (entradas/saídas JSON-serializáveis, sem estado global oculto;
o modelo é lido do disco a cada chamada, com cache explícito opcional pelo argumento
`modelo`):
    treinar(caminho=MODELO_PADRAO, corte="2026-09-30", ate_data_pedido=None) -> dict
    prever_risco(id_pedido, valor, caminho=MODELO_PADRAO, fator_risco=1.0) -> dict
    melhor_valor(id_pedido, caminho=MODELO_PADRAO, pd_max=None, renda_max=0.20,
                 fator_risco=1.0) -> dict

Método de censura: cada parcela vencida é uma "observação" no tempo k (nº da parcela).
Uma parcela só entra no conjunto de risco se o seu desfecho já é conhecido na data de corte
(paga, ou vencida há >= DIAS_DETERMINACAO dias). Ajusta-se:
  h_d(k) = P(parcela k vira inadimplência | nenhuma inadimplência antes)
  h_a(k) = P(parcela k tem qualquer atraso/inadimplência | todas as anteriores em dia)
e projeta-se a vida inteira do contrato (k = 1..prazo):
  P(não paga) = 1 - prod(1 - h_d(k));  P(em dia) = prod(1 - h_a(k));
  P(atraso)   = max(0, 1 - P(não paga) - P(em dia)).
"""
from __future__ import annotations

import json
import os
from datetime import date

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO_PADRAO = os.path.join(AQUI, "modelo_risco.joblib")
BUREAU_CACHE = os.path.join(os.path.dirname(AQUI), "saida", "bureau_cache.json")
TAXA = 0.03
GANHO = {"em_dia": 0.15, "atraso": 0.05, "nao_paga": -0.60}
# Na base, nenhuma parcela foi paga com mais de 60 dias de atraso: parcela vencida e não
# paga há 61+ dias nunca volta a ser paga (estado absorvente), logo já é inadimplência.
DIAS_DETERMINACAO = 61

FEATS = [
    "score", "restricoes_ativas", "outras_renda", "consultas_90_dias", "meses_historico_bureau",
    "renda", "idade", "meses_conta", "vinc_assal", "vinc_auto", "vinc_empr", "vinc_apos",
    "mov_meses", "meses_saldo_neg", "dias_cheque", "entradas_renda", "salario_share",
    "saidas_entradas", "saldo_medio_renda", "cv_entradas", "meses_sem_salario",
    "prazo", "valor_renda", "parcela_renda", "comprometimento", "k", "k_frac",
]
# risco não pode cair quando o valor/parcela sobe
MONO = {"parcela_renda": 1, "comprometimento": 1, "valor_renda": 1}


# ----------------------------------------------------------------------------- utilidades
def parcela_price(valor: float, prazo: int) -> float:
    """Parcela pela tabela Price a 3% a.m., arredondada a 2 casas."""
    return round(valor * TAXA / (1 - (1 + TAXA) ** (-prazo)), 2)


def valor_max_por_parcela(parcela_max: float, prazo: int) -> float:
    """Maior valor cuja parcela Price cabe em `parcela_max`."""
    return parcela_max * (1 - (1 + TAXA) ** (-prazo)) / TAXA


def _q(sql: str) -> pd.DataFrame:
    import sys
    sys.path.insert(0, AQUI)
    from db import q
    return q(sql)


# ----------------------------------------------------------------------------- features
def carregar_pedidos(tipo_base: str | None = None) -> pd.DataFrame:
    """Uma linha por pedido com variáveis de cliente, bureau e movimentação (sem valor)."""
    filtro = f"where p.tipo_base = '{tipo_base}'" if tipo_base else ""
    df = _q(f"""
        select p.*, c.renda_declarada, c.tipo_vinculo, c.data_abertura_conta, c.data_nascimento,
               b.score, b.restricoes_ativas, b.parcelas_outras_instituicoes,
               b.consultas_90_dias, b.meses_historico_bureau
        from hackathon.pedidos p join hackathon.clientes c using(id_cliente)
        left join hackathon.bureau b using(id_pedido) {filtro}""")
    # bureau dos novos vem do cache da API
    if os.path.exists(BUREAU_CACHE):
        cache = json.load(open(BUREAU_CACHE, encoding="utf-8"))
        novo = df["tipo_base"] == "novo"
        for col in ["score", "restricoes_ativas", "parcelas_outras_instituicoes",
                    "consultas_90_dias", "meses_historico_bureau"]:
            df[col] = df[col].astype(float)
        for col in ["score", "restricoes_ativas", "parcelas_outras_instituicoes",
                    "consultas_90_dias", "meses_historico_bureau"]:
            df.loc[novo, col] = df.loc[novo, "id_cliente"].map(
                lambda c: cache.get(c, {}).get(col, np.nan)).astype(float)
    mov = _q("select * from hackathon.movimentacao_mensal")
    for c in ["total_entradas", "entradas_salario", "total_saidas", "saldo_medio", "saldo_minimo"]:
        mov[c] = mov[c].astype(float)
    g = mov.groupby("id_cliente")
    m = pd.DataFrame({
        "mov_meses": g.size(),
        "meses_saldo_neg": g["saldo_minimo"].apply(lambda s: int((s < 0).sum())),
        "dias_cheque": g["dias_cheque_especial"].sum(),
        "ent_media": g["total_entradas"].mean(),
        "sal_media": g["entradas_salario"].mean(),
        "sai_media": g["total_saidas"].mean(),
        "saldo_medio": g["saldo_medio"].mean(),
        "cv_entradas": g["total_entradas"].std() / g["total_entradas"].mean().replace(0, np.nan),
        "meses_sem_salario": g["entradas_salario"].apply(lambda s: int((s <= 0).sum())),
    }).reset_index()
    df = df.merge(m, on="id_cliente", how="left")
    num = ["renda_declarada", "valor_solicitado", "valor_aprovado", "parcelas_outras_instituicoes"]
    for c in num:
        df[c] = df[c].astype(float)
    dp = pd.to_datetime(df["data_pedido"])
    df["renda"] = df["renda_declarada"]
    df["idade"] = (dp - pd.to_datetime(df["data_nascimento"])).dt.days / 365.25
    df["meses_conta"] = (dp - pd.to_datetime(df["data_abertura_conta"])).dt.days / 30.44
    for v, n in [("assalariado", "assal"), ("autonomo", "auto"), ("empresario", "empr"),
                 ("aposentado", "apos")]:
        df[f"vinc_{n}"] = (df["tipo_vinculo"] == v).astype(int)
    r = df["renda"].replace(0, np.nan)
    df["outras_renda"] = df["parcelas_outras_instituicoes"] / r
    df["entradas_renda"] = df["ent_media"] / r
    df["salario_share"] = df["sal_media"] / df["ent_media"].replace(0, np.nan)
    df["saidas_entradas"] = df["sai_media"] / df["ent_media"].replace(0, np.nan)
    df["saldo_medio_renda"] = df["saldo_medio"] / r
    df["prazo"] = df["prazo_meses"].astype(int)
    for c in ["mov_meses", "meses_saldo_neg", "dias_cheque", "meses_sem_salario"]:
        df[c] = df[c].fillna(0)
    return df


def com_valor(df: pd.DataFrame, valor) -> pd.DataFrame:
    """Acrescenta as variáveis que dependem do valor do contrato."""
    d = df.copy()
    d["valor"] = np.asarray(valor, dtype=float) if np.ndim(valor) else float(valor)
    fat = TAXA / (1 - (1 + TAXA) ** (-d["prazo"].astype(float)))
    d["parcela"] = d["valor"] * fat
    d["valor_renda"] = d["valor"] / d["renda"]
    d["parcela_renda"] = d["parcela"] / d["renda"]
    d["comprometimento"] = (d["parcela"] + d["parcelas_outras_instituicoes"]) / d["renda"]
    return d


def painel_parcelas(corte: str = "2026-09-30", ate_data_pedido: str | None = None):
    """Base pessoa-período (parcela) com desfecho conhecido até `corte`.

    Permite simular um corte anterior (validação do método de censura): pagamentos
    posteriores ao corte simulado são apagados e os atrasos recalculados.
    """
    corte_d = pd.Timestamp(corte)
    par = _q("""select pa.id_pedido, pa.numero_parcela k, pa.data_vencimento, pa.data_pagamento,
                       pa.dias_atraso from hackathon.parcelas pa""")
    par["data_vencimento"] = pd.to_datetime(par["data_vencimento"])
    par["data_pagamento"] = pd.to_datetime(par["data_pagamento"])
    ped = carregar_pedidos("historico")
    ped = ped[ped["decisao"] == "aprovado"]
    ped = ped[pd.to_datetime(ped["data_pedido"]) <= corte_d]
    if ate_data_pedido:
        ped = ped[pd.to_datetime(ped["data_pedido"]) <= pd.Timestamp(ate_data_pedido)]
    par = par[par["id_pedido"].isin(ped["id_pedido"])].copy()
    paga = par["data_pagamento"].notna() & (par["data_pagamento"] <= corte_d)
    atraso_pago = (par["data_pagamento"] - par["data_vencimento"]).dt.days.clip(lower=0)
    dias_venc = (corte_d - par["data_vencimento"]).dt.days
    par["status"] = np.where(paga, np.where(atraso_pago > 0, "atraso", "em_dia"),
                     np.where(dias_venc >= DIAS_DETERMINACAO, "inad", "aberta"))
    # parcela "aberta" (sem desfecho conhecido) mas já vencida e não paga = atraso certo
    par["atraso_certo"] = (~paga) & (dias_venc > 0)
    par = par.sort_values(["id_pedido", "k"])
    linhas_d, linhas_a = [], []
    for pid, g in par.groupby("id_pedido", sort=False):
        st = g["status"].values
        ac = g["atraso_certo"].values
        ks = g["k"].values
        limpo = True
        for i in range(len(g)):
            s = st[i]
            if s == "aberta":
                # risco "qualquer atraso": conhecido se já está atrasada
                if limpo and ac[i]:
                    linhas_a.append((pid, ks[i], 1))
                break
            linhas_d.append((pid, ks[i], int(s == "inad")))
            if limpo:
                ev = int(s != "em_dia")
                linhas_a.append((pid, ks[i], ev))
                limpo = not ev
            if s == "inad":
                break
    d = pd.DataFrame(linhas_d, columns=["id_pedido", "k", "y"])
    a = pd.DataFrame(linhas_a, columns=["id_pedido", "k", "y"])
    base = com_valor(ped.set_index("id_pedido"), ped.set_index("id_pedido")["valor_aprovado"].values)
    base = base.reset_index()
    return d.merge(base, on="id_pedido"), a.merge(base, on="id_pedido"), ped, par


def _X(d: pd.DataFrame) -> np.ndarray:
    d = d.copy()
    d["k_frac"] = d["k"] / d["prazo"]
    return d[FEATS].astype(float).values


def _modelo_hazard(d: pd.DataFrame, seed: int = 0) -> HistGradientBoostingClassifier:
    mono = [MONO.get(f, 0) for f in FEATS]
    m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.04, max_leaf_nodes=15,
                                       min_samples_leaf=80, l2_regularization=1.0,
                                       monotonic_cst=mono, random_state=seed)
    m.fit(_X(d), d["y"].values)
    return m


def treinar(caminho: str = MODELO_PADRAO, corte: str = "2026-09-30",
            ate_data_pedido: str | None = None) -> dict:
    """Treina os dois modelos de hazard com dados conhecidos até `corte` e salva em `caminho`.

    `ate_data_pedido` restringe os contratos de treino (para validação fora do tempo).
    Retorna um resumo JSON-serializável.
    """
    d, a, ped, _ = painel_parcelas(corte, ate_data_pedido)
    md, ma = _modelo_hazard(d), _modelo_hazard(a)
    calib = _recalibracao(d, a, ped)
    ref_cols = ["score", "restricoes_ativas", "outras_renda", "consultas_90_dias",
                "meses_historico_bureau", "renda", "meses_saldo_neg", "dias_cheque",
                "entradas_renda", "saldo_medio_renda", "salario_share", "meses_conta", "idade"]
    referencia = {c: float(ped[c].median()) for c in ref_cols}
    joblib.dump({"hazard_inad": md, "hazard_atraso": ma, "feats": FEATS, "corte": corte,
                 "ate_data_pedido": ate_data_pedido, "referencia": referencia,
                 "calibracao": calib}, caminho)
    return {"caminho": caminho, "contratos": int(len(ped)), "linhas_inad": int(len(d)),
            "eventos_inad": int(d["y"].sum()), "linhas_atraso": int(len(a)),
            "eventos_atraso": int(a["y"].sum())}


def km_estratificado(painel: pd.DataFrame, K: int | None = None) -> float:
    """Kaplan-Meier (tempo = nº da parcela) da probabilidade acumulada do evento, estratificado
    por prazo (contrato que termina sem evento não é censura) até min(prazo, K), ponderado
    pelo nº de contratos de cada prazo."""
    if painel.empty:
        return float("nan")
    K = K or int(painel["k"].max())
    tot, w = 0.0, 0
    for p, g in painel.groupby("prazo"):
        kk = min(int(p), K)
        h = g.groupby("k")["y"].agg(["sum", "size"]).reindex(range(1, kk + 1)).fillna(0)
        haz = np.where(h["size"] > 0, h["sum"] / h["size"].replace(0, 1), 0)
        n = g["id_pedido"].nunique()
        tot += n * (1 - np.prod(1 - haz)); w += n
    return float(tot / w)


def _recalibracao(d, a, ped, folds: int = 5, bins: int = 20) -> dict:
    """Recalibração de vida inteira com correção de censura: previsões fora da dobra
    (cross-fit) agrupadas em `bins` faixas; em cada faixa o alvo é o Kaplan-Meier
    estratificado; ajusta-se uma função monótona (isotônica) previsto -> KM."""
    from sklearn.isotonic import IsotonicRegression
    ids = ped["id_pedido"].values
    rng = np.random.default_rng(0)
    fold = dict(zip(ids, rng.integers(0, folds, len(ids))))
    oof = []
    for f in range(folds):
        tr = [i for i in ids if fold[i] != f]
        te = ped[ped["id_pedido"].map(fold) == f]
        m = {"hazard_inad": _modelo_hazard(d[d["id_pedido"].isin(tr)]),
             "hazard_atraso": _modelo_hazard(a[a["id_pedido"].isin(tr)])}
        p = prever_df(te, te["valor_aprovado"].values, m, calibrar=False)
        oof.append(pd.DataFrame({"id_pedido": te["id_pedido"].values, "pd": p["p_nao_paga"].values,
                                 "pa": 1 - p["p_em_dia"].values}))
    oof = pd.concat(oof)
    out = {}
    for col, painel in (("pd", d), ("pa", a)):
        oof["b"] = pd.qcut(oof[col].rank(method="first"), bins, labels=False)
        x, y, w = [], [], []
        for _, g in oof.groupby("b"):
            x.append(g[col].mean()); w.append(len(g))
            y.append(km_estratificado(painel[painel["id_pedido"].isin(g["id_pedido"])]))
        iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(x, y, sample_weight=w)
        out[col] = {"x": [float(v) for v in x], "y_km": [float(v) for v in y],
                    "x_iso": [float(v) for v in iso.X_thresholds_], "y_iso": [float(v) for v in iso.y_thresholds_]}
    return out


def carregar_modelo(caminho: str = MODELO_PADRAO) -> dict:
    return joblib.load(caminho)


# ----------------------------------------------------------------------------- predição
def prever_df(base: pd.DataFrame, valores, modelo: dict, fator_risco: float = 1.0,
              ate_k=None, calibrar: bool = True) -> pd.DataFrame:
    """Vetorizado: para cada linha de `base` (pedidos) e valor, devolve P's de vida inteira.

    `ate_k` (array opcional) limita o horizonte (nº de parcelas) - usado na validação.
    `fator_risco` multiplica P(não paga) (cenários), retirando a diferença de P(em dia).
    """
    b = com_valor(base.reset_index(drop=True), valores)
    n = len(b)
    prazo = b["prazo"].values.astype(int)
    hor = prazo if ate_k is None else np.minimum(prazo, np.asarray(ate_k, dtype=int))
    K = int(hor.max()) if n else 0
    rep = b.loc[b.index.repeat(K)].copy()
    rep["k"] = np.tile(np.arange(1, K + 1), n)
    X = _X(rep)
    hd = modelo["hazard_inad"].predict_proba(X)[:, 1].reshape(n, K)
    ha = modelo["hazard_atraso"].predict_proba(X)[:, 1].reshape(n, K)
    mask = np.arange(1, K + 1)[None, :] <= hor[:, None]
    hd = np.where(mask, hd, 0.0)
    ha = np.where(mask, ha, 0.0)
    p_d = 1 - np.prod(1 - hd, axis=1)
    p_ok = np.prod(1 - ha, axis=1)
    cal = modelo.get("calibracao")
    if calibrar and cal and ate_k is None:   # recalibração só vale para a vida inteira
        p_d = np.interp(p_d, cal["pd"]["x_iso"], cal["pd"]["y_iso"])
        p_ok = 1 - np.interp(1 - p_ok, cal["pa"]["x_iso"], cal["pa"]["y_iso"])
    p_d = np.clip(p_d * fator_risco, 0, 1)
    p_ok = np.minimum(p_ok, 1 - p_d)
    p_l = np.clip(1 - p_d - p_ok, 0, 1)
    v = b["valor"].values
    eg = v * (GANHO["em_dia"] * p_ok + GANHO["atraso"] * p_l + GANHO["nao_paga"] * p_d)
    return pd.DataFrame({"p_em_dia": p_ok, "p_atraso": p_l, "p_nao_paga": p_d,
                         "ganho_esperado": eg, "valor": v,
                         "parcela_renda": b["parcela_renda"].values})


def _pedido(id_pedido: str) -> pd.DataFrame:
    df = carregar_pedidos()
    r = df[df["id_pedido"] == id_pedido]
    if r.empty:
        raise ValueError(f"pedido {id_pedido} não encontrado")
    return r


def _fatores(base: pd.DataFrame, valor: float, modelo: dict) -> list:
    """Principais fatores: efeito de trocar cada variável pela mediana de referência."""
    ref = modelo.get("referencia")
    if ref is None:
        return []
    p0 = prever_df(base, [valor], modelo)["p_nao_paga"].iloc[0]
    out = []
    for f, med in ref.items():
        b2 = base.copy()
        if f in ("valor",):
            continue
        b2[f] = med
        p1 = prever_df(b2, [valor], modelo)["p_nao_paga"].iloc[0]
        out.append({"variavel": f, "valor_cliente": float(base[f].iloc[0]),
                    "mediana_aprovados": float(med), "efeito_pp_p_nao_paga": round(100 * (p0 - p1), 2)})
    out.sort(key=lambda x: -abs(x["efeito_pp_p_nao_paga"]))
    return out[:5]


def prever_risco(id_pedido: str, valor: float, caminho: str = MODELO_PADRAO,
                 fator_risco: float = 1.0) -> dict:
    """Risco de vida inteira do contrato para `id_pedido` aprovado com `valor` (R$).

    Retorna dict com p_em_dia, p_atraso, p_nao_paga, ganho_esperado (R$), parcela,
    parcela_renda e os 5 principais fatores (efeito em pontos percentuais de P(não paga)
    ao trocar a variável pela mediana dos aprovados históricos).
    """
    modelo = carregar_modelo(caminho)
    base = _pedido(id_pedido)
    r = prever_df(base, [float(valor)], modelo, fator_risco).iloc[0]
    prazo = int(base["prazo"].iloc[0])
    return {"id_pedido": id_pedido, "valor": round(float(valor), 2), "prazo": prazo,
            "parcela": parcela_price(float(valor), prazo),
            "parcela_renda": round(float(r["parcela_renda"]), 4),
            "p_em_dia": round(float(r["p_em_dia"]), 4), "p_atraso": round(float(r["p_atraso"]), 4),
            "p_nao_paga": round(float(r["p_nao_paga"]), 4),
            "ganho_esperado": round(float(r["ganho_esperado"]), 2),
            "fatores": _fatores(base, float(valor), modelo)}


def candidatos_valor(solicitado: float, renda: float, prazo: int, renda_max: float = 0.20):
    """Valores de 100% a 10% do solicitado (múltiplos de R$100 + o próprio solicitado),
    limitados a R$30.000, mínimo R$500 e parcela <= renda_max * renda."""
    teto = min(solicitado, 30000.0)
    vmax = valor_max_por_parcela(renda_max * renda, prazo) if renda_max else teto
    cands = set(np.arange(np.ceil(0.1 * solicitado / 100) * 100, teto + 1e-9, 100.0).tolist())
    cands.add(teto)
    out = [round(c, 2) for c in cands
           if 500 <= c <= teto and (renda_max is None or parcela_price(c, prazo) <= renda_max * renda)]
    return sorted(out)


def melhor_valor(id_pedido: str, caminho: str = MODELO_PADRAO, pd_max: float | None = 0.20,
                 renda_max: float | None = 0.20, fator_risco: float = 1.0) -> dict:
    """Escolhe o valor de maior ganho esperado entre os candidatos (ver candidatos_valor),
    exigindo P(não paga) <= pd_max. Se nenhum candidato tem ganho > 0, recomenda NEGAR."""
    modelo = carregar_modelo(caminho)
    base = _pedido(id_pedido)
    s, r, n = (float(base["valor_solicitado"].iloc[0]), float(base["renda"].iloc[0]),
               int(base["prazo"].iloc[0]))
    c = candidatos_valor(s, r, n, renda_max)
    if not c:
        return {"id_pedido": id_pedido, "decisao": "NEGADO", "valor_aprovado": 0.0,
                "motivo": "nenhum valor >= R$500 cabe no limite de parcela"}
    p = prever_df(pd.concat([base] * len(c)), c, modelo, fator_risco)
    ok = p[(p["ganho_esperado"] > 0) & ((pd_max is None) | (p["p_nao_paga"] <= (pd_max or 1)))]
    if ok.empty:
        return {"id_pedido": id_pedido, "decisao": "NEGADO", "valor_aprovado": 0.0,
                "motivo": "nenhum valor com ganho esperado positivo dentro do limite de risco",
                "menor_p_nao_paga": round(float(p["p_nao_paga"].min()), 4)}
    b = ok.loc[ok["ganho_esperado"].idxmax()]
    return {"id_pedido": id_pedido, "decisao": "APROVADO", "valor_aprovado": round(float(b["valor"]), 2),
            "valor_solicitado": s, "p_em_dia": round(float(b["p_em_dia"]), 4),
            "p_atraso": round(float(b["p_atraso"]), 4), "p_nao_paga": round(float(b["p_nao_paga"]), 4),
            "ganho_esperado": round(float(b["ganho_esperado"]), 2)}


if __name__ == "__main__":
    print(json.dumps(treinar(), indent=2))
