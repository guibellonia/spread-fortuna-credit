"""Cliente da API do bureau: retry com backoff em 503/timeout, cache em disco e chamadas em paralelo."""
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

URL = os.environ.get("FORTUNA_BUREAU_URL", "https://gowlab-fortuna-bureau.azurewebsites.net")
CACHE = Path(__file__).resolve().parents[1] / "saida" / "bureau_cache.json"
CAMPOS = ["score", "restricoes_ativas", "parcelas_outras_instituicoes", "consultas_90_dias", "meses_historico_bureau"]
_lock = threading.Lock()


class ErroBureau(Exception):
    pass


class TokenInvalido(ErroBureau):
    pass


def _token():
    t = os.environ.get("FORTUNA_BUREAU_TOKEN")
    if not t:
        raise TokenInvalido("defina a variável de ambiente FORTUNA_BUREAU_TOKEN com o token do time")
    return t


def saude() -> bool:
    try:
        return requests.get(f"{URL}/health", timeout=10).status_code == 200
    except requests.RequestException:
        return False


def consultar(id_cliente: str, sessao=None, tentativas=8, timeout=15) -> dict:
    s = sessao or requests
    headers = {"Authorization": f"Bearer {_token()}"}
    for n in range(tentativas):
        try:
            r = s.get(f"{URL}/v1/bureau/{id_cliente}", headers=headers, timeout=timeout)
        except requests.RequestException:
            r = None  # timeout ou conexão: tenta de novo
        if r is not None:
            if r.status_code == 200:
                d = r.json()
                faltando = [c for c in CAMPOS if c not in d]
                if faltando:
                    raise ErroBureau(f"{id_cliente}: resposta sem {faltando}")
                return {"id_cliente": id_cliente, **{c: d[c] for c in CAMPOS}}
            if r.status_code == 401:
                raise TokenInvalido("401: token ausente ou inválido")
            if r.status_code == 404:
                raise ErroBureau(f"404: {id_cliente} não pertence à base de novos pedidos")
        time.sleep(min(20, 0.5 * 2 ** n) + random.random())  # backoff exponencial com jitter
    raise ErroBureau(f"{id_cliente}: sem resposta após {tentativas} tentativas")


def _ler_cache():
    return json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}


def _salvar_cache(c):
    CACHE.parent.mkdir(exist_ok=True)
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CACHE)


def consultar_lote(ids, paralelo=16, log=print) -> dict:
    """Consulta todos os ids, reaproveitando o cache (a resposta de um cliente não muda)."""
    cache = _ler_cache()
    pendentes = [i for i in ids if i not in cache]
    log(f"bureau: {len(ids) - len(pendentes)} em cache, {len(pendentes)} a consultar")
    falhas = {}
    with requests.Session() as sessao, ThreadPoolExecutor(paralelo) as ex:
        futuros = {ex.submit(consultar, i, sessao): i for i in pendentes}
        for k, f in enumerate(as_completed(futuros), 1):
            i = futuros[f]
            try:
                res = f.result()
                with _lock:
                    cache[i] = res
            except TokenInvalido:
                _salvar_cache(cache)
                raise
            except ErroBureau as e:
                falhas[i] = str(e)
            if k % 100 == 0:
                with _lock:
                    _salvar_cache(cache)
                log(f"bureau: {k}/{len(pendentes)}")
    _salvar_cache(cache)
    if falhas:
        log(f"bureau: {len(falhas)} falhas; rode de novo para tentar só essas. Ex.: {list(falhas.items())[:3]}")
    return {i: cache[i] for i in ids if i in cache}
