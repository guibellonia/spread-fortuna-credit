# Baseline da API do bureau · agregado

Medido em 11/11/2026 com `bureau_baseline.py`: 300 chamadas a clientes novos sorteados (semente 42), mais 77
repetições de checagem. **Sem retry**, para medir a API crua.

## Resultado

| | 10 em paralelo (200 chamadas) | Uma por vez (100 chamadas) |
|---|---|---|
| **Sucesso (200)** | 94,5% | 94,0% |
| **Falha 503** | 5,5% | 6,0% |
| Timeout ou erro de rede | 0 | 0 |
| Latência p50 | 0,19s | 0,21s |
| p90 | 0,38s | 0,39s |
| p95 | 1,75s | 0,87s |
| p99 | 3,71s | 4,93s |
| Mais lenta | 4,01s | 4,93s |
| Chamadas acima de 1s | 15 (7,5%) | 4 (4%) |
| Vazão | **22,6 por segundo** | 2,8 por segundo |

Bate com a consulta completa do Enio aos 2.000 clientes: 113 erros 503 em 2.113 tentativas (5,3%).

## O que se aprendeu

- **O 503 é sorteado a cada chamada, não fica preso a um cliente.** Dos clientes que falharam, 16 de 17
  responderam na segunda tentativa. E, em cada rodada, 3 de 30 clientes que tinham respondido falharam quando
  repetidos.
- **A resposta de um cliente nunca muda:** 27 de 27 repetições vieram idênticas. Dá para guardar em cache.
- **A lentidão vem em picos:** a maioria responde em ~0,2s, e ~5% demoram entre 1 e 5s. Uma chamada lenta pode
  terminar em 200 ou em 503.
- **10 em paralelo não aumentou a taxa de erro** e foi 8 vezes mais rápido: os 2.000 clientes levam ~1,5 minuto.
- **Só existe um corpo de erro:** `503 {"erro":"bureau temporariamente indisponível"}`. Sem token:
  `401 {"erro":"token ausente ou inválido"}`.
- **Amostra de 189 clientes novos:** score de 394 a 979 (mediana 733); 34 (18%) com alguma restrição ativa.

## Configuração recomendada para o cliente da API

| Item | Valor | Por quê |
|---|---|---|
| Timeout | 10s | o dobro da resposta mais lenta vista (4,9s) |
| Retry | só em 503, timeout e erro de rede | 401 e 404 indicam erro de configuração ou de dados, não de disponibilidade |
| Espera entre tentativas | 0,5s, 1s, 2s, 4s... com variação aleatória | não bater na API em rajada |
| Máximo de tentativas | 6 | com 6% de falha por chamada, falhar 6 vezes seguidas tem chance de ~1 em 20 milhões |
| Paralelismo | 10 | mesma taxa de erro, 8× mais rápido |
| Cache | em disco, por `id_cliente` | resposta não muda; rodar de novo só busca quem faltou |
| Registro | falhas por cliente e quantidade de tentativas | serve de evidência de "falha tratada" na nota técnica |

## Como refazer

Da raiz do repositório, com o `.env` preenchido (modelo em `.env.example`):

```
.venv/Scripts/python api-baseline/bureau_baseline.py 200 10
.venv/Scripts/python api-baseline/bureau_baseline.py 100 1
```

Cada execução faz o número pedido mais até 60 repetições de checagem, todas registradas no nome do time.
