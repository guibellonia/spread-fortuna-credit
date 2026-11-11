"""Valida o arquivo de decisões nas regras do manual (seção 5.2) e mostra a composição do arquivo."""
import csv
import re
import sys

from db import consulta

CABECALHO = ["id_pedido", "decisao", "valor_aprovado"]


def validar(caminho):
    erros, avisos = [], []
    novos = consulta("SELECT id_pedido, valor_solicitado FROM hackathon.pedidos WHERE tipo_base = 'novo'")
    sol = dict(zip(novos.id_pedido, novos.valor_solicitado.astype(float)))
    with open(caminho, "rb") as f:
        bruto = f.read()
    if bruto.startswith(b"\xef\xbb\xbf"):
        erros.append("arquivo com BOM: salve em UTF-8 sem BOM")
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError:
        return ["arquivo não está em UTF-8"], [], {}
    if "\r\n" in texto:
        avisos.append("quebra de linha CRLF (Windows); o gerador usa LF")
    linhas = list(csv.reader(texto.lstrip("﻿").splitlines()))
    if not linhas or linhas[0] != CABECALHO:
        erros.append(f"cabeçalho deve ser exatamente {','.join(CABECALHO)}; veio {linhas[0] if linhas else 'vazio'}")
    vistos, aprov, neg, total = set(), 0, 0, 0.0
    for n, linha in enumerate(linhas[1:], 2):
        if len(linha) != 3:
            erros.append(f"linha {n}: {len(linha)} colunas")
            continue
        i, d, v = linha
        if i in vistos:
            erros.append(f"linha {n}: {i} repetido")
        vistos.add(i)
        if i not in sol:
            erros.append(f"linha {n}: {i} não existe na base de novos")
        if d not in ("APROVADO", "NEGADO"):
            erros.append(f"linha {n}: decisao '{d}' (use APROVADO ou NEGADO)")
        if not re.fullmatch(r"\d+\.\d{2}", v):
            erros.append(f"linha {n}: valor '{v}' fora do formato 0.00")
            continue
        v = float(v)
        if d == "APROVADO":
            aprov += 1
            total += v
            if v <= 0:
                erros.append(f"linha {n}: aprovado com valor {v}")
            if i in sol and v > sol[i] + 1e-9:
                erros.append(f"linha {n}: valor {v} acima do solicitado {sol[i]}")
            if v > 30000:
                erros.append(f"linha {n}: valor acima de R$ 30 mil")
        elif d == "NEGADO":
            neg += 1
            if v != 0:
                erros.append(f"linha {n}: negado com valor {v}")
    faltando = set(sol) - vistos
    if faltando:
        erros.append(f"{len(faltando)} pedidos novos ausentes do arquivo (contam como negado)")
    rel = {"linhas": len(linhas) - 1, "pedidos_novos": len(sol), "aprovados": aprov, "negados": neg,
           "valor_total_aprovado": round(total, 2)}
    return erros, avisos, rel


if __name__ == "__main__":
    erros, avisos, rel = validar(sys.argv[1])
    print("composição:", rel)
    for a in avisos:
        print("AVISO:", a)
    for e in erros[:30]:
        print("ERRO:", e)
    print("OK: arquivo no formato do manual" if not erros else f"{len(erros)} erro(s)")
    sys.exit(1 if erros else 0)
