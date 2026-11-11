"""Agente de risco (Hermes e demais LLMs) sobre as tools determinísticas, e conselho de LLMs.

    python agente.py "o score importa depois dos filtros?"          # uma pergunta, com fallback de provedor
    python agente.py --chat                                         # conversa no terminal
    python agente.py --conselho "devo subir o teto de parcela para 30%?"   # vários modelos + presidente
    python agente.py --status                                       # provedores configurados

Regras do agente: todo número vem de uma tool; gerar_csv com confirmar=true exige "aprovo" digitado por uma pessoa.
Cada chamada de tool fica em saida/agente_log.jsonl (auditoria para a banca).
"""
import argparse
import json
import sys
import time
from datetime import datetime

import llm
from modelo import SAIDA
from tools import TOOLS, executar

SISTEMA = """Você é o assistente de risco de crédito da Fortuna, trabalhando com um analista humano.
Regras:
1. TODO número que você citar precisa vir de uma ferramenta chamada nesta conversa. Nunca estime, arredonde de cabeça ou invente.
2. Para testar uma hipótese de padrão, use medir_grupo. Para avaliar uma mudança de política, use simular_politica ou comparar_politicas e cite também o cenário pessimista.
3. Você recomenda; quem decide é o analista. Nunca chame gerar_csv com confirmar=true sem o analista ter escrito "aprovo".
4. Responda em português do Brasil, curto, em linguagem de negócio, dizendo de qual ferramenta veio cada número.
5. Se uma ferramenta devolver erro, corrija os argumentos e tente de novo.
6. Não use gênero, estado civil, CEP ou idade como critério de decisão."""

LOG = SAIDA / "agente_log.jsonl"
MAX_RODADAS = 8


def _registrar(evento):
    SAIDA.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), **evento}, ensure_ascii=False) + "\n")


def _guarda(nome, args, interativo):
    """Bloqueia a gravação do CSV de entrega sem aprovação humana explícita."""
    if nome == "gerar_csv" and args.get("confirmar"):
        if not interativo:
            return {"erro": "gravação bloqueada: só com aprovação humana no modo --chat"}
        resp = input("\n>>> O agente quer GRAVAR o spread_final.csv. Digite 'aprovo' para permitir: ").strip().lower()
        if resp != "aprovo":
            return {"erro": "o analista não aprovou a gravação"}
    return None


def perguntar(pergunta, historico=None, fixo=None, interativo=False, log=print, sessao="cli"):
    """Roda o loop de tool calling. Devolve (resposta, historico, chamadas, provedor/modelo)."""
    msgs = historico or [{"role": "system", "content": SISTEMA}]
    msgs.append({"role": "user", "content": pergunta})
    chamadas, quem = [], None
    for _ in range(MAX_RODADAS):
        msg, prov, modelo = llm.chamar(msgs, tools=TOOLS, fixo=fixo, log=log)
        quem = f"{prov}/{modelo}"
        if fixo is None:  # depois que um provedor respondeu, a conversa segue nele (mantém o contexto coerente)
            fixo = next(((c, m) for c, m in llm.candidatos() if c["nome"] == prov and m == modelo), None)
        tcs = msg.get("tool_calls") or []
        msgs.append({"role": "assistant", "content": msg.get("content") or "", **({"tool_calls": tcs} if tcs else {})})
        if not tcs:
            _registrar({"sessao": sessao, "modelo": quem, "pergunta": pergunta, "resposta": msg.get("content")})
            return msg.get("content") or "", msgs, chamadas, quem
        for tc in tcs:
            nome = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            res = _guarda(nome, args, interativo) or executar(nome, args)
            chamadas.append({"tool": nome, "args": args})
            _registrar({"sessao": sessao, "modelo": quem, "tool": nome, "args": args,
                        "resultado": json.dumps(res, ensure_ascii=False)[:2000]})
            log(f"[tool] {nome}({json.dumps(args, ensure_ascii=False)[:120]})")
            msgs.append({"role": "tool", "tool_call_id": tc.get("id", nome), "name": nome,
                         "content": json.dumps(res, ensure_ascii=False)[:12000]})
    return "Limite de rodadas atingido sem resposta final.", msgs, chamadas, quem


