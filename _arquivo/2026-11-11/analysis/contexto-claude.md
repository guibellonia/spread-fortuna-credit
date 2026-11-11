# Contexto: Hackathon GOW 2026 · Desafio Fortuna Crédito · Time Spread

Você vai ajudar o time **Spread** num hackathon da GOW (11/11/2026). "Spread" é só o nome do time:
o desafio é o mesmo para os 5 times. Isto é um evento da GOW e não tem relação com a Kyte.

## O desafio
A Fortuna Crédito (fintech fictícia, crédito pessoal até R$ 30 mil, juros de 3% a.m., parcela pela tabela Price:
parcela = valor × 0,03 / (1 − 1,03^(−prazo))) quer que a IA encontre padrões no histórico e proponha uma política
de aprovação e de valor melhor que a atual. A IA precisa participar da descoberta dos padrões e da decisão;
usar IA só para escrever código não conta. A IA sugere e o analista de risco decide.

Política atual: score > 600, renda > R$ 2.000, sem restrição ativa, parcela ≤ 30% da renda.
Achado nosso: quando a parcela passa de 30%, a política atual **reduz o valor** até a parcela caber em exatamente
30% da renda, em vez de negar.

## Entregas e prazos
- **CSV de decisões** `spread_final.csv`: UTF-8 sem BOM, separador vírgula, cabeçalho exato
  `id_pedido,decisao,valor_aprovado`, decisao = APROVADO/NEGADO (maiúsculas), valor com 2 casas e ponto
  (0.00 se negado), valor ≤ solicitado e ≤ 30000. Precisa ser gerado por código (CSV editado à mão desclassifica).
  Checkpoint até 14h15 e envio final até **15h30 sem tolerância**, na pasta do time no Teams.
- **Painel de experimentação** para o analista de risco. Parte 1: padrões no formato "Clientes com [X] têm
  inadimplência de N%, contra M% da média. Afeta K clientes." Parte 2: política em passos ordenados.
- **Pitch** de 5 min às 15h45: onde a IA entra, os padrões, a política, o que mudou após o checkpoint e como o
  analista valida.
- Código com README (conta a favor em qualidade técnica).

## Nota
- 40%: ganho financeiro sobre a política atual nos 2.000 pedidos novos. Por pedido aprovado: +15% do valor se
  pagou em dia, +5% se pagou com atraso, −60% se não pagou; negado = 0. O desfecho depende do valor aprovado.
- 25%: padrões. 15%: pitch. 10%: painel. 10%: qualidade técnica (inclui tratar falhas do bureau).

## Dados
PostgreSQL 16, banco `fortuna`, schema `hackathon` (na máquina do Juliano: localhost:5433, usuário postgres;
pedir a senha a ele). Tabelas:
- `pedidos`: 10.000 com tipo_base='historico' (out/24–set/26) e 2.000 com tipo_base='novo' (out/26).
- `clientes`, `movimentacao_mensal` (12 meses antes do pedido) e `bureau` (só no histórico).
- `parcelas`: só dos históricos aprovados.
- Data de corte: 30/09/2026. Muitos contratos ainda estão abertos.
- Valores de `decisao` e `situacao_final` no banco ficam em minúsculas.

Bureau dos novos pedidos: `GET https://gowlab-fortuna-bureau.azurewebsites.net/v1/bureau/{id_cliente}` com
`Authorization: Bearer <token>`. A consulta usa o id_cliente, não o id_pedido. Falha com 503 e demora de propósito.
O token fica na variável de ambiente `FORTUNA_BUREAU_TOKEN`; nunca grave em arquivo nem em commit.

