"""Gera spread_final.csv do zero: lê o banco, treina o modelo, consulta o bureau e aplica a política proposta."""
import argparse
from pathlib import Path

import pandas as pd

import bureau
from features import bureau_historico, montar, movimentacao_agregada, pedidos_base
from modelo import treinar
from politica import PARAMS, politica_atual, politica_proposta

SAIDA = Path(__file__).resolve().parents[1] / "saida"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=str(SAIDA / "spread_final.csv"))
    args = ap.parse_args()
    SAIDA.mkdir(exist_ok=True)

    base, mov = pedidos_base(), movimentacao_agregada()
    hist = montar(base[base.tipo_base == "historico"], mov, bureau_historico())
    hist.to_pickle(SAIDA / "hist.pkl")
    treinar(hist)  # modelo de 3 classes original (painel/backtest)
    from cenarios import m_wrap, treinar_corrigido
    corrigido, meta = treinar_corrigido(hist)  # cenário G: modelo corrigido para censura
    modelo = m_wrap(corrigido)
    print("modelo corrigido:", meta)

    novos = base[base.tipo_base == "novo"]
    print("bureau online:", bureau.saude())
    resp = bureau.consultar_lote(novos.id_cliente.tolist())
    b = pd.DataFrame(list(resp.values()), columns=["id_cliente"] + bureau.CAMPOS)
    b["parcelas_outras_instituicoes"] = b["parcelas_outras_instituicoes"].astype(float)
    x = montar(novos, mov, b, chave_bureau="id_cliente")
    sem_bureau = x["score"].isna()
    if sem_bureau.any():
        raise SystemExit(f"{sem_bureau.sum()} pedidos sem dados do bureau: rode de novo (o cache guarda o que já veio)")
    x.to_pickle(SAIDA / "novos.pkl")

    prop = politica_proposta(x, modelo)
    atual = politica_atual(x)
    det = prop.merge(atual.rename(columns={"aprova": "atual_aprova", "valor": "atual_valor"}), on="id_pedido")
    det.to_csv(SAIDA / "decisoes_detalhadas.csv", index=False, encoding="utf-8")

    out = pd.DataFrame({
        "id_pedido": prop.id_pedido,
        "decisao": prop.aprova.map({True: "APROVADO", False: "NEGADO"}),
        "valor_aprovado": prop.valor.map(lambda v: f"{v:.2f}"),
    })
    with open(args.saida, "w", encoding="utf-8", newline="") as f:
        out.to_csv(f, index=False, lineterminator="\n")
    print(f"gravado {args.saida}: {int(prop.aprova.sum())} aprovados de {len(prop)}, "
          f"R$ {prop.valor.sum():,.2f}; difere da política atual em {int((det.aprova != det.atual_aprova).sum())} pedidos")
    print("parâmetros:", PARAMS)


if __name__ == "__main__":
    main()
