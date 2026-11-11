# Saída de g05b_modelo_em.py

## 6.1b Validação fora do tempo — modelo EM de PD de vida inteira

Treino (corte simulado 30/09/2025): 2,844 contratos, 165 paradas observadas até então, w médio 0.29. Teste: 1,820 contratos (1126 do piloto); 138 pararam até a 4ª parcela.

| modelo                        |   AUC até 4ª |   Brier até 4ª |   prevista até 4ª |   observada até 4ª |   PD vida prevista (média) |
|:------------------------------|-------------:|---------------:|------------------:|-------------------:|---------------------------:|
| Score sozinho (EM, logístico) |       0.6913 |         0.0668 |            0.066  |             0.0758 |                     0.1968 |
| Regressão logística (EM)      |       0.7869 |         0.0585 |            0.0678 |             0.0758 |                     0.1917 |
| Gradient boosting (EM)        |       0.7723 |         0.0572 |            0.0434 |             0.0758 |                     0.112  |

PD vida observada (KM) no teste: **19.8%** [16.7–22.9].

Calibração por quintil (gradient boosting EM, teste fora do tempo):

| quintil          |   n |   PD vida prevista |   PD vida KM | KM IC95    |   piloto % |
|:-----------------|----:|-------------------:|-------------:|:-----------|-----------:|
| Q1 (menor risco) | 364 |              0.008 |        0.097 | 3.1–16.3%  |      0.563 |
| Q2               | 364 |              0.019 |        0.074 | 3.0–11.8%  |      0.566 |
| Q3               | 364 |              0.038 |        0.072 | 3.3–11.1%  |      0.618 |
| Q4               | 364 |              0.083 |        0.104 | 6.1–14.7%  |      0.648 |
| Q5 (maior risco) | 364 |              0.412 |        0.517 | 44.3–59.2% |      0.698 |

## 6.3b Decisão no ponto de equilíbrio (nega se PD vida prevista > 17,5%)

Alvo observável: parou até a 4ª parcela. Precisão = dos negados, quantos pararam; recall = dos que pararam, quantos foram negados.

**Gradient boosting (EM)**: nega 16.2% · precisão 0.276 · recall 0.587 · F1 0.375 · PD vida (KM) dos aprovados 8.8% · dos negados 59.4%
|              |   aprova |   nega |
|:-------------|---------:|-------:|
| pagou até 4ª |     1469 |    213 |
| parou até 4ª |       57 |     81 |

**Regressão logística (EM)**: nega 29.8% · precisão 0.170 · recall 0.667 · F1 0.271 · PD vida (KM) dos aprovados 8.6% · dos negados 40.8%
|              |   aprova |   nega |
|:-------------|---------:|-------:|
| pagou até 4ª |     1232 |    450 |
| parou até 4ª |       46 |     92 |

**Score > 600 sozinho**: nega 15.3% · precisão 0.083 · recall 0.167 · F1 0.111 · PD vida (KM) dos aprovados 18.8% · dos negados 25.7%
|              |   aprova |   nega |
|:-------------|---------:|-------:|
| pagou até 4ª |     1427 |    255 |
| parou até 4ª |      115 |     23 |

**Regra da política atual**: nega 23.5% · precisão 0.108 · recall 0.333 · F1 0.163 · PD vida (KM) dos aprovados 17.2% · dos negados 28.5%
|              |   aprova |   nega |
|:-------------|---------:|-------:|
| pagou até 4ª |     1301 |    381 |
| parou até 4ª |       92 |     46 |


## 6.6b Modelo final (todos os 6.033 aprovados) — PD prevista vs KM por decil (na amostra)

|   decil |   n |   PD prevista |   PD KM | KM IC95     |   P(em dia) prevista |
|--------:|----:|--------------:|--------:|:------------|---------------------:|
|       1 | 604 |         0.019 |   0     | 0.0–0.0%    |                0.579 |
|       2 | 603 |         0.03  |   0     | 0.0–0.0%    |                0.59  |
|       3 | 603 |         0.037 |   0     | 0.0–0.0%    |                0.594 |
|       4 | 603 |         0.044 |   0     | 0.0–0.0%    |                0.594 |
|       5 | 604 |         0.052 |   0     | 0.0–0.0%    |                0.595 |
|       6 | 603 |         0.062 |   0     | 0.0–0.0%    |                0.589 |
|       7 | 603 |         0.076 |   0     | 0.0–0.0%    |                0.567 |
|       8 | 603 |         0.103 |   0.017 | 0.4–3.1%    |                0.547 |
|       9 | 603 |         0.216 |   0.375 | 32.5–42.5%  |                0.448 |
|      10 | 604 |         0.765 |   0.991 | 98.0–100.0% |                0.126 |

Média prevista 0.141 vs KM de todos 0.154.