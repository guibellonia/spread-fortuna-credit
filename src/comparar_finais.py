"""Compara as políticas candidatas à entrega com avaliadores independentes.

Políticas: atual (Fortuna) | regras (Bilosca, src/politica_regras.py) | G (modelo, src/politica.py) |
           G + filtros do Bilosca (híbrida)
Avaliadores nos 2.000 novos (resultado esperado de longo prazo, R$):
    1. GBM corrigido de censura (o mesmo que decide o G: tende a favorecer o G)
    2. modelo de sobrevivência do agente independente (validacao/tool_risco.py)
    3. regressão logística do conselho (validador explicável)
Teste fora da amostra com desfecho observado: pedidos de out/25 a mar/26; o G usa um modelo treinado só até set/25.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.append(str(RAIZ / "validacao"))  # no fim: o db.py de src/ tem precedência

from cenarios import m_wrap, treinar_corrigido  # noqa: E402
from conselho import Conselho  # noqa: E402
from db import consulta  # noqa: E402
from features import parcela_price  # noqa: E402
from modelo import SAIDA, atributos_para_valor  # noqa: E402
from politica import politica_atual, politica_proposta  # noqa: E402

GANHO_POR_CLASSE = {"quitado_em_dia": .15, "em_dia": .15, "quitado_com_atraso": .05, "em_atraso": .05,
                    "inadimplente": -.60}


def saida_maior_3m(df):
    """Meses (dos 3 antes do pedido) com saídas > entradas, como em analysis/scripts-enio/base.py."""
    m = consulta("SELECT id_cliente, mes_referencia, total_entradas::float te, total_saidas::float ts "
                 "FROM hackathon.movimentacao_mensal")
    m = m.merge(df[["id_cliente", "data_pedido"]], on="id_cliente")
    lag = (m.data_pedido.dt.to_period("M") - pd.to_datetime(m.mes_referencia).dt.to_period("M")).apply(lambda x: x.n)
    m = m[(lag >= 1) & (lag <= 3)]
    s = (m.ts > m.te).groupby(m.id_cliente).sum()
    return df.id_cliente.map(s).fillna(0).values


def regras(df):
    """Política do Bilosca (src/politica_regras.py, função spread) sobre as features deste pacote."""
    passa = (df.score > 600) & (df.renda_declarada > 2000) & (df.restricoes_ativas <= 0)
    teto = 0.30 * df.renda_declarada * (1 - 1.03 ** (-df.prazo_meses.astype(float))) / 0.03
    valor = np.minimum(df.valor_solicitado, teto).round(2)
    renda_real = np.minimum(df.renda_declarada, df.mov_entradas_media.fillna(df.renda_declarada))
    passa &= ~(df.saida_maior_3m > 0)
    passa &= (parcela_price(valor, df.prazo_meses) / renda_real) <= 0.28
    v = np.where(passa, valor, 0.0)
    return pd.DataFrame({"id_pedido": df.id_pedido.values, "aprova": v > 0, "valor": v})


def filtros_bilosca(df):
    """Os dois filtros de cliente do Bilosca, medidos como ele mede: sobre o valor que a política atual
    concederia (solicitado, limitado a 30% da renda declarada), não sobre o valor já reduzido pelo G."""
    teto = 0.30 * df.renda_declarada * (1 - 1.03 ** (-df.prazo_meses.astype(float))) / 0.03
    valor_ref = np.minimum(df.valor_solicitado, teto)
    renda_real = np.minimum(df.renda_declarada, df.mov_entradas_media.fillna(df.renda_declarada))
    return ((df.saida_maior_3m > 0) | (parcela_price(valor_ref, df.prazo_meses) / renda_real > 0.28)).values


def hibrida(df, modelo):
    """G (sem corte de score, valor pelo modelo) + os filtros de cliente do Bilosca."""
    dec = politica_proposta(df, modelo).reset_index(drop=True)
    dec.loc[filtros_bilosca(df.reset_index(drop=True)), ["aprova", "valor"]] = [False, 0.0]
    return dec


def ganho_esperado(p_nao, p_atraso=None):
    p_atraso = (1 - p_nao) * 0.23 if p_atraso is None else p_atraso
    return 0.15 * (1 - p_nao - p_atraso) + 0.05 * p_atraso - 0.60 * p_nao


def avaliar_novos(decisoes, x, gbm, cons, base_sobrev):
    import tool_risco
    out = {}
    for nome, dec in decisoes.items():
        d = dec.merge(x, on="id_pedido")
        d = d[d.valor > 0].reset_index(drop=True)
        v = d.valor.values
        p1 = gbm.predict_proba(atributos_para_valor(d, v))[:, 1]
        b = base_sobrev.set_index("id_pedido").loc[d.id_pedido].reset_index()
        s = tool_risco.prever_df(b, v, cons.sobrev)
        from conselho import VARS_LOG, _prep
        p3 = cons.log.predict_proba(_prep(d, v)[VARS_LOG].fillna(0))[:, 1]
        out[nome] = {
            "aprovados": len(d), "volume": round(v.sum()),
            "gbm_corrigido": round(float((ganho_esperado(p1) * v).sum())),
            "sobrevivencia": round(float((ganho_esperado(s.p_nao_paga.values, s.p_atraso.values) * v).sum())),
            "logistico": round(float((ganho_esperado(p3) * v).sum())),
            "p_nao_paga_media": round(float(np.average(p1, weights=v)), 3),
        }
    return pd.DataFrame(out).T


def avaliar_observado(hist):
    """Fora da amostra: G treinado só até set/25; aplica a todos os pedidos de out/25 a mar/26."""
    ate = hist[hist.data_pedido <= "2025-09-30"]
    m = m_wrap(Conselho._gbm_ate(ate))  # mesmo GBM corrigido, treinado só com pedidos até set/25
    t = hist[hist.data_pedido.between("2025-10-01", "2026-03-31")].reset_index(drop=True)
    decs = {"atual": politica_atual(t), "regras_bilosca": regras(t), "G": politica_proposta(t, m),
            "G_+_filtros_bilosca": hibrida(t, m)}
    ap = t[t.decisao == "aprovado"]
    linhas = {}
    for nome, dec in decs.items():
        d = dec.merge(t[["id_pedido", "decisao", "valor_aprovado", "situacao_final"]], on="id_pedido")
        obs = d[(d.valor > 0) & (d.decisao == "aprovado")]
        v = np.minimum(obs.valor, obs.valor_aprovado)
        linhas[nome] = {"aprovados": int((d.valor > 0).sum()), "com_desfecho": len(obs),
                        "sem_desfecho_conta_zero": int(((d.valor > 0) & (d.decisao != "aprovado")).sum()),
                        "resultado_observado": round(float((v * obs.situacao_final.map(GANHO_POR_CLASSE)).sum())),
                        "nao_pagaram": int((obs.situacao_final == "inadimplente").sum())}
    _ = ap
    return pd.DataFrame(linhas).T


def main():
    import tool_risco
    pd.set_option("display.width", 220)
    hist = pd.read_pickle(SAIDA / "hist.pkl")
    x = pd.read_pickle(SAIDA / "novos.pkl").reset_index(drop=True)
    x["saida_maior_3m"] = saida_maior_3m(x)
    hist = hist.copy()
    hist["saida_maior_3m"] = saida_maior_3m(hist)

    # conferência: a reimplementação bate com o CSV gerado pelo src/pipeline.py do Bilosca?
    dec_r = regras(x)
    arq = SAIDA / "bilosca_final.csv"
    if arq.exists():
        b = pd.read_csv(arq).merge(dec_r, on="id_pedido")
        print(f"reimplementação x CSV do Bilosca: decisão igual em {(b.decisao.eq('APROVADO') == b.aprova).mean():.1%}, "
              f"valor igual (±R$1) em {(abs(b.valor_aprovado - b.valor) <= 1).mean():.1%}")

    gbm, _ = treinar_corrigido(hist)
    m = m_wrap(gbm)
    decs = {"atual": politica_atual(x), "regras_bilosca": dec_r, "G": politica_proposta(x, m),
            "G_+_filtros_bilosca": hibrida(x, m)}
    cons = Conselho().treinar(hist)
    print("\n== Resultado esperado nos 2.000 novos (R$), por avaliador ==")
    nov = avaliar_novos(decs, x, gbm, cons, tool_risco.carregar_pedidos("novo"))
    for c in ["gbm_corrigido", "sobrevivencia", "logistico"]:
        nov[f"ganho_{c}"] = nov[c] - nov.loc["atual", c]
    print(nov.to_string())
    print("\n== Fora da amostra, desfecho observado (out/25 a mar/26; sem desfecho conta zero) ==")
    obs = avaliar_observado(hist)
    obs["ganho_vs_atual"] = obs.resultado_observado - obs.loc["atual", "resultado_observado"]
    print(obs.to_string())
    nov.to_csv(SAIDA / "comparacao_finais_novos.csv")
    obs.to_csv(SAIDA / "comparacao_finais_observado.csv")


if __name__ == "__main__":
    main()
