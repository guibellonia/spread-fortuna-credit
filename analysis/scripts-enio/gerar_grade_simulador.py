#!/usr/bin/env python3
"""Gera simulador/grade.json a partir da varredura do motor v2 (9.000 regras).
Autoria: Enio Rocha (motor v2). Só resultados agregados por regra; nada por cliente/contrato.
Uso: python3 -I analysis/scripts-enio/gerar_grade_simulador.py CAMINHO/varredura.csv CAMINHO/ponto-ideal.json simulador/grade.json
Formato: o índice da linha é a combinação dos controles em base mista, na ordem de "ordem"
(teto, acao, conta, score, restr, renda, corte); cada linha = colunas de "cols", inteiros arredondados.
score_op não duplica: cada corte tem um só operador (450/500/550/650 = ">="; 600 = ">"), então vira UM controle de 5 posições.
"""
import csv, json, sys

csv_p, ponto_p, out_p = sys.argv[1:4]
R = list(csv.DictReader(open(csv_p, encoding="utf-8")))
assert len(R) == 9000

dim = {
    "teto": sorted({int(r["teto"]) for r in R}),
    "acao": ["nega", "reduz"],
    "conta": ["nenhum", "saque3", "cheq2_OU"],
    "score": [("ge", 450), ("ge", 500), ("ge", 550), ("gt", 600), ("ge", 650)],
    "restr": [0, 1],
    "renda": [1500, 2000],
    "corte": ["", "0.15", "0.175", "0.2", "0.25"],
}
ordem = list(dim)
ops = {}
for r in R:
    ops.setdefault(int(r["score_corte"]), set()).add(r["score_op"])
assert all(len(v) == 1 for v in ops.values()), "score_op duplica um corte"
assert [(list(ops[c])[0], c) for c in (450, 500, 550, 600, 650)] == dim["score"]

cols = ["aprovados", "valor", "ganho", "ic90_lo", "ic90_hi", "ganho_apertar", "ganho_afrouxar",
        "n_negou_da_atual", "n_reduziu", "n_aprovou_que_atual_nega", "hist_ganho_fora_do_tempo_observado_proj"]
by = {}
for r in R:
    k = (int(r["teto"]), r["acao"], r["conta"], (r["score_op"], int(r["score_corte"])),
         int(r["restr_max"]), int(r["renda_min"]), r["corte_risco"])
    assert k not in by
    by[k] = [int(round(float(r[c]))) for c in cols]

rows = []
def rec(i, k):
    if i == len(ordem):
        rows.append(by[tuple(k)]); return
    for v in dim[ordem[i]]:
        rec(i + 1, k + [v])
rec(0, [])
assert len(rows) == 9000

pi = json.load(open(ponto_p, encoding="utf-8"))
def idx(p):
    sc = p["parametros"]["score"]
    op = "gt" if sc.startswith(">") and not sc.startswith(">=") else "ge"
    num = int(sc.replace(">=", "").replace(">", "").strip())
    cr = p["parametros"]["corte_risco_previsto"]
    cr = "" if cr in (None, "") else {0.15: "0.15", 0.175: "0.175", 0.2: "0.2", 0.25: "0.25"}[cr]
    return [dim["teto"].index(p["parametros"]["teto_parcela_sobre_renda_real_pct"]),
            dim["acao"].index(p["parametros"]["acao_acima_do_teto"]), 0,
            dim["score"].index((op, num)), p["parametros"]["restricoes_max"],
            dim["renda"].index(int(p["parametros"]["renda_declarada_min"].__str__().replace("> ", "")) if isinstance(p["parametros"]["renda_declarada_min"], str) else p["parametros"]["renda_declarada_min"]),
            dim["corte"].index(cr)]
presets = {n: idx(pi[n]) for n in ("seguro", "equilibrado", "agressivo")}
# confere cada preset contra o ponto-ideal.json
for n, ix in presets.items():
    k = (dim["teto"][ix[0]], dim["acao"][ix[1]], dim["conta"][ix[2]], dim["score"][ix[3]], dim["restr"][ix[4]], dim["renda"][ix[5]], dim["corte"][ix[6]])
    assert by[k][0] == pi[n]["novos_2000"]["aprovados"], n
    assert abs(by[k][2] - pi[n]["novos_2000"]["ganho_esperado"]) <= 1, n

a = pi["atual_referencia"]
out = {"ordem": ordem, "dim": {k: [list(x) if isinstance(x, tuple) else x for x in v] for k, v in dim.items()},
       "cols": cols, "presets": presets,
       "atual": {"aprovados": a["aprovados"], "valor": round(a["valor"], 2)},
       "hipoteses": pi["equilibrado"]["hipoteses"][:5],
       "rows": rows}
json.dump(out, open(out_p, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
print("ok", out_p, len(rows), "linhas")
