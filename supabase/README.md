# Banco no Supabase

Um Postgres compartilhado com o dump do hackathon: o time todo usa o mesmo banco, sem restaurar nada na própria
máquina, e o CI (`.github/workflows/ci.yml`) roda o teste de integração contra ele. É também a base para uma API.

## 1. Criar o projeto (uma vez)

1. Em supabase.com, crie um projeto na região São Paulo, com senha forte para o banco.
2. Botão **Connect** → **Session pooler** → copie a URI (funciona em IPv4; a conexão direta é só IPv6).
3. No `.env` da raiz (fora do Git), troque `[YOUR-PASSWORD]` pela senha e defina a senha do papel de leitura:

```
SUPABASE_DB_URL=postgresql://postgres.<ref>:<senha>@<host>.pooler.supabase.com:5432/postgres
SUPABASE_LEITOR_SENHA=<16+ caracteres>
```

## 2. Restaurar o dump

Da raiz do repositório, com `data/fortuna_hackathon.dump` no lugar e o `pg_restore` 16+ no PATH:

```
.venv/Scripts/python supabase/restaurar_banco.py --leitor     # restaura e cria o papel fortuna_leitura
.venv/Scripts/python supabase/restaurar_banco.py --recriar    # apaga o schema hackathon e restaura de novo
```

- Restaura numa transação só (entra tudo ou nada) e confere 10.000 históricos e 2.000 novos.
- Fecha o schema `hackathon` para os papéis da Data API (`anon` e `authenticated`) e liga o RLS.
- `--leitor` cria ou atualiza `fortuna_leitura`: só `SELECT` e sessão somente leitura.
- Sem `--recriar`, nunca apaga nada. Rodar de novo com `--leitor` só refaz o papel.

## 3. Conectar

| Quem | Conexão |
|---|---|
| CI (segredo `FORTUNA_DSN` no GitHub) e quem só consulta | `postgresql://fortuna_leitura.<ref>:<senha do leitor>@<host>:5432/postgres?sslmode=require` (o script imprime o modelo) |
| `src/` e `validacao/` | `FORTUNA_DSN=<URI>`; a do leitor basta para ler |
| `analysis/`, `site/scripts/`, `api-baseline/` | `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` com os dados da URI e `PGSSLMODE=require` |
| psql | `psql "$SUPABASE_DB_URL"` |

## Segurança

- As URIs têm senha: só no `.env` e nos segredos do GitHub, nunca em commit, chat ou código.
- O CI usa o papel de leitura, não o `postgres`.
- **Não adicione `hackathon` aos "Exposed schemas" da Data API.** Os dados crus ficam fora da API; o que for
  exposto depois entra num schema próprio, com RLS e login.
