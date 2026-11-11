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
