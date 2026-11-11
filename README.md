# Spread · Desafio Fortuna Crédito

Hackathon GOW 2026 · 11/11/2026 · entrega do `spread_final.csv` até **15h30** (checkpoint 14h15) · pitch às 15h45.

**Site do time:** https://guibellonia.github.io/spread-fortuna-credit/ (Resumo, Padrões e censura, Documentos e o Painel)

**Painel:** https://guibellonia.github.io/spread-fortuna-credit/dashboard/ (funil das políticas, volume, safras, padrões e saúde da API do bureau)

## O desafio, em 5 linhas

- A Fortuna Crédito quer uma política de aprovação e de valor melhor que a atual, com a IA achando os padrões e o analista decidindo.
- Por pedido aprovado: pagou em dia **+15%** do valor · com atraso **+5%** · não pagou **−60%** · negado **0**.
- Nota: 40 ganho sobre a política atual nos 2.000 pedidos novos · 25 padrões · 15 pitch · 10 painel · 10 qualidade técnica.
- O CSV sai do código (`id_pedido,decisao,valor_aprovado`); editado à mão desclassifica.
- Regras completas: [analysis/resumo-abertura.md](analysis/resumo-abertura.md).

## Onde está cada coisa

Autor entre parênteses, como no [site do time](https://guibellonia.github.io/spread-fortuna-credit/) (coluna Autor da aba Documentos).

| Pasta | O que tem |
|---|---|
| `src/` | **o pipeline de decisão** (Juliano Ferreira): features, padrões, modelo corrigido para censura, política G, bureau com retry, gerador e validador do CSV, painel, tools e agente LLM com fallback, conselho de LLMs, explicabilidade e teste de sanidade. Comando em `src/README.md` |
| `validacao/` | validação independente com modelo de sobrevivência e `tool_risco` para o agente (Juliano Ferreira) |
| `analysis/` | análises da base, uma por autor: banco e contextos (Juliano Ferreira), complementos, resumo e transcrição da abertura (Enio Rocha), padrões, censura e pendências técnicas agregados e scripts (Guilherme Bellonia), pendências do desafio (`chatbot-ia-gow`). Scripts do Enio em `analysis/scripts-enio/` |
| `prompts/` | prompts de contexto do time, com autor e versão (Enio Rocha) |
| `api-baseline/` | baseline da API do bureau (Guilherme Bellonia) |
| `site/` | **o painel**: Next.js com export estático, publicado em [`/dashboard/`](https://guibellonia.github.io/spread-fortuna-credit/dashboard/). Dados de `site/src/data/dashboard.json`, gerado por `site/scripts/snapshot.py` (Guilherme Bellonia). Detalhe em `site/README.md` |
| `docker/` e `docker-compose.yml` | banco local (Guilherme Bellonia) |
| `.github/workflows/` | publicação no GitHub Pages a cada push na `main`: a página do time na raiz e o painel em `/dashboard/` (Guilherme Bellonia) |
| `.claude/` | diretrizes para o Claude Code e para o time: `pull` antes de `push` e checagem de conflitos (Guilherme Bellonia) |
| `index.html` | a página do time, no mesmo padrão visual do painel: Resumo, Padrões e censura, Documentos e link para o Painel (Enio Rocha) |
| `README.md` | este arquivo (Enio Rocha) |

## Como contribuir

Todo mundo pode e deve contribuir. Para não pisar no trabalho do outro:

1. **Antes de começar:** `git pull`. Leia o que já existe na pasta do assunto.
2. **Um arquivo por contribuição,** com o seu nome quando for opinião ou análise sua (ex.: `analysis/analise-<nome>.md`, `prompts/<nome>_<assunto>_v1.md`).
3. **Não reescreva o arquivo de outra pessoa.** Discorde num arquivo seu, citando o dela, ou converse no chat do time.
4. **Todo número com a fonte:** o script ou a consulta que o produz. Hipótese marcada como hipótese.
5. **Versão nova = arquivo novo** (`_v2`), para comparar.
6. **Nunca suba o token do bureau** nem senha de banco. Use variável de ambiente.
7. **Commit pequeno e com mensagem clara.** Depois `git pull --rebase` e `git push`.

O site atualiza sozinho a cada push na `main`. Para um documento novo aparecer na aba Documentos da página, avise quem está cuidando do `index.html` (Enio Rocha). Antes de qualquer `push`, siga `.claude/CLAUDE.md`.

## Decisões do time

| Quando | Decisão |
|---|---|
| 08h50 | Python; repositório único; prompts versionados |
| 09h00 | cada um roda a própria análise; depois juntamos num prompt único |
| 09h00 | duas frentes: back-end (inteligência e automação) e front-end (painel) |
| 09h57 | pipeline de decisão no repositório (`src/`), com política G e validação independente |
| 10h00 | página reduzida a 3 abas: Resumo, Padrões e censura, Documentos |
| 10h01 | `src/` e `validacao/` entram no README e na página |
| 10h04 a 10h12 | tools para o agente LLM, explicabilidade e teste de sanidade, agente com fallback e conselho de LLMs com presidente (Juliano Ferreira, `src/`) |
| 10h11 | painel Next.js em `/dashboard/`, com integração ao bureau e deploy no Pages (Guilherme Bellonia) |
| 10h11 | diretriz de `pull` antes do `push` e checagem de conflitos (`.claude/CLAUDE.md`, Guilherme Bellonia) |
| 10h28 | página e README no mesmo padrão visual do painel (tema claro, Poppins e Montserrat, cartões), com o autor de cada bloco e de cada documento (Enio Rocha) |
