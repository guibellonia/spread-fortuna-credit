# Spread · Desafio Fortuna Crédito

Hackathon GOW 2026, 11/11/2026. `spread_final.csv` até 15h30 (checkpoint 14h15), pitch às 15h45.
Regras do desafio: `analysis/resumo-abertura.md`. Mapa das pastas: `README.md`.
Regras de Git (pull antes do push, conflitos): `.claude/CLAUDE.md`, importado abaixo.

@.claude/CLAUDE.md

## Regras gerais

- Responda em português do Brasil, de forma direta.
- Análise ou opinião vai num arquivo do autor; não reescreva o de outra pessoa. O `README.md` é do time.
- Segredos só no `.env` (fora do Git): token do bureau, senha do banco, `SUPABASE_DB_URL`, chaves de LLM.
- Todo número com a fonte: o script ou a consulta que o produz.

## Toda automação nova vai para o repositório

Script, workflow do GitHub Actions, job agendado, hook, tool de agente ou migração de banco:

1. fica numa pasta do repositório, não só na máquina de alguém;
2. tem no README da pasta o comando para rodar e as variáveis de `.env` que usa;
3. lê segredo só do ambiente;
4. sobe na hora: commit e push seguindo `.claude/CLAUDE.md`.

## Painel (`site/`)

- Next.js 16 (App Router) com export estático, no GitHub Pages em `/dashboard/`
  (https://guibellonia.github.io/spread-fortuna-credit/dashboard/). A página do time (`index.html`) fica na raiz.
- Dados em `site/src/data/dashboard.json`, gerados por `site/scripts/snapshot.py` (banco + API do bureau).
  Atualizar: `.venv/Scripts/python site/scripts/snapshot.py`, commit do JSON e push.
- Políticas do funil: `politicas()` em `site/scripts/snapshot.py`, cada uma é uma lista ordenada de passos.
  A política atual é conferida contra o histórico a cada execução (hoje bate 100%).
- Bureau: `site/scripts/bureau_client.py` (timeout 10 s, até 6 tentativas com espera crescente e jitter,
  10 em paralelo, 401 interrompe, cache em `data/cache/bureau/`, registro em `data/cache/bureau_chamadas.jsonl`).
- Deploy: `.github/workflows/static.yml` a cada push na `main` (build, checagem de ids, raiz + `/dashboard/`).
- Antes de subir mudança no painel: `cd site && npx tsc --noEmit && npm run build`.

Segurança do painel (não quebrar):

- Repositório e site são públicos: o JSON leva só agregados, nunca id de cliente ou pedido. O snapshot e o
  workflow param se acharem `C-…` ou `P-…`.
- O token do bureau não vai para o site nem para o CI. O navegador só testa o `GET /health`, sem token.
- CSP por página em `site/scripts/csp.mjs` (hash dos scripts inline). Origem externa nova entra em
  `connect-src` via `site/site.config.json`.
- Sem CDN em tempo de execução: fontes via `next/font`, baixadas no build.

Visual do painel: Material Design 3, tema claro, Poppins no texto e Montserrat nos números e destaques.
Sem box-shadow, poucas bordas, hover só com camada de estado (opacidade), nunca translate. Todo gráfico tem
a alternância para tabela.

## Banco

- Local: PostgreSQL 16+, banco `fortuna`, schema `hackathon` (`docker compose up -d`). Conexão pelo `.env`
  (`PG*`); o `src/` usa `FORTUNA_DSN`.
- Supabase: `supabase/restaurar_banco.py` restaura o dump e fecha o schema `hackathon` para a Data API
  (sem acesso para `anon`/`authenticated`, RLS ligado). Nunca exponha `hackathon` na API; o que for exposto
  vai num schema próprio, com RLS e login. Detalhe em `supabase/README.md`.
