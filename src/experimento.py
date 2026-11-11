"""Padrão: a Fortuna já testou afrouxar a regra — e voltou atrás.

Achado pela IA ao conferir se a "política atual" documentada reproduz as decisões reais.
Ela reproduz 7.490 de 7.490 (100%) — exceto numa janela de 6 meses.

    01/10/2025 a 31/03/2026: 427 pedidos aprovados fora da regra (score <= 600, restrição ativa
    ou renda <= 2.000). Zero antes, zero depois. Não é ruído nem deriva: é uma janela fechada.

Resultado do experimento, pelas regras do manual: NEGATIVO, e o número ainda é otimista porque
esses contratos têm 7 a 13 meses — parte do calote não apareceu.

Por que isso decide a nossa política: era a dúvida em aberto do time (testes 4 e 5 de
analysis/para-discussao.md — "dá para aprovar quem tem 1 restrição? dá para afrouxar o score?").
A resposta está na base: a própria Fortuna testou e desistiu. Afrouxar é a única direção que pode
dar ganho negativo, e agora há evidência direta de que dá. Por isso a política do time só aperta.

Os 2.000 pedidos novos são de out/26, fora da janela, sob a regra rígida.

Uso:
    .venv/Scripts/python src/experimento.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "scripts-enio"))
sys.path.insert(0, str(ROOT / "src"))

from base import carregar  # noqa: E402
from politica_regras import atual  # noqa: E402

RETORNO = {"em_dia": 0.15, "atraso": 0.05, "nao_paga": -0.60}


def main() -> None:
    df = carregar()
    df["na_regra"] = atual(df).decisao == "APROVADO"
    df["excecao"] = (df.decisao == "aprovado") & ~df.na_regra

    g = df.groupby(df.data_pedido.dt.to_period("Q"))
    print("aprovações fora da regra, por trimestre:")
    print(pd.DataFrame({"pedidos": g.size(),
                        "aprovados": (df.decisao == "aprovado").groupby(g.ngroup()).sum().values,
                        "excecoes": g.excecao.sum()}).to_string())

    exc = df[df.excecao]
    print(f"\n{len(exc)} exceções · de {exc.data_pedido.min():%d/%m/%Y} a {exc.data_pedido.max():%d/%m/%Y}")
    print(f"motivo da regra negar: score<=600 em {(exc.score <= 600).sum()}, "
          f"restrição em {(exc.restricoes_ativas > 0).sum()}, "
          f"renda<=2000 em {(exc.renda_declarada <= 2000).sum()}")

    print("\ndesfecho das exceções:")
    print(exc.classe.value_counts().to_string())
    res = float((exc.classe.map(RETORNO) * exc.valor_aprovado).sum())
    emp = float(exc.valor_aprovado.sum())
    print(f"\nemprestado R$ {emp:,.2f} · resultado R$ {res:,.2f} ({res / emp:.2%})")

    dentro = df[(df.decisao == "aprovado") & df.na_regra & df.data_pedido.between(
        exc.data_pedido.min(), exc.data_pedido.max())]
    res_d = float((dentro.classe.map(RETORNO) * dentro.valor_aprovado).sum())
    emp_d = float(dentro.valor_aprovado.sum())
    print(f"mesma janela, dentro da regra: R$ {res_d:,.2f} sobre R$ {emp_d:,.2f} ({res_d / emp_d:.2%})")
    print("\nMesmas safras, mesma maturidade: dentro da regra dá lucro, fora dá prejuízo.")


if __name__ == "__main__":
    main()
