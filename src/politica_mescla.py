"""Política proposta do time: a mescla das contribuições, comparada com as alternativas.

Resultado da comparação (python politica_mescla.py --comparar, 11/11 12h30): a híbrida do src/politica.py ganha nas
quatro medidas: +R$ 385 a 500 mil esperados nos 2.000 novos pelos três avaliadores e +R$ 398 mil observados fora
da amostra, contra +R$ 258 a 337 mil das regras e +R$ 260 a 324 mil da variante que só aperta. A trava "só aperta"
nega 384 pedidos de score até 600 que, depois das barreiras, têm risco baixo (o score não separa bom e mau pagador).
Por isso a proposta é a híbrida; a variante que só aperta fica medida aqui como alternativa recusada.

O que vem de cada um:
- Juliano (src/politica.py, híbrida G): o modelo corrigido de censura escolhe, entre 100% e 10% do solicitado, o valor
  de maior ganho esperado com P(não pagar) até 17,5%; parcela até 28% da renda declarada; múltiplo de R$ 100;
  mínimo R$ 500, máximo R$ 30 mil.
- Bilosca (src/politica_regras.py): as barreiras de conta apertada e de parcela acima de 28% da renda real, e a
  evidência do experimento da Fortuna (out/25 a mar/26): afrouxar score ou restrição sem as barreiras deu prejuízo.
  Medida aqui como variante "só aperta" (nunca aprova quem a atual nega): rende menos que a híbrida.
- Daniel (analysis/pontuacao-risco.md): sem a regra de saldo negativo, teto plano até 28%, e a pontuação em três
  faixas, que não decide: diz ao analista quanto confiar no cliente e quem revisar primeiro.
- Enio (analysis/analise-enio.md): os dois padrões fortes que viraram barreiras.

Uso, de dentro de src/, depois de `python gerar_decisoes.py` (que grava saida/novos.pkl e decisoes_detalhadas.csv):
    python politica_mescla.py              # saida/decisoes_mescla.csv (proposta, alternativas e faixa de risco)
    python politica_mescla.py --comparar   # e compara atual, regras, híbrida e mescla com os 3 avaliadores
                                           # e no teste fora da amostra (demora alguns minutos)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI.parent / "saida"
REF_ATUAL = "a política atual nega"


def guarda_atual(x: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Quem a política atual aprova (score > 600, renda > R$ 2 mil, sem restrição) e o motivo de quem ela nega."""
    score, renda, restr = x["score"].to_numpy(), x["renda_declarada"].to_numpy(), x["restricoes_ativas"].to_numpy()
    passa = (score > 600) & (renda > 2000) & (restr == 0)
    motivo = np.where(restr > 0, "restrição ativa no bureau",
                      np.where(score <= 600, f"score até 600 ({REF_ATUAL})", f"renda até R$ 2 mil ({REF_ATUAL})"))
    return passa, motivo


def pontuacao(x: pd.DataFrame, valor: np.ndarray) -> pd.DataFrame:
    """Pontuação do Daniel (analysis/pontuacao-risco.md), para quem passou pelas barreiras.
    Entradas instáveis = coeficiente de variação das entradas mensais de 16% ou mais."""
    prazo = x["prazo_meses"].to_numpy()
    vinc = x["tipo_vinculo"].to_numpy()
    renda_real = np.minimum(x["renda_declarada"], x["mov_entradas_media"].fillna(x["renda_declarada"])).to_numpy()
    teto30 = 0.30 * x["renda_declarada"] * (1 - 1.03 ** (-x["prazo_meses"].astype(float))) / 0.03
    ref = np.where(valor > 0, valor, np.minimum(x["valor_solicitado"], teto30))
    parcela = ref * 0.03 / (1 - 1.03 ** (-prazo.astype(float)))
    comprom = (parcela + x["parcelas_outras_instituicoes"].fillna(0).to_numpy()) / renda_real
    sinais = [
        ("prazo curto", np.isin(prazo, [6, 12]), 1),
        ("prazo de 36 meses", prazo == 36, -1),
        ("autônomo ou empresário", np.isin(vinc, ["autonomo", "empresario"]), 1),
        ("aposentado", vinc == "aposentado", -1),
        ("entradas instáveis", x["mov_entradas_cv"].fillna(0).to_numpy() >= 0.16, 1),
        ("parcela + dívidas ≥ 35% da renda real", comprom >= 0.35, 1),
    ]
    pontos = sum(np.where(m, p, 0) for _, m, p in sinais)
    detalhe = [", ".join(f"{'+' if p > 0 else '−'}1 {n}" for n, m, p in sinais if m[i]) or "nenhum sinal"
               for i in range(len(x))]
    faixa = np.select([pontos <= 0, pontos == 1], ["verde", "amarela"], "laranja")
    return pd.DataFrame({"pontos": pontos, "faixa": faixa, "pontos_detalhe": detalhe})


