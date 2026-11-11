# Hermes Agent + OmniRoute + tools do time

```
Analista ─▶ Hermes Agent ─▶ OmniRoute (combo com fallback: Hermes, Gemini, GLM, Llama, Nemotron...)
                 │
                 └─▶ servidor MCP `spread` (src/mcp_server.py) ─▶ 14 tools determinísticas ─▶ banco / modelos
```

O LLM interpreta e recomenda; todo número sai das tools. Gravar o CSV de entrega exige aprovação humana.

## Montar (uma vez por máquina)

1. **OmniRoute:** `docker compose -f hermes/docker-compose.omniroute.yml up -d` (ou `npm i -g omniroute && omniroute`).
   No painel `http://localhost:20128`: cadastre os provedores com as chaves gratuitas, crie o combo `spread` e gere
   uma chave de API do OmniRoute.
2. **Hermes Agent:** instale pela documentação oficial (hermes-agent.nousresearch.com). Copie
   `hermes/config.example.yaml` para `~/.hermes/config.yaml` e ajuste os `<...>`. A chave do OmniRoute vai em
   `~/.hermes/.env` (`OPENAI_API_KEY=...`).
3. **Contexto:** use `hermes/contexto.md` como instrução do agente.
4. **Dados:** rode `python src/gerar_decisoes.py` uma vez (monta `saida/hist.pkl`, `saida/novos.pkl` e o cache do
   bureau) e `python -c "import tool_risco; tool_risco.treinar()"` dentro de `validacao/`.
5. **Teste:** no Hermes, `/reload-mcp` e pergunte "como a política decide?". Ele deve chamar `politica_vigente`.

Sem o Hermes Agent, o mesmo fluxo roda com `python src/agente.py --chat`, que usa as mesmas tools e o OmniRoute.

## Onde ficam as chaves

| Onde roda | Onde colocar | Quem coloca |
|---|---|---|
| Máquina de cada pessoa | `.env` local, `~/.hermes/.env` e painel do OmniRoute | cada pessoa |
| CI (GitHub Actions) | Settings → Secrets and variables → Actions (`FORTUNA_DSN`) | admin do repositório |
| Produção (servidor) | variáveis de ambiente do servidor, injetadas pelo workflow de deploy a partir dos Secrets | admin |

**Nunca dentro do build:** chave gravada em imagem, arquivo ou página publicada vaza para quem tiver o artefato, e
este repositório é público. O CI barra commit com chave.

**Produção ainda não existe:** falta escolher o servidor (máquina do time com Docker, Railway, Render ou Azure
Container Apps). Escolhido o servidor, o workflow de deploy lê os Secrets e configura o ambiente dele.

## Deploy no Railway (`.github/workflows/deploy-hermes.yml`)

A cada CI verde na `main`, o workflow copia os Secrets do GitHub para as variáveis do serviço no Railway e faz o
deploy com `hermes/Dockerfile`. A imagem não leva nenhuma chave nem dado: no primeiro start, a API monta a base a
partir do Supabase e do bureau (`src/bootstrap.py`); `/health` responde 503 até terminar.

Uma vez, no Railway: dentro do projeto, **New → Empty Service** com o nome `hermes` (outro nome: variável de
repositório `RAILWAY_SERVICE`). Em **Settings → Networking → Generate Domain**, gere a URL pública.

Secrets necessários (Settings → Secrets and variables → Actions):

| Secret | Para quê |
|---|---|
| `RAILWAY_TOKEN` | token do projeto no Railway |
| `HERMES_ACCESS_KEY` | chave que quem usa a API manda no cabeçalho `X-Access-Key`; gere com `openssl rand -hex 24` |
| `FORTUNA_DSN` | Supabase, papel só de leitura |
| `FORTUNA_BUREAU_TOKEN` | API do bureau (só no primeiro start) |
| `GROQ_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY` | pelo menos uma |

Uso:

```bash
curl https://<url-do-railway>/health
curl -X POST https://<url-do-railway>/perguntar -H "X-Access-Key: <HERMES_ACCESS_KEY>" -H "Content-Type: application/json" -d '{"pergunta":"como a política decide?"}'
curl -X POST https://<url-do-railway>/tools/decidir_pedido -H "X-Access-Key: <HERMES_ACCESS_KEY>" -H "Content-Type: application/json" -d '{"id_pedido":"P-00070"}'
```

A API não grava o CSV de entrega (403), recusa tudo sem `HERMES_ACCESS_KEY` e atende até 2 perguntas ao agente por vez
(`HERMES_CONCORRENCIA`).
