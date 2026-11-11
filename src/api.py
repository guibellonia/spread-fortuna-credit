"""API HTTP do Hermes: o agente LLM e as tools determinísticas atrás de uma chave de acesso.

    GET  / ou /chat                 sem chave: página de chat (a chave é digitada nela)
    GET  /health                    sem chave: {"status": "ok"|"preparando"|"erro", ...}
    POST /perguntar                 sem chave no modo público (com limites); {"pergunta": "..."} -> resposta do agente, modelo usado e tools chamadas
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
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ESTADO = {"status": "preparando", "detalhe": "carregando base e modelos"}
TRAVA_AGENTE = threading.Semaphore(int(os.environ.get("HERMES_CONCORRENCIA", "2")))
MAX_CORPO = 64 * 1024
CHAT_HTML = Path(__file__).resolve().parent / "chat.html"
SITE_DO_TIME = os.environ.get("HERMES_SITE_ORIGEM", "https://guibellonia.github.io")
# Modo público (desligado por padrão): /perguntar sem chave, com limites. Em uso normal, o acesso é por:
#   - chave do time (X-Access-Key), ou
#   - login de membro do time no painel: o ícone de chat repassa o token do Supabase (Authorization: Bearer ...)
#     e o Hermes confere com painel.eh_membro() no Supabase (mesma lista de membros do painel de revisão).
PUBLICO = os.environ.get("HERMES_PUBLICO", "0") == "1"
SUPABASE_URL = os.environ.get("HERMES_SUPABASE_URL", "https://vjxwagiqgecsscoogxln.supabase.co")
# chave anon é pública por desenho (já está em site/site.config.json); quem protege é o RLS + eh_membro()
SUPABASE_ANON = os.environ.get(
    "HERMES_SUPABASE_ANON",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZqeHdhZ2lxZ2Vjc3Njb29neGxuIiwicm9sZSI6ImFub24i"
    "LCJpYXQiOjE3OTQ0MDI0NzYsImV4cCI6MjEwOTk3ODQ3Nn0.h-DifBlWRtYa3QkChzlqPN_mfCVhOo_EMcGDOsVNoOw")
_MEMBROS_CACHE: dict = {}  # token -> (é membro?, válido até)


def membro_do_time(token: str) -> bool:
    """True se o token de login do Supabase é de alguém em painel.membros. Cache de 5 min por token."""
    if not token or len(token) > 4096:
        return False
    agora = time.time()
    em_cache = _MEMBROS_CACHE.get(token)
    if em_cache and em_cache[1] > agora:
        return em_cache[0]
    try:
        import requests
        r = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/eh_membro", json={}, timeout=10,
                          headers={"apikey": SUPABASE_ANON, "Authorization": f"Bearer {token}",
                                   "Content-Profile": "painel", "Accept-Profile": "painel"})
        ok = r.status_code == 200 and r.json() is True
    except Exception:
        ok = False
    if len(_MEMBROS_CACHE) > 1000:
        _MEMBROS_CACHE.clear()
    _MEMBROS_CACHE[token] = (ok, agora + (300 if ok else 30))
    return ok


class Limite:
    """Limites do modo público: por IP numa janela deslizante e um teto diário para todos."""

    def __init__(self, por_ip=10, janela_s=600, por_dia=300):
        self.por_ip, self.janela, self.por_dia = por_ip, janela_s, por_dia
        self.hist, self.dia, self.total = {}, None, 0
        self.trava = threading.Lock()

    def permitir(self, ip, agora=None):
        agora = agora or time.time()
        hoje = time.strftime("%Y-%m-%d", time.gmtime(agora))
        with self.trava:
            if hoje != self.dia:
                self.dia, self.total, self.hist = hoje, 0, {}
            if self.total >= self.por_dia:
                return False, "limite diário de perguntas atingido; tente amanhã"
            fila = [t for t in self.hist.get(ip, []) if agora - t < self.janela]
            if len(fila) >= self.por_ip:
                espera = int(self.janela - (agora - fila[0])) + 1
                return False, f"muitas perguntas seguidas; tente de novo em {espera // 60 + 1} min"
            fila.append(agora)
            self.hist[ip] = fila
            self.total += 1
            return True, ""


LIMITE = Limite(int(os.environ.get("HERMES_LIMITE_IP", "10")), 600, int(os.environ.get("HERMES_LIMITE_DIA", "300")))


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
        if chave and enviada and hmac.compare_digest(chave, enviada):
            return True
        auth = self.headers.get("Authorization", "")
        return auth.startswith("Bearer ") and membro_do_time(auth[7:].strip())

    def _ip(self):
        # atrás do proxy do Railway o IP real vem no X-Forwarded-For (o primeiro da lista)
        xff = self.headers.get("X-Forwarded-For", "")
        return xff.split(",")[0].strip() if xff else self.client_address[0]

    def _corpo(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_CORPO:
            raise ValueError("corpo grande demais")
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def _pagina_chat(self):
        dados = CHAT_HTML.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        # só a própria página e o site do time podem embutir o chat (iframe)
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                         f"connect-src 'self'; frame-ancestors {SITE_DO_TIME}")
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path in ("/", "/chat"):
            return self._pagina_chat()
        if self.path == "/health":
            return self._json(200 if ESTADO["status"] == "ok" else 503, ESTADO)
        if not self._autorizado():
            return self._json(401, {"erro": "X-Access-Key ausente ou inválida"})
        if self.path == "/tools":
            from tools import TOOLS
            return self._json(200, {"tools": [t["function"]["name"] for t in TOOLS]})
        return self._json(404, {"erro": "rota não existe"})

    def do_POST(self):
        time_do_time = self._autorizado()
        publico_ok = PUBLICO and self.path == "/perguntar"
        if not time_do_time and not publico_ok:
            return self._json(401, {"erro": "entre no painel do time (aba Revisão) para usar o Hermes"})
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
            if not time_do_time:
                ok, motivo = LIMITE.permitir(self._ip())
                if not ok:
                    return self._json(429, {"erro": motivo})
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
