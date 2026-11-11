"""Exporta o motor da Proposta para o painel: as árvores do modelo corrigido de censura (o mesmo que
src/gerar_decisoes.py treina), os parâmetros de src/politica.py e as entradas de cada pedido novo. O navegador refaz
a decisão com site/src/lib/motor.ts para explicar cada pedido na Revisão e para o simulador.

Tudo vai para o Supabase, só para membros (painel.modelo e painel.decisoes.entrada); nada vai para o site público.
Antes de publicar, confere que o modelo retreinado dá as decisões de saida/decisoes_mescla.csv e que o motor em
TypeScript dá as mesmas 2.000 decisões que o Python (site/scripts/paridade-motor.mjs). Se algo não bate, não grava.

Uso, da raiz do repositório, depois de gerar_decisoes.py e politica_mescla.py, com PG* (banco local, para os pesos
de censura) e SUPABASE_DB_URL no .env:
    .venv/Scripts/python supabase/publicar_motor.py              # só gera data/cache/motor/ e confere
    .venv/Scripts/python supabase/publicar_motor.py --publicar   # e grava no Supabase
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(ROOT / "src"))
from restaurar_banco import conexao  # noqa: E402

CACHE = ROOT / "data" / "cache" / "motor"  # fora do Git: tem ids e dados de cliente
CAMPOS = ["valor_solicitado", "prazo_meses", "renda_declarada", "tipo_vinculo", "idade", "meses_conta", "score",
          "restricoes_ativas", "consultas_90_dias", "meses_historico_bureau", "parcelas_outras_instituicoes",
          "mov_entradas_media", "mov_salario_media", "mov_saidas_media", "mov_saldo_medio", "mov_saldo_minimo_min",
          "mov_dias_cheque_total", "mov_meses_cheque", "mov_entradas_cv", "mov_meses_saida_maior_3m"]


def limpo(v):
    """NaN vira null; inteiros do numpy viram int do Python."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if hasattr(v, "item"):
        v = v.item()
    return v


def arvores(m) -> dict:
    out = []
    for (pred,) in m._predictors:  # binário: um preditor por iteração
        n = pred.nodes
        if n["is_categorical"].any():
            raise SystemExit("o modelo tem divisão categórica, que o motor TS não implementa")
        out.append({"f": n["feature_idx"].tolist(), "t": n["num_threshold"].tolist(), "e": n["left"].tolist(),
                    "d": n["right"].tolist(), "m": n["missing_go_to_left"].astype(int).tolist(),
                    "v": n["value"].tolist(), "folha": n["is_leaf"].astype(int).tolist()})
    return {"base": float(m._baseline_prediction.ravel()[0]), "arvores": out}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publicar", action="store_true", help="grava em painel.modelo e painel.decisoes.entrada")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    if not os.environ.get("FORTUNA_DSN"):  # src/db.py; o libpq completa host, porta e senha pelos PG*
        os.environ["FORTUNA_DSN"] = f"dbname={os.environ.get('PGDATABASE', 'fortuna')}"

    from cenarios import R_ATRASO, m_wrap, treinar_corrigido
    from features import TAXA
    from modelo import ATRIBUTOS, GANHO
    from politica import FRACOES, PARAMS, VALOR_MAX, VALOR_MIN, politica_proposta

    hist = pd.read_pickle(ROOT / "saida" / "hist.pkl")
    x = pd.read_pickle(ROOT / "saida" / "novos.pkl").reset_index(drop=True)
    mescla = pd.read_csv(ROOT / "saida" / "decisoes_mescla.csv", dtype={"id_pedido": str}).set_index("id_pedido")

    modelo, meta = treinar_corrigido(hist)
    dec = politica_proposta(x, m_wrap(modelo))
    bate = (dec.set_index("id_pedido").valor.round(2) == mescla.valor_aprovado.reindex(dec.id_pedido)).mean()
    print(f"modelo retreinado ({meta}) bate com decisoes_mescla.csv em {bate:.2%} dos pedidos")
    if bate < 1:
        raise SystemExit("o modelo retreinado não reproduz as decisões publicadas; rode gerar_decisoes.py de novo")

    num = x[CAMPOS].drop(columns="tipo_vinculo")
    tipico = {c: round(float(v), 2) for c, v in num.median().items()}
    tipico["tipo_vinculo"] = str(x.tipo_vinculo.mode()[0])
    conteudo = {
        "atributos": ATRIBUTOS,
        **arvores(modelo),
        "politica": {**{k: limpo(v) for k, v in PARAMS.items()}, "r_atraso": R_ATRASO, "ganho": GANHO.tolist(),
                     "fracoes": FRACOES.tolist(), "valor_min": VALOR_MIN, "valor_max": VALOR_MAX, "taxa": TAXA},
        "tipico": {c: tipico[c] for c in CAMPOS},
        "auc": meta["auc"],
    }
    texto = json.dumps(conteudo, separators=(",", ":"))
    fonte = f"treinar_corrigido(hist.pkl) · {len(conteudo['arvores'])} árvores · sha256:{hashlib.sha256(texto.encode()).hexdigest()[:12]}"
    conteudo["fonte"] = fonte
    entradas = [{c: limpo(v) for c, v in r.items()} for r in x[["id_pedido"] + CAMPOS].to_dict("records")]
    esperado = dec[["id_pedido", "aprova", "valor", "p_nao_paga", "ganho_esperado", "motivo"]].merge(
        mescla[["pontos_detalhe"]], left_on="id_pedido", right_index=True)  # sinais da faixa, para conferir o TS
    esperado = [{k: limpo(v) for k, v in r.items()} for r in esperado.to_dict("records")]

    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "modelo.json").write_text(json.dumps(conteudo, separators=(",", ":")), encoding="utf-8")
    (CACHE / "paridade.json").write_text(json.dumps({"entradas": entradas, "esperado": esperado}), encoding="utf-8")
    print(f"gravado data/cache/motor/ (modelo {len(texto) / 1024:.0f} KB, {len(entradas)} entradas)")

    node = shutil.which("node")
    if not node:
        raise SystemExit("node não encontrado: instale o Node 22+ para conferir o motor TS")
    r = subprocess.run([node, "--experimental-strip-types", "--no-warnings", str(ROOT / "site" / "scripts" / "paridade-motor.mjs")],
                       cwd=ROOT)
    if r.returncode:
        raise SystemExit("o motor TS não reproduz o Python; nada foi publicado")
    if not args.publicar:
        print("conferido; para gravar no Supabase: --publicar")
        return

    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(**conexao(), connect_timeout=15) as c, c.transaction():
        c.execute("""insert into painel.modelo (id, conteudo, fonte) values ('proposta', %s, %s)
                     on conflict (id) do update set conteudo = excluded.conteudo, fonte = excluded.fonte,
                                                    publicado_em = now()""", (Jsonb(conteudo), fonte))
        c.execute("create temp table entrada_motor (id_pedido text, entrada jsonb) on commit drop")
        with c.cursor().copy("copy entrada_motor from stdin") as cp:
            for e in entradas:
                cp.write_row((e["id_pedido"], json.dumps({k: v for k, v in e.items() if k != "id_pedido"})))
        n = c.execute("""update painel.decisoes d set entrada = e.entrada from entrada_motor e
                         where d.id_pedido = e.id_pedido""").rowcount
        if n != len(entradas):
            raise SystemExit(f"só {n} de {len(entradas)} pedidos estão em painel.decisoes; nada foi gravado")
    print(f"publicado: painel.modelo ({fonte}) e a entrada de {n} pedidos")


if __name__ == "__main__":
    main()
