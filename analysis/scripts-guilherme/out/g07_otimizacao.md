# Saída de g07_otimizacao.py

## 7.2 Grade de políticas (2.000 novos) — ordenada pelo pior ganho entre os avaliadores independentes

Volume e ganhos em R$ mil; PD em % do volume. Ganho = resultado − resultado da política atual (A) no MESMO avaliador.

| politica   |   aprovados |   volume |   reduzidos |   pd_modelo |   pd_km |   pd_tool |   ganho_modelo |   ganho_km |   ganho_tool |   ganho_min_indep |
|:-----------|------------:|---------:|------------:|------------:|--------:|----------:|---------------:|-----------:|-------------:|------------------:|
| A (time)   |        1145 |     8856 |          61 |        16.5 |    15.4 |      14.4 |              0 |          0 |            0 |                 0 |
| C (time)   |        1209 |     7968 |         467 |        10.4 |     8.6 |       8.1 |            344 |        384 |          353 |               353 |
| G (time)   |        1527 |    10220 |         478 |        10.7 |     8.5 |       8.1 |            370 |        526 |          501 |               501 |

| politica                                     |   aprovados |   volume |   reduzidos |   pd_modelo |   pd_km |   pd_tool |   ganho_modelo |   ganho_km |   ganho_tool |   ganho_min_indep |
|:---------------------------------------------|------------:|---------:|------------:|------------:|--------:|----------:|---------------:|-----------:|-------------:|------------------:|
| pd≤0.200 | reduz | só modelo | score>0       |        1507 |     9729 |        1223 |         7   |     9.3 |       8   |            605 |        436 |          483 |               436 |
| pd≤0.250 | reduz | só modelo | score>0       |        1507 |     9729 |        1223 |         7   |     9.3 |       8   |            605 |        436 |          483 |               436 |
| pd≤0.175 | reduz | só modelo | score>0       |        1507 |     9729 |        1223 |         7   |     9.3 |       8   |            605 |        436 |          483 |               436 |
| pd≤0.160 | reduz | só modelo | score>0       |        1506 |     9719 |        1222 |         7   |     9.3 |       8   |            605 |        436 |          482 |               436 |
| pd≤0.140 | reduz | só modelo | score>0       |        1493 |     9651 |        1209 |         7   |     9.3 |       7.9 |            604 |        432 |          479 |               432 |
| pd≤0.160 | sem reduzir | só modelo | score>0 |        1441 |     9722 |           0 |         7.8 |     9.4 |       8.1 |            561 |        428 |          471 |               428 |
| pd≤0.250 | sem reduzir | só modelo | score>0 |        1446 |     9740 |           0 |         7.9 |     9.5 |       8.1 |            561 |        428 |          471 |               428 |
| pd≤0.200 | sem reduzir | só modelo | score>0 |        1446 |     9740 |           0 |         7.9 |     9.5 |       8.1 |            561 |        428 |          471 |               428 |
| pd≤0.175 | sem reduzir | só modelo | score>0 |        1446 |     9740 |           0 |         7.9 |     9.5 |       8.1 |            561 |        428 |          471 |               428 |
| pd≤0.140 | sem reduzir | só modelo | score>0 |        1412 |     9540 |           0 |         7.7 |     9.4 |       8.1 |            559 |        421 |          462 |               421 |
| pd≤0.120 | reduz | só modelo | score>0       |        1449 |     9329 |        1167 |         6.8 |     9.2 |       7.9 |            599 |        418 |          462 |               418 |
| pd≤0.120 | sem reduzir | só modelo | score>0 |        1354 |     9095 |           0 |         7.5 |     9.3 |       7.9 |            551 |        401 |          442 |               401 |
| pd≤0.200 | reduz | regras | score>0          |        1328 |     8608 |        1114 |         7.1 |     8.9 |       7.9 |            568 |        397 |          417 |               397 |
| pd≤0.250 | reduz | regras | score>0          |        1328 |     8608 |        1114 |         7.1 |     8.9 |       7.9 |            568 |        397 |          417 |               397 |
| pd≤0.175 | reduz | regras | score>0          |        1328 |     8608 |        1114 |         7.1 |     8.9 |       7.9 |            568 |        397 |          417 |               397 |
| pd≤0.160 | reduz | regras | score>0          |        1327 |     8598 |        1113 |         7.1 |     8.9 |       7.9 |            568 |        396 |          416 |               396 |
| pd≤0.160 | sem reduzir | regras | score>0    |        1279 |     8696 |           0 |         8   |     9.1 |       8.1 |            527 |        392 |          410 |               392 |
| pd≤0.175 | sem reduzir | regras | score>0    |        1284 |     8713 |           0 |         8   |     9.1 |       8.1 |            527 |        392 |          411 |               392 |
| pd≤0.250 | sem reduzir | regras | score>0    |        1284 |     8713 |           0 |         8   |     9.1 |       8.1 |            527 |        392 |          411 |               392 |
| pd≤0.200 | sem reduzir | regras | score>0    |        1284 |     8713 |           0 |         8   |     9.1 |       8.1 |            527 |        392 |          411 |               392 |

Resultado absoluto da política atual por avaliador (R$ mil): modelo -77, km 143, tool 193

