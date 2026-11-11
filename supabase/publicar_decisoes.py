"""Publica as decisões do pipeline em painel.decisoes, para o analista revisar no painel.

Uso, da raiz do repositório, com SUPABASE_DB_URL no .env e o dump já restaurado no Supabase:
    .venv/Scripts/python supabase/publicar_decisoes.py                                   # saida/decisoes_detalhadas.csv
    .venv/Scripts/python supabase/publicar_decisoes.py --arquivo saida/spread_final.csv

Aceita o CSV detalhado do src/gerar_decisoes.py (id_pedido, aprova, valor, p_nao_paga, ganho_esperado, motivo,
atual_aprova, atual_valor) ou o formato de entrega (id_pedido, decisao, valor_aprovado). Tudo numa transação:
confere 2.000 pedidos novos, valor até o solicitado e até R$ 30 mil, ou não grava nada. Revisões já feitas
continuam valendo (cada uma guarda a decisão da IA do momento em que foi feita).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from restaurar_banco import ROOT, conexao  # noqa: E402

PADRAO = ROOT / "saida" / "decisoes_detalhadas.csv"
COLUNAS = ["id_pedido", "decisao", "valor_aprovado", "motivo", "p_nao_paga", "ganho_esperado",
           "atual_decisao", "atual_valor"]


def le(arq: Path) -> list[tuple]:
    d = pd.read_csv(arq, dtype={"id_pedido": str})
    sim = lambda s: s.astype(str).str.lower().isin(["true", "1"])  # noqa: E731
    if {"aprova", "valor"} <= set(d.columns):  # CSV detalhado do src/
        d["decisao"] = sim(d.aprova).map({True: "APROVADO", False: "NEGADO"})
        d["valor_aprovado"] = d.valor
        if {"atual_aprova", "atual_valor"} <= set(d.columns):
            d["atual_decisao"] = sim(d.atual_aprova).map({True: "APROVADO", False: "NEGADO"})
    elif not {"decisao", "valor_aprovado"} <= set(d.columns):
        sys.exit(f"{arq.name}: esperava as colunas aprova/valor ou decisao/valor_aprovado")
    for c in COLUNAS:
        if c not in d.columns:
            d[c] = None
    d = d[COLUNAS].copy()
    d["valor_aprovado"] = pd.to_numeric(d.valor_aprovado).round(2)
    if d.id_pedido.duplicated().any():
        sys.exit(f"{arq.name}: id_pedido repetido")
    if not d.decisao.isin(["APROVADO", "NEGADO"]).all():
        sys.exit(f"{arq.name}: decisão fora de APROVADO/NEGADO")
    colunas = [[None if pd.isna(v) else v for v in d[c].tolist()] for c in COLUNAS]  # tipos nativos do Python
    return list(zip(*colunas))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arquivo", default=str(PADRAO))
    args = ap.parse_args()
    arq = Path(args.arquivo)
    if not arq.exists():
        sys.exit(f"não achei {arq}; gere com: cd src && python gerar_decisoes.py")
    linhas = le(arq)
    fonte = f"{arq.name} sha256:{hashlib.sha256(arq.read_bytes()).hexdigest()[:12]}"

    load_dotenv(ROOT / ".env")
    with psycopg.connect(**conexao(), connect_timeout=15) as c, c.transaction():
        c.execute("create temp table entrada (id_pedido text, decisao text, valor_aprovado numeric, motivo text, "
                  "p_nao_paga numeric, ganho_esperado numeric, atual_decisao text, atual_valor numeric) on commit drop")
        with c.cursor().copy("copy entrada from stdin") as cp:
            for linha in linhas:
                cp.write_row(linha)
        ruins = c.execute("""
            select count(*) filter (where p.id_pedido is null) as sem_pedido,
                   count(*) filter (where e.valor_aprovado > least(p.valor_solicitado, 30000)
                                       or e.valor_aprovado < 0) as valor_invalido,
                   count(*) filter (where (e.decisao = 'NEGADO') <> (e.valor_aprovado = 0)) as decisao_valor
            from entrada e left join hackathon.pedidos p on p.id_pedido = e.id_pedido and p.tipo_base = 'novo'
        """).fetchone()
        total = c.execute("select count(*) from entrada").fetchone()[0]
        if total != 2000 or any(ruins):
            raise SystemExit(f"nada gravado: {total} linhas (esperado 2.000); fora dos novos: {ruins[0]}; "
                             f"valor inválido: {ruins[1]}; decisão x valor: {ruins[2]}")
        c.execute("""
            insert into painel.decisoes as d (id_pedido, id_cliente, valor_solicitado, prazo_meses, decisao,
                   valor_aprovado, motivo, p_nao_paga, ganho_esperado, atual_decisao, atual_valor, fonte, publicado_em)
            select e.id_pedido, p.id_cliente, p.valor_solicitado, p.prazo_meses, e.decisao, e.valor_aprovado,
                   e.motivo, e.p_nao_paga, e.ganho_esperado, e.atual_decisao, e.atual_valor, %s, now()
            from entrada e join hackathon.pedidos p using (id_pedido)
            on conflict (id_pedido) do update set
              decisao = excluded.decisao, valor_aprovado = excluded.valor_aprovado, motivo = excluded.motivo,
              p_nao_paga = excluded.p_nao_paga, ganho_esperado = excluded.ganho_esperado,
              atual_decisao = excluded.atual_decisao, atual_valor = excluded.atual_valor,
              fonte = excluded.fonte, publicado_em = excluded.publicado_em
        """, (fonte,))
        ap_, vol = c.execute("select count(*) filter (where decisao = 'APROVADO'), sum(valor_aprovado) "
                             "from painel.decisoes").fetchone()
    print(f"publicado {fonte}: {ap_} aprovados de 2.000, R$ {vol:,.2f}")


if __name__ == "__main__":
    main()
