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
def test_sem_chave_valida_e_401(servidor, chave, monkeypatch):
    assert _req(servidor + "/tools", chave=chave)[0] == 401
    assert _req(servidor + "/tools/decidir_pedido", "POST", {"id_pedido": "P-1"}, chave=chave)[0] == 401
    monkeypatch.setattr(api, "PUBLICO", False)
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


def test_pagina_de_chat_sem_chave_e_sem_segredo(servidor):
    with urllib.request.urlopen(servidor + "/") as r:
        html = r.read().decode("utf-8")
        assert r.status == 200 and "text/html" in r.headers["Content-Type"]
        assert "frame-ancestors" in r.headers["Content-Security-Policy"]
    assert "Hermes" in html and "chave-de-teste" not in html


def test_modo_publico_responde_sem_chave_e_limita(servidor, monkeypatch):
    import agente
    monkeypatch.setitem(api.ESTADO, "status", "ok")
    monkeypatch.setattr(api, "PUBLICO", True)
    monkeypatch.setattr(api, "LIMITE", api.Limite(por_ip=2, janela_s=600, por_dia=100))
    monkeypatch.setattr(agente, "perguntar", lambda p, **k: ("ok", [], [], "groq/x"))
    assert _req(servidor + "/perguntar", "POST", {"pergunta": "a"})[0] == 200
    assert _req(servidor + "/perguntar", "POST", {"pergunta": "b"})[0] == 200
    code, j = _req(servidor + "/perguntar", "POST", {"pergunta": "c"})
    assert code == 429 and "tente de novo" in j["erro"]
    # com a chave do time não há limite
    assert _req(servidor + "/perguntar", "POST", {"pergunta": "d"}, chave="chave-de-teste")[0] == 200


def test_limite_diario_e_janela():
    lim = api.Limite(por_ip=1, janela_s=60, por_dia=2)
    assert lim.permitir("1.1.1.1", 1000)[0]
    assert not lim.permitir("1.1.1.1", 1010)[0]          # mesmo IP dentro da janela
    assert lim.permitir("2.2.2.2", 1010)[0]              # outro IP
    ok, motivo = lim.permitir("3.3.3.3", 1020)
    assert not ok and "diário" in motivo                 # teto do dia
    assert lim.permitir("3.3.3.3", 1020 + 86400)[0]      # dia seguinte zera


def test_login_de_membro_do_painel_libera(servidor, monkeypatch):
    import agente
    monkeypatch.setitem(api.ESTADO, "status", "ok")
    monkeypatch.setattr(api, "PUBLICO", False)
    monkeypatch.setattr(api, "membro_do_time", lambda t: t == "token-de-membro")
    monkeypatch.setattr(agente, "perguntar", lambda p, **k: ("ok", [], [], "groq/x"))

    def com_token(t):
        r = urllib.request.Request(servidor + "/perguntar", method="POST", data=b'{"pergunta":"oi"}',
                                   headers={"Content-Type": "application/json", "Authorization": f"Bearer {t}"})
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code
    assert com_token("token-de-membro") == 200
    assert com_token("token-de-outro") == 401
    assert _req(servidor + "/perguntar", "POST", {"pergunta": "oi"})[0] == 401   # sem nada


def test_publico_desligado_por_padrao():
    assert api.PUBLICO is False or __import__("os").environ.get("HERMES_PUBLICO") == "1"


def test_membro_do_time_rejeita_vazio_sem_rede():
    assert api.membro_do_time("") is False
