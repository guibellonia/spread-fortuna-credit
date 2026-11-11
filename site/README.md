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

## Proposta no histórico (`/historico/`)

Aplica a Proposta (`src/politica.py`) aos 10.000 pedidos do histórico e compara com a decisão real da Fortuna e
com o desfecho observado: resultado (+15% em dia, +5% com atraso, −60% sem pagar), o efeito de cada ajuste
(barreiras, corte de risco, valor e aprovações novas), a matriz de concordância, a diferença mês a mês, a estimativa
de risco contra o desfecho e o piloto da Fortuna. Alterna entre os 10.000 pedidos e só os maduros (até set/25).

Sem vazamento: cada trimestre é decidido por um modelo (`src/cenarios.treinar_corrigido`) treinado sem ele. Pedidos
que a Fortuna negou e a Proposta aprova não têm desfecho e entram pelo ganho esperado do modelo, sempre separados.

Da raiz do repositório, depois de `cd src && python gerar_decisoes.py` (grava `saida/hist.pkl`), com o banco no
`.env` (`PG*`) ou em `FORTUNA_DSN` (leva cerca de 1 minuto):

```
.venv/Scripts/python site/scripts/historico.py
git add site/src/data/historico.json && git commit -m "painel: atualiza histórico" && git push
```

O script confere que os ajustes somam a diferença observada e para se o JSON tiver id de cliente ou de pedido.

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

## Por que a IA sugeriu, simulador e lote (`/revisao/` e `/simulador/`)

`src/lib/motor.ts` refaz no navegador a decisão da Proposta (`src/politica.py` com o modelo de `src/cenarios.py`):
barreiras, risco, escolha do valor e o ganho esperado de cada valor testado. O modelo e a entrada de cada pedido
ficam no Supabase, só para membros (`supabase/publicar_motor.py`); nada disso vai no build. Antes de publicar, o
script roda `scripts/paridade-motor.mjs`, que exige as mesmas 2.000 decisões, valores e motivos do Python.

- **Revisão:** cada pedido abre com os pontos a favor e contra o cliente lado a lado (barreiras, risco e os sinais
  da faixa verde/amarela/laranja), cada um com o calote que aquele perfil teve no histórico (padrões do
  `dashboard.json`). Abaixo, num bloco que abre, os passos da política contra os limites e o ganho esperado de cada
  valor testado. Os sinais da faixa (`sinais` em `src/lib/motor.ts`) são conferidos contra o Python na paridade.
- **Simulador (`/simulador/`, com login):** formulário de cliente e pedido com perfis prontos (típico, com restrição,
  conta apertada, renda real baixa, pedido alto, score baixo) ou a partir de um pedido real; responde na hora.
  "Simular variações" na Revisão abre o simulador com aquele pedido.
- **Lote:** um CSV de clientes novos (modelo no botão "Baixar modelo de CSV") devolve aprovados, volume, lucro e
  prejuízo esperados, motivos de negação e o CSV das decisões. Roda só no navegador.

## Lucro e prejuízo esperados (Visão geral)

O card "Lucro e prejuízo esperados das sugestões da IA" (`resultadoIA` no `dashboard.json`, de `scripts/snapshot.py`)
soma, nos aprovados da Proposta, prejuízo = 60% do valor × chance de não pagar e lucro = o que se espera de quem paga,
por faixa de risco e por faixa do Daniel, com o ajuste pelo histórico (`historico.json`) e a política atual como
referência.

## Revisão do analista (`/revisao/`)

Login com e-mail e senha (Supabase Auth, cadastro público fechado), fila de pedidos com filtros (sem revisão,
diferente da política atual, revisadas), sugestão da IA com motivo e risco, bureau ao vivo pela Edge Function e
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
| `scripts/historico.py` | Proposta nos 10.000 pedidos do histórico → `src/data/historico.json` |
| `scripts/paridade-motor.mjs` | confere o motor TS contra o Python nos 2.000 novos (`node --experimental-strip-types`) |
| `src/lib/motor.ts` | política e modelo da Proposta no navegador (Revisão e Simulador) |
| `scripts/bureau_client.py` | cliente da API com retry, cache e registro |
| `scripts/csp.mjs` | grava a CSP em cada HTML depois do build |
| `src/components/` | cartões do painel (funil, volume, safras, pontos, padrões, API, comparativo) |
| `src/app/globals.css` | tokens do Material Design 3 (tema claro) e layout |
