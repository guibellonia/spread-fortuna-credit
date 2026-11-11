"""Cria e configura o projeto do Supabase de ponta a ponta, pela API de gerenciamento. Nenhum segredo é impresso.

Uso, da raiz do repositório, com no .env: SUPABASE_ACCESS_TOKEN (Account > Access Tokens), SUPABASE_DB_SENHA,
SUPABASE_LEITOR_SENHA e BUREAU_TOKEN:
    .venv/Scripts/python supabase/configurar_projeto.py --usuario ana@x.com --usuario bia@y.com

Etapas (todas idempotentes; rodar de novo só faz o que falta):
 1. acha a organização (--org) e o projeto (--projeto); cria o projeto em São Paulo se não existir e espera subir;
 2. grava SUPABASE_DB_URL (Session pooler) no .env;
 3. restaura o dump e cria o papel só de leitura (restaurar_banco.py --leitor), se o schema ainda não existir;
 4. aplica as migrações e cadastra os membros (aplicar_migracoes.py --membro ...);
 5. expõe o schema painel na Data API, fecha o cadastro público no Auth e exige SSL nas conexões ao banco;
 6. grava BUREAU_TOKEN, BUREAU_URL e ORIGENS_PERMITIDAS como segredos das Edge Functions e publica a função bureau;
 7. cria no Auth os usuários que ainda não existem, com senha aleatória gravada FORA do repositório;
 8. grava supabaseUrl e a chave anon (pública por desenho) em site/site.config.json.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
API = "https://api.supabase.com/v1"
REGIAO = "sa-east-1"
ORIGENS = "https://guibellonia.github.io,http://localhost:3000"
ACESSOS = ROOT.parent / "spread-acessos-painel.txt"  # fora do repositório


class Api:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})

    def __call__(self, metodo: str, caminho: str, **kw):
        r = self.s.request(metodo, f"{API}{caminho}", timeout=60, **kw)
        if r.status_code >= 400:
            try:
                msg = r.json().get("message") or r.json().get("error") or r.text[:200]
            except ValueError:
                msg = r.text[:200]
            raise SystemExit(f"API {metodo} {caminho}: HTTP {r.status_code} · {msg}")
        return r.json() if r.content else None


def env_obrigatoria(nome: str) -> str:
    v = os.environ.get(nome, "").strip()
    if not v:
        sys.exit(f"defina {nome} no .env")
    return v


def grava_env(chave: str, valor: str) -> None:
    arq = ROOT / ".env"
    txt = arq.read_text(encoding="utf-8")
    linha = f"{chave}={valor}"
    if re.search(rf"^{chave}=.*$", txt, re.M):
        txt = re.sub(rf"^{chave}=.*$", lambda _m: linha, txt, flags=re.M)
    else:
        txt = txt.rstrip("\n") + f"\n{linha}\n"
    arq.write_text(txt, encoding="utf-8")
    os.environ[chave] = valor


def roda(*args: str) -> None:
    r = subprocess.run([sys.executable, *args], cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode:
        raise SystemExit(f"falhou: {' '.join(Path(a).name for a in args)}")


def projeto(api: Api, org_nome: str, org_id: str | None, nome: str, senha: str) -> dict:
    if org_id:  # token com escopo de organização não lista organizações
        org = org_id
    else:
        orgs = [o for o in api("GET", "/organizations") if o["name"] == org_nome]
        if len(orgs) != 1:
            sys.exit(f"esperava 1 organização chamada {org_nome!r}, achei {len(orgs)}; use --org-id")
        org = orgs[0]["id"]
    achados = [p for p in api("GET", "/projects") if p["name"] == nome and p["organization_id"] == org]
    if achados:
        p = achados[0]
        print(f"1. projeto {nome} já existe ({p['id']}, {p['region']})")
    else:
        p = api("POST", "/projects", json={"name": nome, "organization_id": org, "db_pass": senha, "region": REGIAO})
        print(f"1. projeto {nome} criado ({p['id']}, {REGIAO}); esperando subir...")
    ref = p["id"]
    for _ in range(90):
        st = api("GET", f"/projects/{ref}")["status"]
        if st == "ACTIVE_HEALTHY":
            break
        time.sleep(10)
    else:
        sys.exit(f"o projeto não ficou ACTIVE_HEALTHY a tempo (status {st})")
    print(f"   status {st}")
    return {"ref": ref}


def url_banco(api: Api, ref: str, senha: str) -> None:
    for _ in range(30):
        poolers = api("GET", f"/projects/{ref}/config/database/pooler") or []
        prim = [x for x in poolers if x.get("database_type", "PRIMARY") == "PRIMARY" and x.get("db_host")]
        if prim:
            break
        time.sleep(10)
    else:
        sys.exit("o pooler do banco ainda não está disponível; rode de novo em alguns minutos")
    x = prim[0]
    url = f"postgresql://{x['db_user']}:{senha}@{x['db_host']}:5432/{x.get('db_name', 'postgres')}?sslmode=require"
    grava_env("SUPABASE_DB_URL", url)
    print(f"2. SUPABASE_DB_URL gravada no .env (Session pooler {x['db_host']}:5432)")


def banco(usuarios: list[str]) -> None:
    import psycopg
    from psycopg.conninfo import conninfo_to_dict

    info = conninfo_to_dict(os.environ["SUPABASE_DB_URL"])
    with psycopg.connect(**info, connect_timeout=20) as c:
        existe = c.execute("select count(*) from information_schema.tables where table_schema = 'hackathon'").fetchone()[0]
    print("3. banco:", "schema hackathon já existe, refazendo só o papel de leitura" if existe else "restaurando o dump")
    roda(str(AQUI / "restaurar_banco.py"), "--leitor")
    print("4. migrações e membros")
    roda(str(AQUI / "aplicar_migracoes.py"), *[a for u in usuarios for a in ("--membro", u)])


def api_e_auth(api: Api, ref: str) -> None:
    atual = api("GET", f"/projects/{ref}/postgrest").get("db_schema", "public,graphql_public")
    schemas = [s.strip() for s in atual.split(",") if s.strip()]
    if "painel" not in schemas:
        api("PATCH", f"/projects/{ref}/postgrest", json={"db_schema": ",".join(schemas + ["painel"])})
    api("PATCH", f"/projects/{ref}/config/auth", json={"disable_signup": True})
    print("5. schema painel exposto na Data API; cadastro público fechado no Auth")


def exige_ssl(api: Api, ref: str) -> None:
    """Recusa conexão sem TLS no Postgres e no pooler. Os clientes do time já usam sslmode=require.
    Ligar reinicia o banco por alguns segundos; se já está ligado, não faz nada."""
    if not api("GET", f"/projects/{ref}/ssl-enforcement")["currentConfig"]["database"]:
        r = api("PUT", f"/projects/{ref}/ssl-enforcement", json={"requestedConfig": {"database": True}})
        if not (r.get("appliedSuccessfully") and r["currentConfig"]["database"]):
            sys.exit("a API não confirmou a exigência de SSL; confira em Database > Settings > SSL Configuration")
    print("5. banco exige SSL: conexão sem TLS é recusada")


def funcao(api: Api, ref: str) -> None:
    api("POST", f"/projects/{ref}/secrets", json=[
        {"name": "BUREAU_TOKEN", "value": env_obrigatoria("BUREAU_TOKEN")},
        {"name": "BUREAU_URL", "value": os.environ.get("BUREAU_URL", "https://gowlab-fortuna-bureau.azurewebsites.net")},
        {"name": "ORIGENS_PERMITIDAS", "value": ORIGENS},
    ])
    npx = shutil.which("npx")
    if not npx:
        sys.exit("npx não encontrado (instale o Node 20+) para publicar a função")
    # --yes: a CLI pede confirmação quando roda sem terminal interativo; quem roda este script já decidiu publicar
    r = subprocess.run([npx, "--yes", "supabase@3.1.0", "functions", "deploy", "bureau", "--project-ref", ref, "--use-api",
                        "--yes"],
                       cwd=ROOT, env=os.environ.copy())
    if r.returncode:
        raise SystemExit("falhou ao publicar a função bureau")
    print("6. segredos gravados e função bureau publicada")


def usuarios_auth(api: Api, ref: str, emails: list[str]) -> str:
    chaves = api("GET", f"/projects/{ref}/api-keys", params={"reveal": "true"})
    por_nome = {k.get("name"): k.get("api_key") for k in chaves}
    anon, servico = por_nome.get("anon"), por_nome.get("service_role")
    if not anon or not servico:
        sys.exit("não achei as chaves anon e service_role do projeto")
    base = f"https://{ref}.supabase.co/auth/v1/admin/users"
    h = {"apikey": servico, "Authorization": f"Bearer {servico}", "Content-Type": "application/json"}
    existentes = {u["email"].lower() for u in requests.get(base, headers=h, params={"per_page": 1000}, timeout=30)
                  .json().get("users", [])}
    alfa = string.ascii_letters + string.digits
    novos = []
    for e in emails:
        if e in existentes:
            continue
        senha = "".join(secrets.choice(alfa) for _ in range(20))
        r = requests.post(base, headers=h, json={"email": e, "password": senha, "email_confirm": True}, timeout=30)
        if r.status_code >= 400:
            raise SystemExit(f"não consegui criar o usuário {e}: HTTP {r.status_code}")
        novos.append((e, senha))
    if novos:
        with ACESSOS.open("a", encoding="utf-8") as f:
            f.write(f"# painel de revisão · https://guibellonia.github.io/spread-fortuna-credit/dashboard/revisao/\n")
            for e, s in novos:
                f.write(f"{e}\t{s}\n")
    print(f"7. usuários no Auth: {len(novos)} criados, {len(emails) - len(novos)} já existiam"
          + (f"; senhas em {ACESSOS}" if novos else ""))
    return anon


def site_config(ref: str, anon: str) -> None:
    arq = ROOT / "site" / "site.config.json"
    cfg = json.loads(arq.read_text(encoding="utf-8"))
    cfg.update({"supabaseUrl": f"https://{ref}.supabase.co", "supabaseAnonKey": anon})
    arq.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"8. site/site.config.json: supabaseUrl https://{ref}.supabase.co e chave anon (pública)")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org", default="Spread")
    ap.add_argument("--org-id", default=os.environ.get("SUPABASE_ORG_ID"), help="id (slug) da organização, ex.: da URL do painel")
    ap.add_argument("--projeto", default="spread-fortuna")
    ap.add_argument("--usuario", action="append", default=[], help="e-mail do time (vira usuário e membro)")
    args = ap.parse_args()
    emails = sorted({e.strip().lower() for e in args.usuario if e.strip()})

    load_dotenv(ROOT / ".env")
    api = Api(env_obrigatoria("SUPABASE_ACCESS_TOKEN"))
    senha = env_obrigatoria("SUPABASE_DB_SENHA")
    env_obrigatoria("SUPABASE_LEITOR_SENHA")

    ref = projeto(api, args.org, args.org_id, args.projeto, senha)["ref"]
    url_banco(api, ref, senha)
    banco(emails)
    api_e_auth(api, ref)
    exige_ssl(api, ref)
    funcao(api, ref)
    anon = usuarios_auth(api, ref, emails)
    site_config(ref, anon)
    print(f"pronto: https://supabase.com/dashboard/project/{ref}")


if __name__ == "__main__":
    main()
