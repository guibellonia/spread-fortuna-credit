"""Servidor MCP: protocolo e guarda-corpo, sem banco."""
import json

import mcp_server


def _req(metodo, params=None, mid=1):
    return mcp_server.tratar({"jsonrpc": "2.0", "id": mid, "method": metodo, "params": params or {}})


def test_initialize_negocia_versao():
    r = _req("initialize", {"protocolVersion": "2024-11-05"})["result"]
    assert r["protocolVersion"] == "2024-11-05" and "tools" in r["capabilities"]
    assert _req("initialize", {"protocolVersion": "1999-01-01"})["result"]["protocolVersion"] == mcp_server.VERSOES[0]


def test_notificacao_nao_tem_resposta():
    assert mcp_server.tratar({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_tools_list_expoe_todas_com_schema():
    from tools import TOOLS
    lista = _req("tools/list")["result"]["tools"]
    assert len(lista) == len(TOOLS)
    for t in lista:
        assert t["name"] and t["description"] and t["inputSchema"]["type"] == "object"
    json.dumps(lista)


def test_gerar_csv_bloqueado_sem_permissao(monkeypatch):
    monkeypatch.delenv("SPREAD_PERMITE_GRAVAR", raising=False)
    r = _req("tools/call", {"name": "gerar_csv", "arguments": {"confirmar": True}})["result"]
    assert r["isError"] and "bloqueada" in r["content"][0]["text"]


def test_tool_inexistente_vira_erro_de_tool():
    r = _req("tools/call", {"name": "nao_existe", "arguments": {}})["result"]
    assert r["isError"]


def test_metodo_desconhecido():
    assert _req("recursos/qualquer")["error"]["code"] == -32601
