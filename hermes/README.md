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
