"""Conexão com o PostgreSQL local onde o dump do hackathon foi restaurado."""
import os
from pathlib import Path

import pandas as pd
import psycopg2

ARQ_CONEXAO = Path(__file__).resolve().parents[2] / "pg16-local.txt"


def dsn() -> str:
    if os.environ.get("FORTUNA_DSN"):
        return os.environ["FORTUNA_DSN"]
    return ARQ_CONEXAO.read_text(encoding="utf-8-sig").strip()


def consulta(sql: str, params=None) -> pd.DataFrame:
    with psycopg2.connect(dsn()) as con:
        with con.cursor() as cur:
            cur.execute(sql, params)
            cols = [c.name for c in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)


def q(sql: str) -> pd.DataFrame:
    """Compatível com validacao/db.py (usado pela tool do agente quando importada junto com src/)."""
    import warnings
    with psycopg2.connect(dsn()) as con:
        con.set_session(readonly=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return pd.read_sql(sql, con)
