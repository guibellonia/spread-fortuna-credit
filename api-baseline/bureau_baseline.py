"""Baseline da API do bureau: latência, taxa de 503/timeout e determinismo.

Mede a API crua, SEM retry. Usa o .env da raiz (BUREAU_URL, BUREAU_TOKEN, PG*) e sorteia clientes novos do banco.

Uso (da raiz do repositório):
    .venv/Scripts/python api-baseline/bureau_baseline.py [N] [PARALELO]
    .venv/Scripts/python api-baseline/bureau_baseline.py 200 10    # 200 chamadas, 10 em paralelo
    .venv/Scripts/python api-baseline/bureau_baseline.py 100 1     # 100 chamadas, uma por vez

Cada execução gera chamadas registradas no nome do time. Não precisa rodar de novo para o pipeline.
"""
import json
import os
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
URL, TOKEN = os.environ["BUREAU_URL"], os.environ["BUREAU_TOKEN"]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 10
TIMEOUT = 30  # alto de propósito: medir a cauda, não cortar

session = requests.Session()


def call(cid):
    t = time.perf_counter()
    try:
        r = session.get(f"{URL}/v1/bureau/{cid}", headers={"Authorization": f"Bearer {TOKEN}"}, timeout=TIMEOUT)
        return cid, r.status_code, time.perf_counter() - t, r.text if r.status_code == 200 else r.text[:120]
    except requests.Timeout:
        return cid, "timeout", time.perf_counter() - t, ""
    except requests.RequestException as e:
        return cid, type(e).__name__, time.perf_counter() - t, ""


def run(ids):
    with ThreadPoolExecutor(WORKERS) as ex:
        return list(ex.map(call, ids))


def main():
    with psycopg.connect() as c:
        ids = [r[0] for r in c.execute("select id_cliente from hackathon.pedidos where tipo_base='novo' order by id_pedido")]
    random.seed(42)
    sample = random.sample(ids, N)

    t0 = time.perf_counter()
    res = run(sample)
    wall = time.perf_counter() - t0

    ok = [r for r in res if r[1] == 200]
    fail = [r for r in res if r[1] != 200]
    rep_ok = run([r[0] for r in ok[:30]])      # determinismo: a mesma resposta volta?
    rep_fail = run([r[0] for r in fail[:30]])  # a falha é do cliente ou é sorteio?

    lat = sorted(r[2] for r in res)
    q = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))]
    print(f"N={N} paralelo={WORKERS} timeout={TIMEOUT}s tempo={wall:.1f}s vazão={N / wall:.1f} req/s")
    by = {}
    for r in res:
        by.setdefault(str(r[1]), []).append(r[2])
    for k, v in sorted(by.items()):
        print(f"  status {k}: {len(v)} ({len(v) / N:.1%})  latência média {statistics.mean(v):.2f}s  máx {max(v):.2f}s")
    print(f"latência: p50={q(.5):.2f}s p90={q(.9):.2f}s p95={q(.95):.2f}s p99={q(.99):.2f}s máx={lat[-1]:.2f}s")
    for lim in (1, 2, 3, 5, 10):
        print(f"  > {lim}s: {sum(x > lim for x in lat)}")

    first = {r[0]: r[3] for r in ok}
    rep200 = [r for r in rep_ok if r[1] == 200]
    same = sum(json.loads(r[3]) == json.loads(first[r[0]]) for r in rep200)
    print(f"determinismo: {same}/{len(rep200)} respostas repetidas iguais "
          f"({len(rep_ok) - len(rep200)} falhas ao repetir {len(rep_ok)} clientes que tinham respondido)")
    print(f"clientes que falharam, na 2ª tentativa: {sum(r[1] == 200 for r in rep_fail)}/{len(rep_fail)} responderam 200")
    errs = {}
    for r in fail:
        errs[(str(r[1]), r[3])] = errs.get((str(r[1]), r[3]), 0) + 1
    for (st, body), n in errs.items():
        print(f"  erro {st} x{n}: {body!r}")
    if ok:
        sc = [json.loads(r[3]) for r in ok]
        print(f"score min/mediana/max: {min(x['score'] for x in sc)} / {statistics.median(x['score'] for x in sc)} / "
              f"{max(x['score'] for x in sc)} | com restrição: {sum(x['restricoes_ativas'] > 0 for x in sc)} de {len(sc)}")


if __name__ == "__main__":
    main()
