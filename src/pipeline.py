"""Gera o spread_final.csv: a decisão do time para os 2.000 pedidos novos.

Um comando, do banco ao arquivo validado:
    .venv/Scripts/python src/pipeline.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "scripts-enio"))
sys.path.insert(0, str(ROOT / "src"))

import bureau_api as bureau  # noqa: E402
from base import carregar  # noqa: E402
from politica_regras import POLITICAS, PARAMS  # noqa: E402
from validar import validar  # noqa: E402

SAIDA = ROOT / "spread_final.csv"


def base_novos() -> pd.DataFrame:
    """Os 2.000 pedidos novos com features e o birô da API (a tabela `bureau` só tem histórico)."""
    df = carregar(tipo="novo")
    bur = bureau.tabela()
    faltam = set(df.id_cliente) - set(bur.id_cliente)
    if faltam:
        raise SystemExit(f"birô faltando para {len(faltam)} clientes. Rode: python src/bureau_api.py")
    return df.merge(bur, on="id_cliente", how="left")


def main() -> None:
    df = base_novos()
    print(f"{len(df)} pedidos novos · birô completo")

    dec = POLITICAS["spread"](df)
    saida = pd.DataFrame({"id_pedido": df.id_pedido,
                          "decisao": dec.decisao,
                          "valor_aprovado": dec.valor_aprovado.map(lambda v: f"{v:.2f}")})
    saida.to_csv(SAIDA, index=False, encoding="utf-8", lineterminator="\n")

    comp = POLITICAS["atual"](df)
    for nome, d in (("atual", comp), ("spread", dec)):
        ap = d.decisao == "APROVADO"
        print(f"{nome:<8} aprovados {ap.sum():>5} · emprestado R$ {d.valor_aprovado[ap].sum():>14,.2f}")

    print(f"\nPARAMS: {PARAMS}")
    print(f"\narquivo: {SAIDA}")
    validar(SAIDA, df.set_index("id_pedido").valor_solicitado)


if __name__ == "__main__":
    main()
