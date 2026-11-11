"""Backtest no histórico maduro: quanto a nossa política ganha sobre a atual.

Só mede o que dá para medir. O desfecho existe apenas para pedidos que a Fortuna aprovou, então
o backtest responde "negar estes aqui melhora quanto?" — que é exatamente a direção da nossa
política. Aprovar quem a atual negou não é mensurável nesta base: é aposta, e está fora.

Maturidade: pedido até 30/09/2025 (12+ meses de contrato). As safras de 2026 têm calote perto de
zero só por falta de tempo; incluí-las infla qualquer política.

Uso (da raiz do repositório):
    .venv/Scripts/python src/backtest_maduro.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "scripts-enio"))
sys.path.insert(0, str(ROOT / "src"))

from base import carregar  # noqa: E402
from politica_regras import POLITICAS, atual  # noqa: E402

MATURIDADE = pd.Timestamp("2025-09-30")
EXPERIMENTO = (pd.Timestamp("2025-10-01"), pd.Timestamp("2026-03-31"))
RETORNO = {"em_dia": 0.15, "atraso": 0.05, "nao_paga": -0.60}


def conferir_reproducao(df: pd.DataFrame) -> None:
    """A política atual só serve de piso se reproduzir as decisões reais. Falha alto se não bate.

    Fora da janela do experimento, a regra reproduz as decisões exatamente. Dentro dela a Fortuna
    aprovou 427 pedidos que a regra nega (score baixo, restrição, renda baixa) e o resultado foi
    negativo — ver src/experimento.py. Os 2.000 novos são de out/26, fora da janela, então o piso
    é a regra rígida.
    """
    fora = df[~df.data_pedido.between(*EXPERIMENTO)]
    r = atual(fora)
    real_aprovado = fora.decisao == "aprovado"
    igual = (r.decisao == "APROVADO") == real_aprovado
    pct = igual.mean()
    print(f"reprodução da política atual (fora da janela do experimento): "
          f"{igual.sum()}/{len(fora)} decisões ({pct:.2%})")
    if pct < 0.99:
        raise SystemExit("A reprodução da política atual não bate com o histórico. "
                         "Sem piso confiável não dá para medir ganho — pare e investigue.")

    ap = fora[real_aprovado]
    r = r[real_aprovado]
    dif = (r.valor_aprovado - ap.valor_aprovado).abs()
    print(f"valor aprovado: erro máximo R$ {dif.max():,.2f} · média R$ {dif.mean():,.2f}")


def resultado(df: pd.DataFrame, dec: pd.DataFrame) -> float:
    """Resultado financeiro de um conjunto de decisões, pelas regras do manual."""
    aprovado = dec.decisao == "APROVADO"
    retorno = df.classe.map(RETORNO).fillna(0.0)
    return float((dec.valor_aprovado * retorno * aprovado).sum())


def main() -> None:
    df = carregar()
    conferir_reproducao(df)

    maduro = df[(df.decisao == "aprovado") & (df.data_pedido <= MATURIDADE)].copy()
    print(f"\nbase madura: {len(maduro)} pedidos aprovados até {MATURIDADE:%d/%m/%Y}")
    print(maduro.classe.value_counts(normalize=True).to_string())

    base = resultado(maduro, atual(maduro))
    print(f"\n{'política':<10} {'aprovados':>10} {'emprestado':>16} {'resultado':>16} {'ganho':>16}")
    for nome, fn in POLITICAS.items():
        dec = fn(maduro)
        ap = dec.decisao == "APROVADO"
        res = resultado(maduro, dec)
        print(f"{nome:<10} {ap.sum():>10} {dec.valor_aprovado[ap].sum():>16,.2f} "
              f"{res:>16,.2f} {res - base:>16,.2f}")

    print("\nnegados pela nossa política (todos já aprovados pela atual):")
    dec = POLITICAS["spread"](maduro)
    negados = maduro[dec.decisao == "NEGADO"]
    print(negados.classe.value_counts().to_string())
    perdido = resultado(negados, atual(negados))
    print(f"resultado que esses pedidos davam: R$ {perdido:,.2f} (negá-los soma {-perdido:,.2f})")


if __name__ == "__main__":
    main()
