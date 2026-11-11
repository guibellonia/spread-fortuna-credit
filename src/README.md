# Time Spread · Desafio Fortuna Crédito (Hackathon GOW 2026)

Pré-requisitos: PostgreSQL 16 com o dump restaurado no banco `fortuna` e Python 3.12 com
`pip install pandas scikit-learn psycopg2-binary requests joblib`.

A conexão vem de `FORTUNA_DSN` ou do arquivo `../pg16-local.txt`.

## Gerar o arquivo de decisões do zero

```bash
export FORTUNA_BUREAU_TOKEN=<token do time>
cd src
python gerar_decisoes.py          # treina, consulta o bureau (com retry e cache) e grava saida/spread_final.csv
python validar_csv.py ../saida/spread_final.csv
python painel.py                  # gera saida/painel.html
```

## Ferramentas (determinísticas, para o agente chamar)

| Arquivo | O que faz |
|---|---|
| `features.py` | Monta atributos por pedido: cadastro, movimentação da conta e bureau |
| `padroes.py` | Padrões de inadimplência por grupo e combinações via árvore de decisão |
| `modelo.py` | Modelo de risco (em dia / atraso / não paga) que depende do valor aprovado |
| `politica.py` | Política atual (reproduzida) e política proposta, com parâmetros ajustáveis |
| `backtest.py` | Teste fora da amostra: treina até set/25 e compara as políticas em out/25–mar/26 |
| `bureau.py` | Cliente do bureau: retry com backoff em 503 e timeout, cache em disco, paralelo |
| `validar_csv.py` | Confere o CSV nas regras do manual |
| `painel.py` | Painel de experimentação para o analista de risco |

## Tools para o agente LLM (`tools.py`)

Todas devolvem JSON e todo número sai de código (o LLM interpreta e recomenda, não calcula).
Esquemas no formato de function calling (OpenAI-compatível): `from tools import TOOLS, executar`.

| Tool | O que faz |
|---|---|
| `politica_vigente` | parâmetros e passos da política proposta (cenário G) |
| `listar_padroes` | padrões por grupo e combinações da árvore, no formato do manual |
| `medir_grupo` | inadimplência projetada (corrigida de censura) com IC95 de um grupo definido por condições — para o LLM testar hipóteses |
| `consultar_pedido` | dados de um pedido novo |
| `decidir_pedido` | decisão, valor, motivo e probabilidades; e a decisão da política atual |
| `avaliar_pedido` | conselho de 4 modelos (opiniões, divergência, veredito) + fatores |
| `simular_politica` | resultado esperado de longo prazo de uma configuração (base, pessimista, otimista) vs atual |
| `comparar_politicas` | várias configurações lado a lado |
| `backtest_politica` | teste fora da amostra com desfecho observado |
| `pedidos_em_divergencia` | fila para o analista: onde os modelos discordam |
| `gerar_csv` | dry-run por padrão; só grava `saida/spread_final.csv` com `confirmar=true` (aprovação humana) |
| `validar_arquivo` | valida o CSV nas regras do manual |
| `explicar_modelo` | importância das variáveis (queda de AUC fora do tempo) e dependência parcial |
| `teste_sanidade` | atributos sensíveis usados, sonda de vazamento, disparidade por grupo (regra dos 80%) e monotonicidade |

Teste pela linha de comando:

```bash
python tools.py listar
python tools.py decidir_pedido '{"id_pedido": "P-00070"}'
python tools.py medir_grupo '{"condicoes": [{"campo": "r_saidas", "op": ">=", "valor": 0.8}]}'
```

Pré-requisito: rodar `gerar_decisoes.py` uma vez (monta `saida/hist.pkl`, `saida/novos.pkl` e o cache do bureau).

## Agente LLM e conselho de LLMs (`llm.py`, `agente.py`)

- **Fallback em duas camadas:** o OmniRoute é o principal e faz o fallback entre os modelos configurados nele;
  se o próprio OmniRoute cair, `llm.py` chama direto Z.ai (GLM), NVIDIA, Google (Gemini), OpenRouter (`:free`), Groq e Ollama.
- **Configuração:** só por variável de ambiente. Modelo em `src/llm.env.example`. Os ids de modelo padrão são
  palpites: confira no painel de cada provedor.
- **Regras do agente:** todo número vem de uma tool; `gerar_csv` com `confirmar=true` exige o analista digitar
  "aprovo"; cada chamada de tool fica em `saida/agente_log.jsonl` (auditoria).
- **Conselho de LLMs:** cada modelo de `CONSELHO_MODELOS` responde sozinho, com as tools; um presidente lista
  consenso, divergências, confere os números divergentes nas tools e dá a recomendação com o grau de concordância.

```bash
python llm.py                                   # provedores configurados
python agente.py "o score importa depois dos filtros?"
python agente.py --chat
python agente.py --conselho "vale subir o teto de parcela para 30%?"
```

## Pipeline (`.github/workflows/ci.yml`)

Roda em todo push e em todo pull request para a `main`:

| Job | O que confere | Bloqueia? |
|---|---|---|
| Segredos | nenhum `.env`, dump, cache do bureau, token (48 hex) ou chave de API versionados | sim |
| Lint | erros que quebram (sintaxe, nome indefinido); imports sem uso só avisam | sim |
| Testes | `pytest tests`: parcela Price, políticas, validador do CSV, bureau (retry/401), tools e agente | sim |
| Integração | com o segredo `FORTUNA_DSN` (Supabase): contagens do banco batem com o kit; sem o segredo, só avisa | sim, se configurado |
| CSV | todo `*_final.csv` e `decisoes_*.csv` versionado passa no validador (modo offline) | sim |

Banco: `src/db.py` e `validacao/db.py` leem `FORTUNA_DSN` (ex.: Supabase com `?sslmode=require`); sem ela, usam o
arquivo local. O schema precisa se chamar `hackathon`.

**Proteger a `main` (só o admin do repositório):** Settings → Branches → Add rule `main` → "Require a pull request
before merging" + "Require status checks to pass" (Segredos, Lint (Python), Testes, Formato dos CSVs de decisão).
Pelo terminal:

```bash
gh api -X PUT repos/guibellonia/spread-fortuna-credit/branches/main/protection --input - <<'JSON'
{"required_status_checks":{"strict":true,"contexts":["Segredos","Lint (Python)","Testes","Formato dos CSVs de decisão"]},
 "enforce_admins":false,"required_pull_request_reviews":{"required_approving_review_count":0},"restrictions":null}
JSON
```