def conselho(pergunta, max_membros=4, log=print):
    """Cada modelo disponível (um por provedor) responde sozinho, com as tools; um presidente consolida."""
    import os
    vistos, membros = set(), []
    fixos = [m.strip() for m in os.environ.get("CONSELHO_MODELOS", "").split(",") if m.strip()]
    if fixos:  # ex.: "omniroute:hermes,omniroute:glm-4.6,omniroute:gemini-2.5-flash" (todos via OmniRoute)
        for item in fixos:
            prov, _, modelo = item.partition(":")
            cfg = llm._cfg(prov)
            if cfg["base_url"] and (cfg["chave"] or not cfg["precisa_chave"]):
                membros.append((cfg, modelo))
    else:  # sem lista: um modelo por provedor configurado
        for cfg, modelo in llm.candidatos():
            if cfg["nome"] not in vistos:
                vistos.add(cfg["nome"])
                membros.append((cfg, modelo))
    membros = membros[:max_membros]
    if not membros:
        raise llm.SemProvedor("nenhum provedor configurado")
    sessao = f"conselho-{int(time.time())}"
    votos = []
    for cfg, modelo in membros:
        log(f"\n== membro {cfg['nome']}/{modelo} ==")
        try:
            resp, _, ch, quem = perguntar(pergunta, fixo=(cfg, modelo), log=log, sessao=sessao)
            votos.append({"membro": quem, "resposta": resp, "tools": [c["tool"] for c in ch]})
        except Exception as e:
            votos.append({"membro": f"{cfg['nome']}/{modelo}", "erro": str(e)[:200]})
    validos = [v for v in votos if "resposta" in v]
    if not validos:
        return {"pergunta": pergunta, "votos": votos, "sintese": "nenhum membro respondeu"}
    pauta = "\n\n".join(f"### {v['membro']} (tools: {', '.join(v['tools']) or 'nenhuma'})\n{v['resposta']}" for v in validos)
    pedido = (f"Pergunta ao conselho: {pergunta}\n\nRespostas dos membros:\n{pauta}\n\n"
              "Como presidente do conselho: 1) liste os pontos de CONSENSO; 2) liste as DIVERGÊNCIAS e qual membro "
              "defende o quê; 3) confira os números que divergem chamando as ferramentas; 4) dê a recomendação final "
              "ao analista e o grau de concordância (unânime, maioria, dividido). Membro que citou número sem ter chamado "
              "ferramenta deve ser apontado.")
    log("\n== presidente ==")
    sintese, _, _, presidente = perguntar(pedido, log=log, sessao=sessao)
    out = {"pergunta": pergunta, "votos": votos, "presidente": presidente, "sintese": sintese}
    _registrar({"sessao": sessao, "conselho": out})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pergunta", nargs="?")
    ap.add_argument("--chat", action="store_true")
    ap.add_argument("--conselho", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status:
        print(json.dumps(llm.status(), ensure_ascii=False, indent=2))
        return
    if a.conselho:
        r = conselho(a.pergunta)
        print("\n" + "=" * 70 + "\n" + r["sintese"])
        return
    if a.chat:
        hist = None
        while True:
            try:
                q = input("\nanalista> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q in ("sair", "exit", ""):
                break
            resp, hist, _, quem = perguntar(q, hist, interativo=True)
            print(f"\n[{quem}]\n{resp}")
        return
    if not a.pergunta:
        ap.print_help()
        sys.exit(1)
    resp, _, _, quem = perguntar(a.pergunta)
    print(f"\n[{quem}]\n{resp}")


if __name__ == "__main__":
    main()
