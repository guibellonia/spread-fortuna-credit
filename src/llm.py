"""Cliente LLM multi-provedor com fallback. Todos falam o protocolo OpenAI (/chat/completions + tools).

Duas camadas de fallback:
  1. OmniRoute (principal): o roteador do time já faz o fallback entre modelos/provedores configurados nele.
  2. Este módulo (rede de segurança): se o próprio OmniRoute cair, chama os provedores direto, na ordem abaixo.

Ordem padrão (o primeiro com chave configurada e respondendo vence):
  omniroute (Hermes) -> groq -> google (Gemini) -> openrouter (free) -> nvidia (NIM) -> zai (GLM) -> ollama (local)

Configuração só por variável de ambiente (nunca no código, nunca no git):
  <PROVEDOR>_API_KEY      chave (ollama não precisa)
  <PROVEDOR>_BASE_URL     sobrescreve o endereço
  <PROVEDOR>_MODELS       lista separada por vírgula; sobrescreve os modelos padrão
  LLM_ORDEM               ex.: "omniroute,zai,google"  (sobrescreve a ordem)
  LLM_TIMEOUT             segundos por chamada (padrão 90)

Os ids de modelo padrão abaixo são palpites razoáveis: CONFIRA no painel de cada provedor e ajuste via <PROVEDOR>_MODELS.
"""
import json
import os
import time

import requests

try:  # lê o .env da raiz do repositório (fora do Git), sem sobrescrever variáveis já definidas
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=False)
except ImportError:
    pass

PROVEDORES = {  # ids testados em 11/11/2026 com chamada de ferramenta; a ordem é a de preferência
    "omniroute": {"base_url": "", "models": ["hermes"], "precisa_chave": True},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "models": ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"],
             "precisa_chave": True},
    "google": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
               "models": ["gemini-3.5-flash", "gemini-3.5-flash-lite"], "precisa_chave": True},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "models": ["openrouter/free"], "precisa_chave": True},
    "nvidia": {"base_url": "https://integrate.api.nvidia.com/v1", "models": ["minimaxai/minimax-m3.1-flash"],
               "precisa_chave": True},
    "zai": {"base_url": "https://api.z.ai/api/paas/v4", "models": ["glm-4.5-flash"], "precisa_chave": True},
    "ollama": {"base_url": "http://localhost:11434/v1", "models": ["llama3.1"], "precisa_chave": False},
}
ORDEM_PADRAO = list(PROVEDORES)


def limpar_chave(v: str) -> str:
    """Tolera os erros comuns ao colar chave: aspas, espaços, quebra de linha, 'Bearer ' e rótulo antes da chave
    (ex.: "groq gsk_..."). Fica com o último pedaço sem espaço."""
    v = (v or "").strip().strip('"').strip("'").strip()
    if v.lower().startswith("bearer "):
        v = v[7:]
    return v.split()[-1] if v.split() else ""


class SemProvedor(Exception):
    pass


def _cfg(nome):
    base = PROVEDORES[nome]
    pre = nome.upper()
    return {
        "nome": nome,
        "base_url": (os.environ.get(f"{pre}_BASE_URL") or base["base_url"]).rstrip("/"),
        "chave": limpar_chave(os.environ.get(f"{pre}_API_KEY", "")),
        "models": [m.strip() for m in os.environ.get(f"{pre}_MODELS", "").split(",") if m.strip()] or base["models"],
        "precisa_chave": base["precisa_chave"],
    }


def candidatos(ordem=None):
    """Lista (provedor, modelo) configurados, na ordem de preferência."""
    ordem = ordem or [o.strip() for o in os.environ.get("LLM_ORDEM", "").split(",") if o.strip()] or ORDEM_PADRAO
    out = []
    for nome in ordem:
        if nome not in PROVEDORES:
            continue
        c = _cfg(nome)
        if not c["base_url"] or (c["precisa_chave"] and not c["chave"]):
            continue
        out += [(c, m) for m in c["models"]]
    return out


def status():
    """Quais provedores estão configurados (sem expor chaves)."""
    return [{"provedor": n, "configurado": bool(_cfg(n)["base_url"]) and (bool(_cfg(n)["chave"]) or not PROVEDORES[n]["precisa_chave"]),
             "modelos": _cfg(n)["models"]} for n in PROVEDORES]


def chamar_um(cfg, modelo, mensagens, tools=None, temperatura=0.2, timeout=None):
    url = f"{cfg['base_url']}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg["chave"]:
        headers["Authorization"] = f"Bearer {cfg['chave']}"
    corpo = {"model": modelo, "messages": mensagens, "temperature": temperatura}
    if tools:
        corpo["tools"] = tools
        corpo["tool_choice"] = "auto"
    r = requests.post(url, headers=headers, json=corpo, timeout=timeout or float(os.environ.get("LLM_TIMEOUT", 90)))
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    msg = r.json()["choices"][0]["message"]
    return msg


def chamar(mensagens, tools=None, ordem=None, fixo=None, preferido=None, log=print, **kw):
    """Tenta cada (provedor, modelo) até um responder. `fixo` = (cfg, modelo) sem fallback (usado no conselho);
    `preferido` = tenta primeiro esse e, se falhar, segue a ordem normal. Devolve (mensagem, provedor, modelo)."""
    if fixo:
        lista = [fixo]
    else:
        lista = candidatos(ordem)
        if preferido:
            lista = [preferido] + [c for c in lista if (c[0]["nome"], c[1]) != (preferido[0]["nome"], preferido[1])]
    if not lista:
        raise SemProvedor("nenhum provedor configurado: defina ao menos uma <PROVEDOR>_API_KEY (ver src/llm.py)")
    erros = []
    for cfg, modelo in lista:
        for tentativa in range(2):  # 2 tentativas por modelo (429/5xx passageiros)
            try:
                t = time.time()
                msg = chamar_um(cfg, modelo, mensagens, tools, **kw)
                log(f"[llm] {cfg['nome']}/{modelo} ok em {time.time() - t:.1f}s")
                return msg, cfg["nome"], modelo
            except Exception as e:
                erro = str(e)
                erros.append(f"{cfg['nome']}/{modelo}: {erro[:120]}")
                if "HTTP 4" in erro and "HTTP 429" not in erro:
                    break  # 400/401/404: não adianta repetir este modelo
                time.sleep(1.5 * (tentativa + 1))
        log(f"[llm] {cfg['nome']}/{modelo} falhou, indo para o próximo")
    raise SemProvedor("todos os provedores falharam: " + " | ".join(erros))


if __name__ == "__main__":
    print(json.dumps(status(), ensure_ascii=False, indent=2))
