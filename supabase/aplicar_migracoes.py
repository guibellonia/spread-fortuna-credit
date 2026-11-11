"""Aplica as migrações de supabase/migrations/ (em ordem, cada uma numa transação) e cadastra membros do painel.

Uso, da raiz do repositório, com SUPABASE_DB_URL no .env:
    .venv/Scripts/python supabase/aplicar_migracoes.py
    .venv/Scripts/python supabase/aplicar_migracoes.py --membro ana@empresa.com --membro bruno@empresa.com

Cada migração roda uma vez só (registro em painel.migracoes) e também é idempotente. O membro também precisa existir no
Supabase Auth (Authentication > Users > Add user) para conseguir entrar no painel.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from restaurar_banco import ROOT, conexao  # noqa: E402

MIGRACOES = Path(__file__).resolve().parent / "migrations"
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--membro", action="append", default=[], help="e-mail com acesso ao painel (pode repetir)")
    args = ap.parse_args()
    emails = [e.strip().lower() for e in args.membro]
    ruins = [e for e in emails if not EMAIL.match(e)]
    if ruins:
        sys.exit(f"e-mail inválido: {', '.join(ruins)}")

    load_dotenv(ROOT / ".env")
    info = conexao()
    arquivos = sorted(MIGRACOES.glob("*.sql"))
    with psycopg.connect(**info, connect_timeout=15) as c:
        with c.transaction():  # registro das migrações aplicadas: cada uma roda uma vez só
            c.execute("create schema if not exists painel")
            c.execute("create table if not exists painel.migracoes (nome text primary key, "
                      "aplicada_em timestamptz not null default now())")
            c.execute("revoke all on painel.migracoes from public")
            feitas = {n for (n,) in c.execute("select nome from painel.migracoes").fetchall()}
        for arq in arquivos:
            if arq.name in feitas:
                print(f"já aplicada: {arq.name}")
                continue
            with c.transaction():
                c.execute(arq.read_text(encoding="utf-8"))
                c.execute("insert into painel.migracoes (nome) values (%s)", (arq.name,))
            print(f"aplicada: {arq.name}")
        with c.transaction():
            for e in emails:
                c.execute("insert into painel.membros (email) values (%s) on conflict do nothing", (e,))
        membros = [m for (m,) in c.execute("select email from painel.membros order by 1").fetchall()]
    print(f"membros do painel ({len(membros)}): {', '.join(membros) or 'nenhum'}")
    if not membros:
        print("cadastre pelo menos um: --membro <e-mail>")


if __name__ == "__main__":
    main()
