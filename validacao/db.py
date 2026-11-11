"""Acesso somente-leitura ao banco fortuna (schema hackathon).
Conexão: variável FORTUNA_DSN (ex.: Supabase, com sslmode=require) ou, se ausente, o arquivo local pg16-local.txt."""
import os
import warnings

import pandas as pd
import psycopg2

CONN_FILE = r"C:\Users\Juliano Ferreira\Downloads\material\pg16-local.txt"


def _dsn():
    return os.environ.get("FORTUNA_DSN") or open(CONN_FILE, encoding="utf-8-sig").read().strip()


def q(sql):
    with psycopg2.connect(_dsn()) as c:
        c.set_session(readonly=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return pd.read_sql(sql, c)
