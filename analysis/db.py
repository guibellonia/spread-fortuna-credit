"""Conexão com o Postgres do hackathon (lê o .env da raiz do repositório)."""
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def query(sql: str, params=None) -> pd.DataFrame:
    with psycopg.connect() as conn:  # usa PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE
        cur = conn.execute(sql, params)
        cols = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)
