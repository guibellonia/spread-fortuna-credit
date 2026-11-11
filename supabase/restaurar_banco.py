"""Restaura o dump do hackathon no Postgres do Supabase (schema `hackathon`) e fecha o acesso pela API.

Uso, da raiz do repositório, com SUPABASE_DB_URL no .env (string "Session pooler" do botão Connect do Supabase):
    .venv/Scripts/python supabase/restaurar_banco.py             # restaura se o schema ainda não existir
    .venv/Scripts/python supabase/restaurar_banco.py --recriar   # apaga o schema hackathon e restaura de novo
    .venv/Scripts/python supabase/restaurar_banco.py --leitor    # cria/atualiza o papel só de leitura
                                                                 # fortuna_leitura (senha em SUPABASE_LEITOR_SENHA)

Precisa do pg_restore 16 ou mais novo no PATH. A senha não vai para a linha de comando: o pg_restore recebe a
conexão por variáveis de ambiente. A restauração é uma transação só: ou entra tudo, ou nada.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parents[1]
TABELAS = ["clientes", "pedidos", "movimentacao_mensal", "bureau", "parcelas"]
ESPERADO = {"historico": 10000, "novo": 2000}
LEITOR = "fortuna_leitura"


def conexao() -> dict:
    url = os.environ.get("SUPABASE_DB_URL", "").strip()
    if not url:
        sys.exit("defina SUPABASE_DB_URL no .env (Supabase > Connect > Session pooler); modelo em .env.example")
    info = conninfo_to_dict(url)
    info.setdefault("sslmode", "require")
    info.setdefault("dbname", "postgres")
    info.setdefault("port", "5432")
    if info.get("port") == "6543":
        sys.exit("essa é a string do Transaction pooler (6543); use a do Session pooler (5432)")
    return info


def pg_restore() -> str:
    exe = shutil.which("pg_restore")
    if not exe:
        sys.exit("pg_restore não encontrado no PATH (instale o PostgreSQL 16 ou mais novo)")
    versao = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout
    m = re.search(r"(\d+)\.", versao)
    if not m or int(m.group(1)) < 16:
        sys.exit(f"o dump é do PostgreSQL 16; o pg_restore precisa ser 16 ou mais novo ({versao.strip()})")
    return exe


def contagens(c: psycopg.Connection) -> dict:
    return {t: c.execute(f"select count(*) from hackathon.{t}").fetchone()[0] for t in TABELAS}


def restaurar(info: dict, dump: Path) -> None:
    exe = pg_restore()
    env = {**os.environ, "PGHOST": info["host"], "PGPORT": str(info["port"]), "PGUSER": info["user"],
           "PGPASSWORD": info.get("password", ""), "PGDATABASE": info["dbname"], "PGSSLMODE": info["sslmode"],
           "PGCONNECT_TIMEOUT": "15"}
    print("restaurando (uma transação só)...")
    r = subprocess.run([exe, "--no-owner", "--no-privileges", "--single-transaction", "--exit-on-error",
                        "--dbname", info["dbname"], str(dump)], env=env)
    if r.returncode:
        sys.exit(f"pg_restore falhou (código {r.returncode}); nada foi gravado")


def fechar(c: psycopg.Connection) -> list[str]:
    """Sem acesso para os papéis da Data API do Supabase e RLS ligado em todas as tabelas."""
    papeis = [p for (p,) in c.execute(
        "select rolname from pg_roles where rolname in ('anon', 'authenticated')").fetchall()]
    if papeis:
        alvo = ", ".join(papeis)
        c.execute(f"revoke all on schema hackathon from public, {alvo}")
        c.execute(f"revoke all on all tables in schema hackathon from public, {alvo}")
    for t in TABELAS:
        c.execute(f"alter table hackathon.{t} enable row level security")
    return papeis


def leitor(c: psycopg.Connection, senha: str | None) -> bool:
    """Papel só de leitura para o CI e para quem só consulta. Sem senha, só refaz as permissões se ele existir."""
    existe = c.execute("select 1 from pg_roles where rolname = %s", (LEITOR,)).fetchone() is not None
    if senha:
        if len(senha) < 16:
            sys.exit("SUPABASE_LEITOR_SENHA precisa ter pelo menos 16 caracteres")
        acao = "alter" if existe else "create"
        c.execute(sql.SQL(acao + " role {} with login password {}").format(sql.Identifier(LEITOR), sql.Literal(senha)))
        c.execute(sql.SQL("alter role {} set default_transaction_read_only = on").format(sql.Identifier(LEITOR)))
        existe = True
    if not existe:
        return False
    c.execute(sql.SQL("grant usage on schema hackathon to {}").format(sql.Identifier(LEITOR)))
    c.execute(sql.SQL("grant select on all tables in schema hackathon to {}").format(sql.Identifier(LEITOR)))
    for t in TABELAS:
        c.execute(f"drop policy if exists leitura on hackathon.{t}")
        c.execute(sql.SQL("create policy leitura on hackathon.{} for select to {} using (true)").format(
            sql.Identifier(t), sql.Identifier(LEITOR)))
    return True


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recriar", action="store_true", help="apaga o schema hackathon do Supabase antes de restaurar")
    ap.add_argument("--leitor", action="store_true", help=f"cria/atualiza o papel {LEITOR} (senha em SUPABASE_LEITOR_SENHA)")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    senha_leitor = os.environ.get("SUPABASE_LEITOR_SENHA") if args.leitor else None
    if args.leitor and not senha_leitor:
        sys.exit("defina SUPABASE_LEITOR_SENHA no .env para criar o papel só de leitura")
    dump = Path(os.environ.get("FORTUNA_DUMP") or ROOT / "data" / "fortuna_hackathon.dump")
    info = conexao()

    with psycopg.connect(**info, connect_timeout=15, autocommit=True) as c:
        versao = c.execute("show server_version").fetchone()[0]
        n = c.execute("select count(*) from information_schema.tables where table_schema = 'hackathon'").fetchone()[0]
        print(f"servidor PostgreSQL {versao} em {info['host']} · tabelas em hackathon: {n}")
        if n and not args.recriar and not args.leitor:
            print("o schema hackathon já existe:", contagens(c))
            sys.exit("nada foi feito; use --recriar para apagar e restaurar de novo")
        if n and args.recriar:
            print("apagando o schema hackathon:", contagens(c))
            c.execute("drop schema hackathon cascade")
            n = 0

    if not n:
        if not dump.exists():
            sys.exit(f"dump não encontrado: {dump} (copie fortuna_hackathon.dump para data/)")
        restaurar(info, dump)

    with psycopg.connect(**info, connect_timeout=15, autocommit=True) as c:
        papeis = fechar(c)
        tem_leitor = leitor(c, senha_leitor)
        for t in TABELAS:
            c.execute(f"analyze hackathon.{t}")
        por_tipo = dict(c.execute("select tipo_base, count(*) from hackathon.pedidos group by 1").fetchall())
        print("banco:", contagens(c), "· pedidos por base:", por_tipo)
        if por_tipo != ESPERADO:
            sys.exit(f"contagem diferente do esperado {ESPERADO}")

    fechado = f", sem acesso para {', '.join(papeis)}" if papeis else ""
    print(f"ok: hackathon com RLS ligado{fechado}.")
    if tem_leitor:
        user = f"{LEITOR}.{info['user'].split('.', 1)[1]}" if "." in info["user"] else LEITOR
        print(f"papel só de leitura: {LEITOR} · use como FORTUNA_DSN no CI e para consultas:")
        print(f"  postgresql://{user}:<SUPABASE_LEITOR_SENHA>@{info['host']}:{info['port']}/{info['dbname']}?sslmode=require")
    print("para gravar (pipeline, scripts): FORTUNA_DSN=<a mesma SUPABASE_DB_URL>")


if __name__ == "__main__":
    main()
