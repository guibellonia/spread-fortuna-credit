"""API HTTP do Hermes: o agente LLM e as tools determinísticas atrás de uma chave de acesso.

    GET  /health                    sem chave: {"status": "ok"|"preparando"|"erro", ...}
    POST /perguntar                 {"pergunta": "..."} -> resposta do agente, modelo usado e tools chamadas
    POST /tools/<nome>              argumentos da tool no corpo (JSON) -> resultado da tool, sem LLM
    GET  /tools                     lista das tools

Autenticação: cabeçalho "X-Access-Key: <HERMES_ACCESS_KEY>". Sem HERMES_ACCESS_KEY definida, a API recusa tudo
(menos /health): ninguém de fora gasta as cotas de IA. Porta: variável PORT (Railway define), padrão 8080.
Sem dependências além das do projeto (http.server da biblioteca padrão).
"""
import hmac
import json
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ESTADO = {"status": "preparando", "detalhe": "carregando base e modelos"}
TRAVA_AGENTE = threading.Semaphore(int(os.environ.get("HERMES_CONCORRENCIA", "2")))
MAX_CORPO = 64 * 1024


def preparar():
    """Monta a base (hist/novos), aquece as tools e o conselho. Roda em segundo plano no start."""
    try:
        import bootstrap
        bootstrap.garantir_base()
        import tools
        tools.politica_vigente()
        ESTADO.update(status="ok", detalhe="pronto")
    except Exception as e:
        traceback.print_exc()
        ESTADO.update(status="erro", detalhe=f"{type(e).__name__}: {e}"[:300])


class Handler(BaseHTTPRequestHandler):
    server_version = "spread-hermes/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[api] " + fmt % args + "\n")

    def _json(self, code, corpo):
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def _autorizado(self):
        chave = os.environ.get("HERMES_ACCESS_KEY", "")
        enviada = self.headers.get("X-Access-Key", "")
        return bool(chave) and hmac.compare_digest(chave, enviada)

    def _corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_CORPO:
            raise ValueError("corpo grande demais")
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        if self.path == "/health":
            return self._json(200 if ESTADO["status"] == "ok" else 503, ESTADO)
        if not self._autorizado():
            return self._json(401, {"erro": "X-Access-Key ausente ou inválida"})
        if self.path == "/tools":
            from tools import TOOLS
            return self._json(200, {"tools": [t["function"]["name"] for t in TOOLS]})
        return self._json(404, {"erro": "rota não existe"})

    def do_POST(self):
        if not self._autorizado():
            return self._json(401, {"erro": "X-Access-Key ausente ou inválida"})
        if ESTADO["status"] != "ok":
            return self._json(503, ESTADO)
        try:
            corpo = self._corpo()
        except Exception as e:
            return self._json(400, {"erro": f"JSON inválido: {e}"})
        if self.path == "/perguntar":
            pergunta = str(corpo.get("pergunta", "")).strip()
            if not pergunta or len(pergunta) > 2000:
                return self._json(400, {"erro": "envie 'pergunta' com até 2.000 caracteres"})
            if not TRAVA_AGENTE.acquire(timeout=60):
                return self._json(429, {"erro": "agente ocupado, tente de novo"})
            try:
                import agente
                resp, _, chamadas, quem = agente.perguntar(pergunta, log=lambda *a: None, sessao="api")
                return self._json(200, {"resposta": resp, "modelo": quem, "tools": chamadas})
            except Exception as e:
                return self._json(502, {"erro": f"{type(e).__name__}: {e}"[:300]})
            finally:
                TRAVA_AGENTE.release()
        if self.path.startswith("/tools/"):
            nome = self.path.split("/", 2)[2]
            if nome == "gerar_csv" and corpo.get("confirmar"):
                return self._json(403, {"erro": "gravação do CSV de entrega não é permitida pela API"})
            from tools import executar
            res = executar(nome, corpo)
            return self._json(400 if isinstance(res, dict) and "erro" in res else 200, res)
        return self._json(404, {"erro": "rota não existe"})


def main():
    porta = int(os.environ.get("PORT", "8080"))
    if not os.environ.get("HERMES_ACCESS_KEY"):
        print("[api] AVISO: HERMES_ACCESS_KEY não definida; só /health responde", file=sys.stderr)
    threading.Thread(target=preparar, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", porta), Handler)
    print(f"[api] ouvindo na porta {porta}", file=sys.stderr, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