def regras_bilosca(x: pd.DataFrame) -> pd.DataFrame:
    sys.path.insert(0, str(AQUI))
    from comparar_finais import regras, saida_maior_3m
    x = x.copy()
    x["saida_maior_3m"] = saida_maior_3m(x)
    return regras(x)


def montar(x: pd.DataFrame, det: pd.DataFrame) -> pd.DataFrame:
    x = x.reset_index(drop=True)
    det = det.set_index("id_pedido").loc[x["id_pedido"]].reset_index()
    sim = lambda s: s.astype(str).str.lower().isin(["true", "1"]).to_numpy()  # noqa: E731
    hib_aprova, hib_valor = sim(det["aprova"]), det["valor"].to_numpy(float)
    aprova, valor, motivo = hib_aprova, np.where(hib_aprova, hib_valor, 0.0), det["motivo"].to_numpy(object)
    reg = regras_bilosca(x).set_index("id_pedido").loc[x["id_pedido"]]
    pts = pontuacao(x, valor)
    barreira = det["motivo"].str.startswith(("conta apertada", "parcela acima de 28%", "restrição")).to_numpy()
    rotulo = lambda a: np.where(a, "APROVADO", "NEGADO")  # noqa: E731
    return pd.DataFrame({
        "id_pedido": x["id_pedido"], "decisao": rotulo(aprova), "valor_aprovado": valor.round(2), "motivo": motivo,
        "p_nao_paga": det["p_nao_paga"], "ganho_esperado": np.where(aprova, det["ganho_esperado"], 0.0),
        "atual_decisao": rotulo(sim(det["atual_aprova"])), "atual_valor": det["atual_valor"].astype(float).round(2),
        "regras_decisao": rotulo(reg["aprova"].to_numpy()), "regras_valor": reg["valor"].to_numpy(float).round(2),
        "pontos": pts["pontos"], "faixa": np.where(barreira, "barreira", pts["faixa"]),
        "pontos_detalhe": np.where(barreira, "barrado antes da pontuação", pts["pontos_detalhe"]),
    })