## Fronteira de eficiência (regras + modelo, com redução de valor, sem corte de score)

| politica                            |   aprovados |   volume |   pd_km |   pd_tool |   ganho_km |   ganho_tool |   ganho_modelo |
|:------------------------------------|------------:|---------:|--------:|----------:|-----------:|-------------:|---------------:|
| pd≤0.080 | reduz | regras | score>0 |         979 |     6223 |     8.6 |       7.4 |        264 |          271 |            486 |
| pd≤0.100 | reduz | regras | score>0 |        1173 |     7588 |     8.7 |       7.6 |        341 |          361 |            545 |
| pd≤0.120 | reduz | regras | score>0 |        1272 |     8241 |     8.9 |       7.8 |        376 |          397 |            562 |
| pd≤0.140 | reduz | regras | score>0 |        1314 |     8530 |     8.9 |       7.8 |        392 |          413 |            567 |
| pd≤0.160 | reduz | regras | score>0 |        1327 |     8598 |     8.9 |       7.9 |        396 |          416 |            568 |
| pd≤0.175 | reduz | regras | score>0 |        1328 |     8608 |     8.9 |       7.9 |        397 |          417 |            568 |
| pd≤0.200 | reduz | regras | score>0 |        1328 |     8608 |     8.9 |       7.9 |        397 |          417 |            568 |
| pd≤0.250 | reduz | regras | score>0 |        1328 |     8608 |     8.9 |       7.9 |        397 |          417 |            568 |

Mesma fronteira, SEM reduzir valor (aprova o pedido inteiro ou nega):

| politica                                  |   aprovados |   volume |   pd_km |   pd_tool |   ganho_km |   ganho_tool |   ganho_modelo |
|:------------------------------------------|------------:|---------:|--------:|----------:|-----------:|-------------:|---------------:|
| pd≤0.080 | sem reduzir | regras | score>0 |         797 |     5141 |     8.5 |       7.1 |        197 |          199 |            399 |
| pd≤0.100 | sem reduzir | regras | score>0 |        1062 |     7023 |     8.7 |       7.5 |        310 |          325 |            485 |
| pd≤0.120 | sem reduzir | regras | score>0 |        1195 |     8103 |     8.9 |       7.8 |        362 |          383 |            517 |
| pd≤0.140 | sem reduzir | regras | score>0 |        1251 |     8521 |     9.1 |       8   |        381 |          402 |            525 |
| pd≤0.160 | sem reduzir | regras | score>0 |        1279 |     8696 |     9.1 |       8.1 |        392 |          410 |            527 |
| pd≤0.175 | sem reduzir | regras | score>0 |        1284 |     8713 |     9.1 |       8.1 |        392 |          411 |            527 |
| pd≤0.200 | sem reduzir | regras | score>0 |        1284 |     8713 |     9.1 |       8.1 |        392 |          411 |            527 |
| pd≤0.250 | sem reduzir | regras | score>0 |        1284 |     8713 |     9.1 |       8.1 |        392 |          411 |            527 |

**Política com maior ganho mínimo independente:** `pd≤0.200 | reduz | só modelo | score>0` → out/g07_decisoes_recomendadas.csv

### Onde a recomendada difere da atual (A) e do G do time

|   aprova A e recomendada |   só A aprova |   só recomendada aprova |   aprova G e recomendada |   só G aprova |   só recomendada (vs G) |
|-------------------------:|--------------:|------------------------:|-------------------------:|--------------:|------------------------:|
|                      976 |           169 |                     531 |                     1307 |           220 |                     200 |

Dos 169 que só A aprova, quantos caem em cada regra (um pedido pode cair em várias):
|                   |   pedidos |
|:------------------|----------:|
| outras_40pct      |        51 |
| saidas_80pct      |        24 |
| deficit_3m        |        24 |
| deficit_2m_12m    |        22 |
| cheque_2m_12m     |        21 |
| renda_conta_60pct |         9 |
| restricao         |         0 |

A política atual reduz o valor de 61 pedidos aprovados; a recomendada aprova 2 deles.

## 8. Rentabilidade (regra do desafio: +15% em dia, +5% atraso, −60% não paga)

|                                           |   A (time) |   G (time) |   pd≤0.200 | reduz | só modelo | score>0 |
|:------------------------------------------|-----------:|-----------:|-----------------------------------------:|
| resultado KM (R$ mil)                     |   143      |   669      |                                 579      |
| por R$ concedido (KM)                     |     0.0161 |     0.0655 |                                   0.0595 |
| por cliente aprovado (KM, R$)             |   125      |   438      |                                 384      |
| resultado tool_risco (R$ mil)             |   193      |   694      |                                 676      |
| por R$ concedido (tool_risco)             |     0.0218 |     0.0679 |                                   0.0695 |
| por cliente aprovado (tool_risco, R$)     |   169      |   455      |                                 448      |
| resultado modelo próprio (R$ mil)         |   -77      |   293      |                                 528      |
| por R$ concedido (modelo próprio)         |    -0.0087 |     0.0287 |                                   0.0543 |
| por cliente aprovado (modelo próprio, R$) |   -67      |   192      |                                 350      |