"""Cliente da API do bureau com retry, espera crescente com variação aleatória e cache em disco.

Configuração tirada de api-baseline/baseline-agregado.md:
- timeout de 10s (o dobro da resposta mais lenta medida);
- nova tentativa só em 503, timeout e erro de rede, até 6 tentativas, esperando 0,5s, 1s, 2s, 4s... com jitter;
- 401 interrompe tudo (token errado não melhora tentando de novo); 404 e outros 4xx falham só aquele cliente;
- cache por id_cliente em data/cache/bureau/ (a resposta de um cliente não muda; a pasta está no .gitignore).

O token vem só do ambiente (BUREAU_TOKEN no .env da raiz). Nunca é gravado em arquivo nem impresso.
"""
from __future__ import annotations

import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "bureau"
LOG = ROOT / "data" / "cache" / "bureau_chamadas.jsonl"  # uma linha por chamada feita à API (evidência de falha tratada)
CAMPOS = ("score", "restricoes_ativas", "parcelas_outras_instituicoes", "consultas_90_dias", "meses_historico_bureau")

TIMEOUT = 10
MAX_TENTATIVAS = 6
ESPERA_BASE = 0.5
PARALELO = 10


class TokenInvalido(RuntimeError):
    pass


@dataclass
class Consulta:
    id_cliente: str
    dados: dict | None = None
    origem: str = "api"            # "api" ou "cache"
    tentativas: list = field(default_factory=list)  # [(status, segundos)] de cada chamada feita
    erro: str | None = None


def _valida(dados: dict, id_cliente: str) -> dict:
    if dados.get("id_cliente") != id_cliente:
        raise ValueError("resposta de outro cliente")
    for c in CAMPOS:
        if not isinstance(dados.get(c), (int, float)):
            raise ValueError(f"campo {c} ausente ou não numérico")
    return {c: dados[c] for c in ("id_cliente", *CAMPOS)}


class Bureau:
    def __init__(self, url: str | None = None, token: str | None = None):
        self.url = (url or os.environ.get("BUREAU_URL", "")).rstrip("/")
        self._token = token or os.environ.get("BUREAU_TOKEN") or os.environ.get("FORTUNA_BUREAU_TOKEN")
        if not self.url.startswith("https://"):
            raise SystemExit("BUREAU_URL precisa ser https:// (veja .env.example)")
        self._sessao = requests.Session()
        self._parar = False
        self._trava = threading.Lock()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _registra(self, id_cliente: str, tentativa: int, status, segundos: float):
        linha = json.dumps({"em": time.strftime("%Y-%m-%dT%H:%M:%S"), "id_cliente": id_cliente,
                            "tentativa": tentativa, "status": status, "segundos": segundos})
        with self._trava, LOG.open("a", encoding="utf-8") as f:
            f.write(linha + "\n")

    def _cache(self, id_cliente: str) -> Path:
        if not id_cliente.replace("-", "").isalnum():
            raise ValueError("id_cliente inesperado")
        return CACHE_DIR / f"{id_cliente}.json"

    def consultar(self, id_cliente: str) -> Consulta:
        cons = Consulta(id_cliente)
        arq = self._cache(id_cliente)
        if arq.exists():
            cons.dados, cons.origem = json.loads(arq.read_text(encoding="utf-8")), "cache"
            return cons
        if not self._token:
            raise TokenInvalido("BUREAU_TOKEN não definido no .env")
        for n in range(MAX_TENTATIVAS):
            if self._parar:
                cons.erro = "interrompido"
                return cons
            t = time.perf_counter()
            try:
                r = self._sessao.get(f"{self.url}/v1/bureau/{id_cliente}",
                                     headers={"Authorization": f"Bearer {self._token}"}, timeout=TIMEOUT)
                status = r.status_code
            except requests.Timeout:
                status = "timeout"
            except requests.RequestException as e:
                status = type(e).__name__
            seg = round(time.perf_counter() - t, 3)
            cons.tentativas.append((status, seg))
            self._registra(id_cliente, n + 1, status, seg)
            if status == 200:
                try:
                    cons.dados = _valida(r.json(), id_cliente)
                except ValueError as e:
                    cons.erro = f"resposta inválida: {e}"
                    return cons
                arq.write_text(json.dumps(cons.dados), encoding="utf-8")
                return cons
            if status == 401:
                self._parar = True
                raise TokenInvalido("401: token ausente ou inválido")
            if isinstance(status, int) and status != 503:
                cons.erro = f"HTTP {status}"
                return cons
            if n < MAX_TENTATIVAS - 1:
                time.sleep(ESPERA_BASE * 2 ** n * random.uniform(0.75, 1.25))
        cons.erro = f"sem resposta após {MAX_TENTATIVAS} tentativas"
        return cons

    def consultar_varios(self, ids: list[str], paralelo: int = PARALELO) -> list[Consulta]:
        with ThreadPoolExecutor(paralelo) as ex:
            return list(ex.map(self.consultar, ids))


if __name__ == "__main__":
    import sys

    import psycopg
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    with psycopg.connect() as c:
        ids = [r[0] for r in c.execute("select id_cliente from hackathon.pedidos where tipo_base='novo' order by id_pedido")]
    t0 = time.perf_counter()
    res = Bureau().consultar_varios(ids)
    ok = sum(r.dados is not None for r in res)
    chamadas = sum(len(r.tentativas) for r in res)
    print(f"{ok}/{len(ids)} clientes com bureau · {chamadas} chamadas à API · {time.perf_counter() - t0:.0f}s", file=sys.stderr)
    for r in res:
        if r.erro:
            print(f"  falhou: {r.id_cliente} · {r.erro}", file=sys.stderr)