def comparar(x: pd.DataFrame, dec_mescla: pd.DataFrame) -> None:
    """Mesmo comparador do Juliano (src/comparar_finais.py), com a mescla entre as candidatas."""
    sys.path.insert(0, str(AQUI))
    sys.path.append(str(AQUI.parent / "validacao"))
    import tool_risco
    from cenarios import m_wrap, treinar_corrigido
    from comparar_finais import GANHO_POR_CLASSE, avaliar_novos, regras, saida_maior_3m
    from conselho import Conselho
    from politica import politica_atual, politica_proposta

    pd.set_option("display.width", 220)
    hist = pd.read_pickle(SAIDA / "hist.pkl").copy()
    hist["saida_maior_3m"] = saida_maior_3m(hist)
    x = x.reset_index(drop=True).copy()
    x["saida_maior_3m"] = saida_maior_3m(x)

    gbm, _ = treinar_corrigido(hist)
    m = m_wrap(gbm)
    hib = politica_proposta(x, m)
    passa, _ = guarda_atual(x)
    mes = hib.copy()
    mes.loc[~passa, ["aprova", "valor"]] = [False, 0.0]
    decs = {"atual": politica_atual(x), "regras_bilosca": regras(x), "hibrida": hib, "so_aperta": mes}
    cons = Conselho().treinar(hist)
    nov = avaliar_novos(decs, x, gbm, cons, tool_risco.carregar_pedidos("novo"))
    for c in ["gbm_corrigido", "sobrevivencia", "logistico"]:
        nov[f"ganho_{c}"] = nov[c] - nov.loc["atual", c]
    print("\n== Resultado esperado nos 2.000 novos (R$), por avaliador ==")
    print(nov.to_string())

    # fora da amostra: modelo treinado só até set/25, aplicado a out/25-mar/26, com desfecho observado
    ate = hist[hist.data_pedido <= "2025-09-30"]
    m2 = m_wrap(Conselho._gbm_ate(ate))
    t = hist[hist.data_pedido.between("2025-10-01", "2026-03-31")].reset_index(drop=True)
    hib_t = politica_proposta(t, m2)
    mes_t = hib_t.copy()
    mes_t.loc[~guarda_atual(t)[0], ["aprova", "valor"]] = [False, 0.0]
    linhas = {}
    for nome, dec in {"atual": politica_atual(t), "regras_bilosca": regras(t), "hibrida": hib_t, "so_aperta": mes_t}.items():
        d = dec.merge(t[["id_pedido", "decisao", "valor_aprovado", "situacao_final"]], on="id_pedido")
        obs = d[(d.valor > 0) & (d.decisao == "aprovado")]
        v = np.minimum(obs.valor, obs.valor_aprovado)
        linhas[nome] = {"aprovados": int((d.valor > 0).sum()), "com_desfecho": len(obs),
                        "resultado_observado": round(float((v * obs.situacao_final.map(GANHO_POR_CLASSE)).sum())),
                        "nao_pagaram": int((obs.situacao_final == "inadimplente").sum())}
    obs = pd.DataFrame(linhas).T
    obs["ganho_vs_atual"] = obs.resultado_observado - obs.loc["atual", "resultado_observado"]
    print("\n== Fora da amostra, desfecho observado (out/25 a mar/26; sem desfecho conta zero) ==")
    print(obs.to_string())
    nov.to_csv(SAIDA / "comparacao_mescla_novos.csv")
    obs.to_csv(SAIDA / "comparacao_mescla_observado.csv")
    igual = (hib.set_index("id_pedido").valor.round(2) == dec_mescla.set_index("id_pedido").valor_aprovado).mean()
    print(f"\nconferência: a proposta recalculada bate com decisoes_mescla.csv em {igual:.1%} dos pedidos")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comparar", action="store_true")
    args = ap.parse_args()
    x = pd.read_pickle(SAIDA / "novos.pkl")
    det = pd.read_csv(SAIDA / "decisoes_detalhadas.csv", dtype={"id_pedido": str})
    d = montar(x, det)
    d.to_csv(SAIDA / "decisoes_mescla.csv", index=False, encoding="utf-8")
    ap_ = d.decisao.eq("APROVADO")
    print(f"proposta: {ap_.sum()} aprovados de {len(d)}, R$ {d.valor_aprovado.sum():,.2f} · difere da atual em "
          f"{(d.decisao != d.atual_decisao).sum()} e das regras em {(d.decisao != d.regras_decisao).sum()} pedidos")
    print("faixas:", d.faixa.value_counts().to_dict())
    print("gravado: saida/decisoes_mescla.csv · o arquivo de entrega continua saida/spread_final.csv (gerar_decisoes.py)")
    if args.comparar:
        comparar(x, d)


if __name__ == "__main__":
    main()
