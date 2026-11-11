"""Birô dos clientes dos pedidos novos, com retry nos 503 e cache em disco.

A resposta de um cliente não muda (manual), então cachear é seguro e o pipeline fica reprodutível
sem depender da API no dia da entrega.

Uso (da raiz do repositório):
    .venv/Scripts/python src/bureau_api.py
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import psycopg
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
CACHE = ROOT / "data" / "cache" / "bureau_novos.json"
URL, TOKEN = os.environ["BUREAU_URL"], os.environ["BUREAU_TOKEN"]
TENTATIVAS = 6


def _ler_cache() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def _ids_novos() -> list[str]:
    with psycopg.connect() as c:
        return [r[0] for r in c.execute(
            "select distinct id_cliente from hackathon.pedidos where tipo_base='novo'")]


def _buscar(sessao: requests.Session, cid: str):
    """Uma consulta, com backoff. Devolve o dict do birô ou None se esgotou as tentativas."""
    for n in range(TENTATIVAS):
        try:
            r = sessao.get(f"{URL}/v1/bureau/{cid}",
                           headers={"Authorization": f"Bearer {TOKEN}"}, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (401, 403):
                raise SystemExit(f"birô recusou o token ({r.status_code}): confira BUREAU_TOKEN no .env")
        except requests.RequestException:
            pass
        time.sleep(0.5 * 2 ** n)
    return None


def coletar(workers: int = 10) -> dict:
    """Garante o birô de todo cliente novo no cache. Só busca o que falta."""
    cache = _ler_cache()
    faltam = [c for c in _ids_novos() if c not in cache]
    if faltam:
        print(f"consultando o birô de {len(faltam)} clientes...")
        with requests.Session() as s, ThreadPoolExecutor(workers) as ex:
            for cid, dado in zip(faltam, ex.map(lambda c: _buscar(s, c), faltam)):
                if dado is not None:
                    cache[cid] = dado
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache))
    return cache


def tabela() -> pd.DataFrame:
    """Birô dos clientes novos como DataFrame, uma linha por id_cliente."""
    return pd.DataFrame.from_records(list(coletar().values()))


if __name__ == "__main__":
    df = tabela()
    alvo = len(_ids_novos())
    print(f"{len(df)} de {alvo} clientes no cache -> {CACHE}")
    if len(df) < alvo:
        print("AVISO: faltaram clientes. Rode de novo; o cache continua de onde parou.")
    print(df.describe().to_string())
