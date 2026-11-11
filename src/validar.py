"""Validador do CSV, conferido contra o formato do manual.

Arquivo fora do formato não pontua, então o pipeline valida sempre e falha alto.
Regras (resumo-abertura.md): UTF-8 · vírgula · ponto decimal com 2 casas · APROVADO/NEGADO em
maiúsculas · 0.00 quando negado · valor nunca acima do pedido nem de 30000.

Uso avulso:
    .venv/Scripts/python src/validar.py spread_final.csv
"""
import re
import sys
from pathlib import Path

import pandas as pd

TETO = 30000.0
VALOR = re.compile(r"^\d+\.\d{2}$")


def validar(caminho: Path, solicitado: pd.Series | None = None) -> None:
    """Confere o CSV. Levanta SystemExit na primeira falha, com a linha do problema."""
    texto = Path(caminho).read_bytes().decode("utf-8")
    linhas = texto.strip("\n").split("\n")
    erros = []

    if linhas[0] != "id_pedido,decisao,valor_aprovado":
        erros.append(f"cabeçalho errado: {linhas[0]!r}")

    vistos = set()
    for n, linha in enumerate(linhas[1:], start=2):
        campos = linha.split(",")
        if len(campos) != 3:
            erros.append(f"linha {n}: {len(campos)} campos, esperado 3")
            continue
        pid, decisao, valor = campos
        if pid in vistos:
            erros.append(f"linha {n}: id_pedido {pid} repetido")
        vistos.add(pid)
        if decisao not in ("APROVADO", "NEGADO"):
            erros.append(f"linha {n}: decisão {decisao!r}")
            continue
        if not VALOR.match(valor):
            erros.append(f"linha {n}: valor {valor!r} fora do formato 0.00")
            continue
        v = float(valor)
        if decisao == "NEGADO" and v != 0.0:
            erros.append(f"linha {n}: negado com valor {valor}")
        if v > TETO:
            erros.append(f"linha {n}: valor {valor} acima do teto de {TETO:.2f}")
        if solicitado is not None and pid in solicitado.index and v > float(solicitado[pid]) + 0.01:
            erros.append(f"linha {n}: valor {valor} acima do solicitado {solicitado[pid]:.2f}")

    if solicitado is not None and len(vistos) != len(solicitado):
        erros.append(f"{len(vistos)} pedidos no CSV, esperado {len(solicitado)}")

    if erros:
        for e in erros[:20]:
            print("ERRO:", e)
        raise SystemExit(f"CSV inválido: {len(erros)} problema(s). NÃO ENVIE.")
    print(f"CSV válido: {len(vistos)} pedidos, formato conferido.")


if __name__ == "__main__":
    validar(Path(sys.argv[1] if len(sys.argv) > 1 else "spread_final.csv"))
