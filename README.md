# Spread · Desafio Fortuna Crédito

Hackathon GOW 2026 · 11/11/2026 · `spread_final.csv` até **15h30** (checkpoint 14h15) · pitch às 15h45.
Regras do desafio: [analysis/resumo-abertura.md](analysis/resumo-abertura.md).

- **Site do time:** https://guibellonia.github.io/spread-fortuna-credit/
- **Painel:** https://guibellonia.github.io/spread-fortuna-credit/dashboard/

## Comandos

| Para | Comando | Detalhe |
|---|---|---|
| Gerar e validar o CSV | `cd src && python gerar_decisoes.py && python validar_csv.py ../saida/spread_final.csv` | `src/README.md` |
| Conversar com o agente | `cd src && python agente.py --chat` | `src/README.md` |
| Testes | `pytest tests` | `src/README.md` |
| Atualizar o painel | `.venv/Scripts/python site/scripts/snapshot.py`, depois commit e push | `site/README.md` |
| Banco local | `docker compose up -d` | `docker-compose.yml` |
| Banco no Supabase | `.venv/Scripts/python supabase/restaurar_banco.py --leitor` | `supabase/README.md` |

Segredos (token do bureau, senhas e URIs do banco, chaves de LLM) ficam só no `.env` (modelo em `.env.example`) e
nos segredos do GitHub. Nunca no Git.

## Pastas

| Pasta | O que tem | Autor |
|---|---|---|
| `src/` | pipeline de decisão: features, padrões, modelo corrigido para censura, política G, bureau com retry, CSV, tools e agente LLM | Juliano Ferreira |
| `validacao/` | validação independente (modelo de sobrevivência) e `tool_risco` | Juliano Ferreira |
| `tests/` | testes sem banco: parcela, políticas, validador, bureau, tools e agente | Juliano Ferreira |
| `analysis/` | análises da base, um arquivo por autor | time |
| `prompts/` | prompts de contexto, com autor e versão | Enio Rocha |
| `api-baseline/` | baseline da API do bureau | Guilherme Bellonia |
| `site/` | painel Next.js publicado em `/dashboard/` | Guilherme Bellonia |
| `supabase/` | restauração do banco no Supabase e papel só de leitura | Guilherme Bellonia |
| `docker/`, `docker-compose.yml` | banco local | Guilherme Bellonia |
| `.github/workflows/` | `ci.yml`: segredos, lint, testes, integração com o banco e formato dos CSVs · `static.yml`: publica o site a cada push na `main` | Juliano Ferreira · Guilherme Bellonia |
| `index.html` | página do time | Enio Rocha |
| `CLAUDE.md`, `.claude/` | contexto do projeto e regras para o Claude Code | Guilherme Bellonia |

## Rodar (um comando)

```bash
cp .env.example .env          # preencha PGPASSWORD e BUREAU_TOKEN
docker compose up -d          # banco restaurado do dump em ./data/
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python src/pipeline.py      # -> spread_final.csv, já validado
```

| Script | O que faz |
|---|---|
| `src/pipeline.py` | do banco ao `spread_final.csv` validado |
| `src/politica_regras.py` | a política por regras (atual + conta apertada + parcela > 28% da renda real), com `PARAMS` |
| `src/backtest_maduro.py` | ganho sobre a política atual no histórico maduro |
| `src/experimento.py` | o padrão que decidiu a política (ver abaixo) |
| `src/bureau_api.py` | birô dos 2.000 novos, com retry e cache |
| `src/validar.py` | confere o CSV contra o formato do manual |

> Há duas políticas candidatas no repositório: a por regras (`src/pipeline.py`, acima) e a por modelo de risco com
> valor ajustado (`src/gerar_decisoes.py`, cenário G; ver `src/README.md`). A escolha final sai da comparação das duas
> com `src/tools.py comparar_politicas`. Os três arquivos acima ganharam o sufixo `_regras`, `_api` e `_maduro` na
> integração, porque `src/politica.py`, `src/bureau.py` e `src/backtest.py` já existiam na `main`.

## Como contribuir

1. `git pull --rebase` antes de começar e antes de cada push, conferindo conflitos ([.claude/CLAUDE.md](.claude/CLAUDE.md)).
2. Análise ou opinião vai num arquivo seu (`analysis/analise-<nome>.md`); versão nova é arquivo novo (`_v2`).
   Não reescreva o arquivo de outra pessoa. O README é do time.
3. Todo número com a fonte: o script ou a consulta que o produz. Hipótese marcada como hipótese.
4. Automação nova (script, workflow, job, tool, migração) entra no repositório e sobe na hora, com o comando no
   README da pasta.
5. Documento novo na página do time: avise quem cuida do `index.html` (Enio Rocha).

## Decisões do time

| Quando | Decisão |
|---|---|
| 08h50 | Python, repositório único, prompts versionados |
| 09h00 | cada um analisa a base; duas frentes: inteligência e automação, e painel |
| 09h57 | pipeline de decisão em `src/`, com política G e validação independente |
| 10h04–10h12 | tools e agente LLM com fallback, conselho de LLMs, explicabilidade e teste de sanidade |
| 10h11 | painel em `/dashboard/` com integração ao bureau; `pull` antes do `push` |
| 10h28 | página e README no padrão visual do painel |
| 10h36 | CI de validação: segredos, lint, testes, integração com o banco e formato dos CSVs |
| 10h45 | banco no Supabase (restauração e papel só de leitura) e `CLAUDE.md` com o contexto do projeto |
