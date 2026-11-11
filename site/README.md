# Painel do time Spread

Painel de experimentação dos 2.000 pedidos novos da Fortuna, com as duas partes que o manual exige: os padrões no
formato "Clientes com X têm inadimplência de N%, contra M% da média. Afeta K clientes." e a política proposta em
passos. Também o funil e o volume de cada política, o comparativo de ganho, a inadimplência por safra, o perfil do
bureau e a saúde da integração com a API do bureau.

Next.js 16 (App Router) com export estático, publicado pelo GitHub Actions em
`https://guibellonia.github.io/spread-fortuna-credit/dashboard/`. A página do time continua na raiz.

## Como os dados chegam ao painel

```
banco ──────────────┐
API do bureau ──────┼─► scripts/snapshot.py ─► src/data/dashboard.json ─► git push ─► Actions ─► Pages
saida/decisoes_     │     (token só aqui)          (só agregados)
  mescla.csv ───────┘
```

1. `src/gerar_decisoes.py` e `src/politica_mescla.py` gravam `saida/decisoes_mescla.csv` (proposta, regras, atual
   e faixa de risco), a mesma fonte da revisão.
2. `scripts/snapshot.py` lê o banco, o bureau e esse CSV e grava `src/data/dashboard.json`. Se existir
   `saida/comparacao_mescla_*.csv` (de `politica_mescla.py --comparar`), entra no comparativo.
3. O JSON é versionado. O push na `main` dispara o build e a publicação.

### Atualizar os dados

Da raiz do repositório, com o `.env` preenchido (modelo em `.env.example`):

```
.venv/Scripts/python -m pip install -r site/scripts/requirements.txt   # uma vez
.venv/Scripts/python site/scripts/snapshot.py
git add site/src/data/dashboard.json && git commit -m "painel: atualiza dados" && git push
```

O script confere a política atual contra o histórico (hoje: 100% das decisões e valores), confere o funil das
regras contra o CSV e imprime o resumo de cada política. A proposta é definida em `src/politica.py`; o painel só
a mostra.

## Integração com o bureau

`scripts/bureau_client.py`, com a configuração medida em `api-baseline/baseline-agregado.md`:

- timeout de 10 s; nova tentativa só em 503, timeout e erro de rede;
- até 6 tentativas, esperando 0,5 s, 1 s, 2 s, 4 s... com variação aleatória;
- 401 interrompe tudo; 404 e outros 4xx falham só aquele cliente;
- 10 chamadas em paralelo;
- cache por `id_cliente` em `data/cache/bureau/` e registro de cada chamada em `data/cache/bureau_chamadas.jsonl`
  (os dois ficam fora do Git). Rodar de novo só busca quem faltou.

O cartão "API do bureau" mostra os números desse registro e faz, do navegador, um teste ao vivo do `GET /health`
(aberto, sem token).

## Revisão do analista (`/revisao/`)

Login com e-mail e senha (Supabase Auth, cadastro público fechado), fila de pedidos com filtros (sem revisão,
diferente da política atual, revisadas), decisão da IA com motivo e risco, bureau ao vivo pela Edge Function e
registro da revisão (confirmar, aprovar com valor ou negar, com justificativa). Os dados vêm do schema `painel`
do Supabase, só para membros; nada disso vai no build. Configuração em `site.config.json` (`supabaseUrl` e a
chave anon, pública por desenho). Banco, função e acessos: `supabase/README.md`.

## Segurança

- **O token nunca sai da máquina do time.** Ele só é lido do `.env` pelo script de snapshot. O build não recebe
  segredo nenhum, e o site publicado não chama a API autenticada.
- **Só agregados vão para o site** (o repositório é público). O snapshot e o workflow param se encontrarem um id de
  cliente ou de pedido (`C-…`, `P-…`).
- **Content-Security-Policy** em cada página (`scripts/csp.mjs`): scripts só do próprio site, com hash para os
  inline do Next; conexões só para o próprio site, para o bureau (`/health`) e para o projeto do Supabase
  (`supabaseUrl`); sem `object`, `frame`, `form` ou `base`.
  O GitHub Pages não deixa configurar cabeçalhos, então a política vai numa `<meta>` e `frame-ancestors` não se
  aplica.
- Fontes (Poppins e Montserrat) são baixadas no build e servidas pelo próprio site. Sem CDN em tempo de execução.
- `referrer: no-referrer` e `noindex`.
- No CI: `npm ci --ignore-scripts` com lockfile exato, `npm audit` de produção barrando falha crítica,
  checkout sem credencial persistida e permissões mínimas por job.

## Desenvolvimento

```
cd site
npm install
npm run dev          # http://localhost:3000
npm run build        # gera out/ com a CSP aplicada
```

Para simular o caminho do Pages: `PAGES_BASE_PATH=/spread-fortuna-credit/dashboard npm run build`
(no Git Bash do Windows, prefixe com `MSYS_NO_PATHCONV=1`).

## Estrutura

| Caminho | O que é |
|---|---|
| `scripts/snapshot.py` | banco + bureau → `src/data/dashboard.json` |
| `scripts/bureau_client.py` | cliente da API com retry, cache e registro |
| `scripts/csp.mjs` | grava a CSP em cada HTML depois do build |
| `src/components/` | cartões do painel (funil, volume, safras, pontos, padrões, API, comparativo) |
| `src/app/globals.css` | tokens do Material Design 3 (tema claro) e layout |
