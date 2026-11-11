"""Confere o .env da raiz sem nunca mostrar valores.

    python src/checar_env.py            # nomes, formato e se está protegido pelo .gitignore
    python src/checar_env.py --testar   # também faz uma chamada curta a cada provedor configurado
"""
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENV = RAIZ / ".env"
# nome -> (obrigatório?, prefixo esperado ou None, tamanho mínimo)
ESPERADO = {
    "GROQ_API_KEY": (False, "gsk_", 40), "GOOGLE_API_KEY": (False, None, 30), "OPENROUTER_API_KEY": (False, "sk-or-", 40),
    "NVIDIA_API_KEY": (False, "nvapi-", 40), "ZAI_API_KEY": (False, None, 30), "OMNIROUTE_API_KEY": (False, None, 8),
    "OMNIROUTE_BASE_URL": (False, "http", 10), "FORTUNA_DSN": (False, "postgres", 20), "FORTUNA_BUREAU_TOKEN": (False, None, 20),
}
IA = ["GROQ_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "ZAI_API_KEY", "OMNIROUTE_API_KEY"]


def main():
    ok = True
    if not ENV.exists():
        print(f"ERRO: {ENV} não existe. Copie src/llm.env.example para .env na raiz e preencha.")
        return 1
    protegido = subprocess.run(["git", "check-ignore", "-q", str(ENV)], cwd=RAIZ).returncode == 0
    print(f"{'ok ' if protegido else 'ERRO'} .env ignorado pelo git")
    ok &= protegido
    vistos = {}
    for n, linha in enumerate(ENV.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        if "=" not in linha:
            print(f"ERRO linha {n}: sem '=' (formato é NOME=valor)")
            ok = False
            continue
        nome, valor = (x.strip() for x in linha.split("=", 1))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", nome):
            print(f"ERRO linha {n}: nome '{nome}' inválido (use MAIÚSCULAS_COM_SUBLINHADO)")
            ok = False
        if nome in vistos:
            print(f"AVISO linha {n}: {nome} repetido (vale o primeiro, linha {vistos[nome]})")
        vistos.setdefault(nome, n)
        if nome not in ESPERADO or not valor:
            continue
        _, pref, minimo = ESPERADO[nome]
        probs = []
        if valor[:1] in "\"'":
            probs.append("tem aspas (pode tirar)")
        if " " in valor:
            probs.append("tem espaço: parece ter rótulo junto")
        if pref and not valor.split()[-1].strip("\"'").startswith(pref):
            probs.append(f"não começa com '{pref}': confira se é a chave certa")
        if len(valor) < minimo:
            probs.append("curta demais")
        print(f"{'AVISO' if probs else 'ok   '} {nome}: {'; '.join(probs) if probs else 'formato ok'} (tamanho {len(valor)})")
    ia = [k for k in IA if k in vistos]
    print(f"\nprovedores de IA preenchidos: {', '.join(ia) or 'nenhum'}")
    if not ia:
        print("ERRO: nenhuma chave de IA; o agente não tem com quem falar")
        ok = False
    if "--testar" in sys.argv:
        sys.path.insert(0, str(RAIZ / "src"))
        import llm
        print()
        for cfg, modelo in llm.candidatos():
            if cfg["nome"] == "ollama":
                continue
            try:
                llm.chamar_um(cfg, modelo, [{"role": "user", "content": "Responda só: ok"}], timeout=60)
                print(f"ok    {cfg['nome']}/{modelo}")
            except Exception as e:
                print(f"FALHA {cfg['nome']}/{modelo}: {str(e)[:90]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
