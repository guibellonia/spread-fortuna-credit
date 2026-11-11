# Saída de g05_modelo.py

## 6.1 Validação fora do tempo (treino: pedidos até set/25 com corte simulado; teste: out/25–mar/26)

Treino: 2,844 contratos, 10,171 parcelas decididas, 165 paradas. Teste: 1,820 contratos (1126 do piloto), 138 pararam até a 4ª parcela (7.6%).

| modelo                            |   AUC (parou até 4ª) |    Brier |   prevista até 4ª |   observada até 4ª |   PD vida média prevista |
|:----------------------------------|---------------------:|---------:|------------------:|-------------------:|-------------------------:|
| Score do birô sozinho (logístico) |               0.6838 |   0.0681 |            0.0659 |             0.0758 |                   0.3076 |
| Regressão logística (hazard)      |               0.787  |   0.0614 |            0.0769 |             0.0758 |                   0.4304 |
| Gradient boosting (hazard)        |               0.7896 |   0.0571 |            0.0708 |             0.0758 |                   0.2937 |
| Regra da política atual (nega=1)  |               0.5534 | nan      |          nan      |           nan      |                 nan      |

PD vida observada (KM) no teste: 19.8% [16.7–22.9] — comparar com a PD vida média prevista.

## 6.2 Calibração (gradient boosting, teste fora do tempo)

| quintil          |   n |   prevista até 4ª |   observada até 4ª |   PD vida prevista |   PD vida KM | KM IC95    |
|:-----------------|----:|------------------:|-------------------:|-------------------:|-------------:|:-----------|
| Q1 (menor risco) | 365 |             0.046 |              0.055 |              0.137 |        0.085 | 5.4–11.7%  |
| Q2               | 363 |             0.041 |              0.041 |              0.192 |        0.109 | 4.8–16.9%  |
| Q3               | 364 |             0.048 |              0.033 |              0.233 |        0.068 | 1.3–12.4%  |
| Q4               | 364 |             0.044 |              0.036 |              0.286 |        0.113 | 4.3–18.3%  |
| Q5 (maior risco) | 364 |             0.176 |              0.214 |              0.621 |        0.688 | 59.2–78.4% |

## 6.3 Decisão pelo ponto de equilíbrio (nega se PD vida prevista > 17,5%) vs quem parou até a 4ª parcela

**Gradient boosting (hazard)**: precisão 0.080 · recall 0.855 · F1 0.147 · nega 80.5% do teste
|              |   aprova |   nega |
|:-------------|---------:|-------:|
| pagou até 4ª |      334 |   1348 |
| parou até 4ª |       20 |    118 |

**Regressão logística (hazard)**: precisão 0.079 · recall 0.862 · F1 0.145 · nega 82.9% do teste
|              |   aprova |   nega |
|:-------------|---------:|-------:|
| pagou até 4ª |      292 |   1390 |
| parou até 4ª |       19 |    119 |

**Regra da política atual**: precisão 0.108 · recall 0.333 · F1 0.163 · nega 23.5% do teste (sem a redução de valor)
|              |   aprova |   nega |
|:-------------|---------:|-------:|
| pagou até 4ª |     1301 |    381 |
| parou até 4ª |       92 |     46 |

## 6.4 Gênero, estado civil, região e idade acrescentam poder preditivo?

AUC sem demográficas 0.7896 · com demográficas 0.7870 (teste fora do tempo, n=1820).

## 6.5 O que o modelo usa (queda de AUC ao embaralhar cada atributo no teste)

| atributo          |   queda_AUC |
|:------------------|------------:|
| pss               |      0.1082 |
| score             |      0.0116 |
| cheq_dias_media   |      0.0104 |
| prazo_meses       |      0.0095 |
| meses_conta       |      0.0095 |
| consultas_90_dias |      0.006  |
| saldo_min         |      0.0057 |
| sal_share         |      0.0043 |
| comp_antes        |      0.0037 |
| saldo_medio       |      0.0037 |
| ent_cv            |      0.0036 |
| comp_decl_solic   |      0.0031 |
| sai_tend          |      0.0028 |
| comp_real_solic   |      0.0026 |
| renda_ratio       |      0.0024 |

## 6.6 Modelo final (todos os aprovados): PD vida prevista vs KM por decil (dentro da amostra)

|   decil |   n |   PD prevista |   PD KM |   P(em dia) prevista |
|--------:|----:|--------------:|--------:|---------------------:|
|       1 | 605 |         0.063 |   0.019 |                0.738 |
|       2 | 603 |         0.071 |   0.015 |                0.736 |
|       3 | 602 |         0.075 |   0.039 |                0.73  |
|       4 | 603 |         0.079 |   0.043 |                0.728 |
|       5 | 604 |         0.084 |   0.04  |                0.724 |
|       6 | 603 |         0.091 |   0.077 |                0.715 |
|       7 | 603 |         0.102 |   0.09  |                0.696 |
|       8 | 603 |         0.122 |   0.088 |                0.661 |
|       9 | 603 |         0.181 |   0.243 |                0.606 |
|      10 | 604 |         0.729 |   0.859 |                0.207 |

Média prevista 0.160 vs KM de todos 0.154.