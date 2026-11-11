# Painel do time Spread

Painel web dos 2.000 pedidos novos da Fortuna: funil de cada política, volume aprovado, inadimplência por safra,
perfil do bureau, padrões no formato do manual e a saúde da integração com a API do bureau.

Next.js 16 (App Router) com export estático, publicado pelo GitHub Actions em
`https://guibellonia.github.io/spread-fortuna-credit/dashboard/`. A página do time continua na raiz.

## Como os dados chegam ao painel

```
banco (localhost) ─┐
                   ├─► scripts/snapshot.py ─► src/data/dashboard.json ─► git push ─► Actions ─► Pages
API do bureau ─────┘     (token só aqui)          (só agregados)
```

1. `scripts/snapshot.py` lê o banco, consulta o bureau para os 2.000 clientes novos e grava
   `src/data/dashboard.json`.
2. O JSON é versionado. O push na `main` dispara o build e a publicação.

### Atualizar os dados

Da raiz do repositório, com o `.env` preenchido (modelo em `.env.example`):

```
.venv/Scripts/python -m pip install -r site/scripts/requirements.txt   # uma vez
.venv/Scripts/python site/scripts/snapshot.py
git add site/src/data/dashboard.json && git commit -m "painel: atualiza dados" && git push
```

O script confere a política atual contra o histórico (hoje: 100% das decisões e valores) e imprime o resumo de
cada política. Para mudar ou incluir uma política, edite `politicas()` em `scripts/snapshot.py`: cada uma é uma
lista de passos em ordem, e o funil do painel segue essa ordem.

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

## Segurança

- **O token nunca sai da máquina do time.** Ele só é lido do `.env` pelo script de snapshot. O build não recebe
  segredo nenhum, e o site publicado não chama a API autenticada.
- **Só agregados vão para o site** (o repositório é público). O snapshot e o workflow param se encontrarem um id de
  cliente ou de pedido (`C-…`, `P-…`).
- **Content-Security-Policy** em cada página (`scripts/csp.mjs`): scripts só do próprio site, com hash para os
  inline do Next; conexões só para o próprio site e para o bureau; sem `object`, `frame`, `form` ou `base`.
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