## O que já está pronto (pasta `Downloads\material\spread`, repo https://github.com/guibellonia/spread-fortuna-credit)
Arquitetura inspirada no "Caronte": um LLM (Hermes, via OmniRoute + Z.ai, **ainda não configurado**) chama
ferramentas determinísticas em Python, que ficam em `src/`:
- `features.py`: atributos por pedido (parcela/renda, sobra mensal, meses com saldo negativo, bureau etc.).
- `padroes.py`: padrões por grupo e combinações via árvore de decisão; grava `saida/padroes.json`.
- `modelo.py`: classificador HistGradientBoosting em 3 classes (em dia / atraso / não paga), treinado com aprovados
  até 31/03/2026 (contratos com 6+ meses). Os atributos dependem do valor aprovado. AUC 0,78 em validação temporal.
- `politica.py`: política atual reproduzida e política proposta com PARAMS ajustáveis.
- `backtest.py`: treina até set/25 e compara as políticas em out/25–mar/26.
- `bureau.py`: retry com backoff e jitter em 503/timeout, 16 chamadas em paralelo, cache em
  `saida/bureau_cache.json`, 401 interrompe.
- `gerar_decisoes.py`: fluxo completo; grava `saida/spread_final.csv` e `saida/decisoes_detalhadas.csv`.
- `validar_csv.py`: confere o CSV nas regras do manual.
- `painel.py`: gera `saida/painel.html`.
- Para rodar: `cd src && python gerar_decisoes.py && python validar_csv.py ../saida/spread_final.csv && python painel.py`
  (Python 3.12 com pandas, scikit-learn, psycopg2-binary, requests e joblib).

## Política proposta (atual)
1. Nega se há restrição ativa no bureau.
2. Nega se houve 2 ou mais meses com saldo negativo nos últimos 12.
3. Parcela limitada a 20% da renda declarada; acima disso, reduz o valor.
4. Para cada valor de 100% a 10% do solicitado, o modelo estima as chances de cada desfecho. Aprova o valor de maior
   ganho esperado (0,15·P(em dia) + 0,05·P(atraso) − 0,60·P(não paga)), com P(não paga) ≤ 20%. Sem ganho positivo, nega.
5. Valor mínimo de R$ 500, máximo de R$ 30 mil, nunca acima do solicitado.

Backtest: cerca de **+R$ 202 mil** sobre a atual (R$ 504 mil → R$ 706 mil). A conta é conservadora: aprovações de
pedidos negados na época contam como zero.

CSV real gerado e validado: **1.550 aprovados de 2.000, R$ 10,16 milhões**. A política atual aprovaria 1.145
(R$ 8,86 milhões). A proposta difere da atual em 497 pedidos e reduziu o valor em 575 aprovações.
Negações: restrição (377), saldo negativo (38), risco ou ganho (35).

## Padrões principais (aprovados com 6+ meses; inadimplência média de 12%)
- 2+ meses com saldo negativo: 64% (135 clientes).
- Parcela entre 25% e 30% da renda: 45% (318). Acima de 20%: 37% (562).
- Parcela/renda até 28% e sobra mensal até R$ 565: 75% (116). Parcela/renda até 28%, sobra > R$ 565 e entradas
  estáveis: 7% (3.774).
- Prazo de 6 meses: 26%. Prazo de 36 meses: 7%.
- Sobra mensal < R$ 1.750: 24%. Mais de 3 consultas ao CPF em 90 dias: 23%. Restrição (piloto): 20%.
- Empresário: 17%. Aposentado: 8%.
- **Score não separa bons e maus pagadores:** score ≤ 600 aprovado no piloto teve 13%, igual à média.
  A regra de score > 600 nega quem pagaria.

## Pendências
- Ligar o agente LLM (Hermes/OmniRoute/Z.ai) às ferramentas, para explicar padrões, responder ao analista e
  propor ajustes de PARAMS. Esperar o time configurar.
- Perguntar à Fortuna como contratos abertos (em_dia/em_atraso) viram desfecho na nota.
- Validar o CSV no Teams até 14h15 e entregar até 15h30.
- Responder em português do Brasil, de forma direta.
