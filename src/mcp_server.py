"""Servidor MCP (stdio) que expõe as tools determinísticas de src/tools.py para o Hermes Agent ou qualquer cliente MCP.

Sem dependências além das do projeto: implementa o protocolo MCP (JSON-RPC 2.0, uma mensagem por linha) direto.

    python src/mcp_server.py            # o cliente MCP inicia este processo e conversa por stdin/stdout

Guarda-corpo: a tool gerar_csv só grava o arquivo de entrega (confirmar=true) se a variável
SPREAD_PERMITE_GRAVAR=1 estiver definida no ambiente do servidor. Sem ela, o agente só consegue simular.
Logs vão para stderr; stdout é exclusivo do protocolo.
"""
import contextlib
import json
import os
import sys
import traceback

VERSOES = ["2025-06-18", "2025-03-26", "2024-11-05"]
INFO = {"name": "spread-fortuna-tools", "version": "1.0.0"}


def _log(*a):
    print("[mcp]", *a, file=sys.stderr, flush=True)


def _tools():
    with contextlib.redirect_stdout(sys.stderr):  # imports pesados não podem sujar o stdout
        import tools
    return tools


def _lista():
    t = _tools()
    return [{"name": x["function"]["name"], "description": x["function"]["description"],
             "inputSchema": x["function"]["parameters"]} for x in t.TOOLS]


def _chamar(nome, args):
    if nome == "gerar_csv" and (args or {}).get("confirmar") and os.environ.get("SPREAD_PERMITE_GRAVAR") != "1":
        res = {"erro": "gravação bloqueada neste servidor: o analista precisa aprovar e habilitar SPREAD_PERMITE_GRAVAR=1"}
    else:
        t = _tools()
        with contextlib.redirect_stdout(sys.stderr):
            res = t.executar(nome, args or {})
    erro = isinstance(res, dict) and "erro" in res
    return {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False)}], "isError": erro}


def tratar(msg: dict):
    """Processa uma mensagem JSON-RPC. Devolve a resposta (dict) ou None para notificações."""
    metodo, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if mid is None:  # notificação (ex.: notifications/initialized): sem resposta
        return None
    try:
        if metodo == "initialize":
            pedida = params.get("protocolVersion")
            resultado = {"protocolVersion": pedida if pedida in VERSOES else VERSOES[0],
                         "capabilities": {"tools": {"listChanged": False}}, "serverInfo": INFO,
                         "instructions": "Ferramentas determinísticas de risco de crédito da Fortuna. "
                                         "Todo número citado ao analista deve vir de uma destas ferramentas."}
        elif metodo == "ping":
            resultado = {}
        elif metodo == "tools/list":
            resultado = {"tools": _lista()}
        elif metodo == "tools/call":
            resultado = _chamar(params.get("name"), params.get("arguments"))
        else:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"método não suportado: {metodo}"}}
        return {"jsonrpc": "2.0", "id": mid, "result": resultado}
    except Exception as e:
        _log(traceback.format_exc())
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": f"{type(e).__name__}: {e}"}}


def main():
    _log("pronto (stdio)")
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            msg = json.loads(linha)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON inválido"}}
        else:
            resp = tratar(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
