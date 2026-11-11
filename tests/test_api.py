"""API HTTP: autenticação, health e bloqueios, sem banco e sem LLM."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import api


@pytest.fixture()
def servidor(monkeypatch):
    monkeypatch.setenv("HERMES_ACCESS_KEY", "chave-de-teste")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _req(url, metodo="GET", corpo=None, chave=None):
    r = urllib.request.Request(url, method=metodo, data=json.dumps(corpo).encode() if corpo is not None else None,
                               headers={"Content-Type": "application/json", **({"X-Access-Key": chave} if chave else {})})
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_health_reflete_estado(servidor, monkeypatch):
    monkeypatch.setitem(api.ESTADO, "status", "preparando")
    assert _req(servidor + "/health")[0] == 503
    monkeypatch.setitem(api.ESTADO, "status", "ok")
    assert _req(servidor + "/health")[0] == 200


@pytest.mark.parametrize("chave", [None, "errada"])
def test_sem_chave_valida_e_401(servidor, chave):
    assert _req(servidor + "/tools", chave=chave)[0] == 401
    assert _req(servidor + "/perguntar", "POST", {"pergunta": "oi"}, chave=chave)[0] == 401


def test_sem_hermes_access_key_recusa_tudo(servidor, monkeypatch):
    monkeypatch.delenv("HERMES_ACCESS_KEY")
    assert _req(servidor + "/tools", chave="")[0] == 401


def test_api_nao_grava_csv(servidor, monkeypatch):
    monkeypatch.setitem(api.ESTADO, "status", "ok")
    assert _req(servidor + "/tools/gerar_csv", "POST", {"confirmar": True}, chave="chave-de-teste")[0] == 403


def test_pergunta_vazia_e_400(servidor, monkeypatch):
    monkeypatch.setitem(api.ESTADO, "status", "ok")
    assert _req(servidor + "/perguntar", "POST", {"pergunta": " "}, chave="chave-de-teste")[0] == 400


def test_perguntar_usa_o_agente(servidor, monkeypatch):
    import agente
    monkeypatch.setitem(api.ESTADO, "status", "ok")
    monkeypatch.setattr(agente, "perguntar", lambda p, **k: ("resposta de teste", [], [{"tool": "simular_politica"}], "groq/x"))
    code, j = _req(servidor + "/perguntar", "POST", {"pergunta": "quanto ganha?"}, chave="chave-de-teste")
    assert code == 200 and j["resposta"] == "resposta de teste" and j["tools"][0]["tool"] == "simular_politica"
