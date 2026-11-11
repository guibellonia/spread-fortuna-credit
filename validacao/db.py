"""Acesso somente-leitura ao banco fortuna (schema hackathon)."""
import psycopg2, pandas as pd, warnings
CONN_FILE = r"C:\Users\Juliano Ferreira\Downloads\material\pg16-local.txt"
def q(sql):
    dsn = open(CONN_FILE, encoding="utf-8-sig").read().strip()
    with psycopg2.connect(dsn) as c:
        c.set_session(readonly=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return pd.read_sql(sql, c)
