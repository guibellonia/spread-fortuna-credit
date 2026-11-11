# Análise do banco Fortuna · Time Spread

Fonte: banco `fortuna`, schema `hackathon` (dump do Hackathon GOW 2026). Data de corte: 30/09/2026.

## 1. O que tem no banco
- **10.000 pedidos históricos**, de outubro de 2024 a setembro de 2026.
- **2.000 pedidos novos**, de outubro de 2026, ainda sem decisão.
- Cada cliente tem um único pedido. Também há 12 meses de movimentação da conta antes de cada pedido e o bureau dos
  pedidos históricos.
- Os pedidos novos se parecem com os históricos: valor médio pedido de R$ 7,7 mil (R$ 8,1 mil no histórico), renda
  mediana de R$ 4,4 mil, score médio de 722 e prazo de 24 meses. Por isso, o que se aprendeu no histórico vale para
  os novos.

## 2. Como a Fortuna decidiu
- Aprovou 60% dos pedidos: 56% pela política atual e 89% pelo piloto. No total, R$ 48 milhões emprestados.
- **A política atual reduz o valor em vez de negar.** Se a parcela passa de 30% da renda, ela corta o valor até a
  parcela caber em exatamente 30%. Isso aparece nos dados e não está no manual.

## 3. O desfecho dos aprovados
- Dos 6.033 aprovados, 4.523 contratos ainda estavam abertos na data de corte.
- Contratos recentes parecem bons só porque ainda não houve tempo de atrasar. Os de 2026 têm 0% a 1% de
  inadimplência, contra cerca de 15% nos de 2024.
- Por isso, os padrões usam só contratos com **6 meses ou mais** (4.664 contratos). Neles, a inadimplência média é
  **12%** e o atraso, 22%.

## 4. Padrões encontrados

| Grupo | Inadimplência (média de 12%) | Clientes |
|---|---|---|
| 2 ou mais meses com saldo negativo na conta | **64%** | 135 |
| Parcela entre 25% e 30% da renda | **45%** | 318 |
| Parcela acima de 20% da renda | 37% | 562 |
| Prazo de 6 meses | 26% | 246 |
| Sobra mensal (entradas menos saídas) abaixo de R$ 1.750 | 24% | 939 |
| Mais de 3 consultas ao CPF em 90 dias | 23% | 446 |
| Restrição ativa no bureau (aprovados no piloto) | 20% | 127 |
| Empresário | 17% | 475 |
| Prazo de 36 meses | **7%** | 1.179 |
| Aposentado | **8%** | 490 |
| Score até 600 (aprovados no piloto) | 13%, igual à média | 278 |

Combinações encontradas pela árvore de decisão:
- Parcela até 28% da renda e sobra mensal até R$ 565: **75%** de inadimplência (116 clientes).
- Parcela até 28% da renda, sobra acima de R$ 565 e entradas estáveis: **7%** (3.774 clientes).

## 5. Onde a política atual erra
1. **Exige score acima de 600, mas o score não prevê quem paga.** Ela nega clientes que pagariam.
2. **Aceita parcela de até 30% da renda.** A faixa de 25% a 30% é justamente a de maior risco, e a redução automática
   de valor empurra o cliente para lá.
3. **Ignora a conta corrente,** que traz os sinais mais fortes: saldo negativo frequente e pouca sobra no mês.
4. **Não diferencia prazos.** Prazos curtos, com parcela mais alta, inadimplem mais.

## 6. Política proposta aplicada aos 2.000 novos

| | Política atual | Proposta |
|---|---|---|
| Aprovados | 1.145 | **1.550** |
| Volume aprovado | R$ 8,86 milhões | R$ 10,16 milhões |

- A proposta aprova 451 pedidos que a atual negaria e nega 46 que ela aprovaria.
- Em 575 aprovações, o valor foi reduzido para baixar o risco.
- Motivos das 450 negações: restrição no bureau (377), 2 ou mais meses com saldo negativo (38) e risco ou ganho
  esperado ruim (35).
- **Teste fora da amostra:** o modelo foi treinado só com pedidos até setembro de 2025 e aplicado aos de outubro de
  2025 a março de 2026. Nesse período, a proposta rende **cerca de R$ 202 mil a mais** que a política atual, uns 40%
  a mais. O modelo separa bem os casos de inadimplência (AUC 0,78).

## 7. Pontos de atenção
- **Só se conhece o desfecho de quem foi aprovado.** O que se sabe sobre clientes negados vem do piloto, que tem só
  1.126 aprovações.
- **O efeito de reduzir o valor é uma estimativa do modelo.** No histórico, 94% dos aprovados receberam o valor que
  pediram, então há pouco dado para medir isso.
- **Pergunta para a Fortuna:** como contratos ainda abertos entram nos desfechos "pagou em dia", "pagou com atraso" e
  "não pagou" usados na nota.
