# Perfil socioeconômico, cruzamentos e segmentação · Guilherme

Gerado por `analysis/scripts-guilherme/g03_perfil.py` a partir de `out/base.pkl` (g02_base.py). PD = inadimplência de vida inteira por Kaplan-Meier no tempo relativo do contrato, IC 95% de Greenwood. Todas as taxas de inadimplência são condicionais à aprovação (viés de seleção: só aprovados têm desfecho; score ≤ 600 e restrição só existem no piloto de out/25–mar/26).

## Achados (resumo)

Referência: 6.033 aprovados do histórico, PD de vida 15,4% [14,3–16,6], margem +0,014 por R$.

1. **Os 2.000 novos têm o mesmo perfil dos históricos.** Gênero, região, vínculo, estado civil, idade, prazo, score e renda conta/declarada não mudam (qui² p ≥ 0,09). As exceções são pequenas: mais pedidos de renda 2–3k (+2,6 p.p., p = 0,028) e de valor < R$ 3 mil (+2,6 p.p., p = 0,030). O que se aprende no histórico vale para os novos.
2. **Gênero, estado civil, região e idade não têm sinal depois das variáveis financeiras.** No modelo de hazard por parcela (50.957 parcelas, 626 paradas), o bloco demográfico inteiro dá LR χ² = 12,3 com 17 g.l. (p = 0,78). A AUC fora da dobra vai de 0,7927 para 0,7932 na regressão logística e cai de 0,7922 para 0,7895 no boosting. As diferenças brutas somem com controle: viúvo tem 7,3% (n = 177) e 65+ tem 10,9% (n = 359), mas os dois são sobretudo aposentados, e gênero dá 15,6% × 15,1%. **Recomendação: não usar.** Não melhoram a previsão e trazem risco jurídico: LGPD art. 6º IX (não discriminação), art. 20 (revisão de decisão automatizada) e CEP como proxy de renda e raça. Ponto a monitorar: SP interior continua com 15,6% [9,7–21,5] (n = 235) no perfil financeiro limpo, contra ~8% nas outras regiões. Mas o bloco de região não é significativo (p = 0,70), são 10 comparações, e a renda mediana lá é R$ 3.350, a menor de todas.
3. **A capacidade média é igual em todos os perfis.** Em toda célula de vínculo × faixa de renda, a mediana de saídas/entradas é 0,32 e a de parcela pedida/renda é 0,10–0,11. O risco não está no perfil médio, está nas caudas: parcela > 28% da renda, conta no vermelho, renda que não aparece na conta.
4. **O vínculo tem sinal próprio, mesmo com comprometimento baixo.** Aposentado tem 10,7% [7,7–13,7] (n = 612), assalariado 14,7% [13,2–16,3] (n = 3.426), autônomo 17,5% [14,9–20,1] (n = 1.373) e empresário 19,9% [15,9–23,9] (n = 622, margem −0,019). Com parcela < 10% da renda, empresário ainda dá 17,3% (n = 320) e aposentado 5,2% (n = 291). É variável legítima de crédito (estabilidade de renda) e o modelo já a controla.
5. **A renda importa pelo comprometimento, não pela faixa em si.** Renda 2–3k tem 18,9% [15,8–22,0] (n = 1.045, margem −0,012) e 5–10k tem 13,6% [11,7–15,4] (n = 2.201). Com parcela < 20% da renda, todas as faixas ficam entre 8% e 15%. Com parcela de 28–40%, renda 2–5k sobe para 48–51% (n = 162 e 156). Entre as rendas abaixo de 3k, 18% pedem parcela > 28% da renda; nas rendas a partir de 5k, só 4–6%.
6. **Profissão é proxy de renda e vínculo.** Vai de 6,2% (gerente comercial, n = 69) a 31,1% (auxiliar de produção, n = 125) e 31,3% (motorista de aplicativo, n = 59). Os ICs se sobrepõem na maioria das 46 profissões. Não usar profissão diretamente.
7. **Score baixo é, na prática, cadastro novo no birô.** Dos 2.385 pedidos com score ≤ 600, 1.994 têm ≤ 12 meses de histórico no birô. Acima de 600 não há degrau: 601–700 dá 14,7%, 701–800 dá 15,3% e 800+ dá 15,1%. No piloto, que é a mesma safra:
   - score ≤ 600 **com finanças boas**: 9,6% [2,8–16,5] (n = 149), margem +0,046;
   - score > 600 com finanças boas: 6,0% [3,3–8,7] (n = 464);
   - score ≤ 600 **sem** finanças boas: 40,8% (n = 129).

   Nos novos há **235** pedidos de score ≤ 600 com finanças boas, todos negados pela política atual. É oportunidade para teste controlado, com teto de valor. O limite superior do IC (16,5%) fica perto do ponto de equilíbrio (~17,5%).
8. **Score alto não protege de comprometimento excessivo.** Score > 700 com parcela > 28% da renda estimada, ou (parcela + outras) > 50%, ou saídas ≥ 80% das entradas, ou renda conta < 60% da declarada: **46,1% [41,7–50,5]** (n = 746), margem −0,214. Sem esses sinais: 8,3% (n = 3.831). Nos novos são 273 pedidos; **a política atual aprova 141** (48 com valor reduzido). É o maior vazamento da política atual.
9. **Há segmentos com espaço para aumento de limite.** O segmento de bom histórico e baixa exposição tem 6,1% [4,3–7,8] (n = 1.173), margem +0,084. Os critérios: score > 600, sem restrição, ≤ 1 consulta em 90 dias, ≥ 60 meses no birô, (parcela + outras) < 30%, sem cheque especial e saídas < 60% das entradas. Aposentados com finanças boas têm 5,6% [2,7–8,5] (n = 363). Nos novos são 236 e 99 pedidos, quase todos já aprovados pela atual: o ganho aqui vem do valor, não de aprovar mais.
10. **Clusters (k-means, k = 6).** A silhueta fica ≤ 0,23: os clientes formam um contínuo. Mesmo assim, três grupos de risco extremo aparecem sozinhos:
    - **"conta no vermelho"** (saídas/entradas 1,02, 2 meses de déficit, 4,8 dias de cheque especial por mês, 6 consultas): 102 de 157 aprovados pararam, PD ≈ 100%. São 97 nos novos, 24 aprovados pela atual.
    - **"parcela pesada"** (parcela pedida/renda mediana 0,56): 63,9% [57,2–70,6] (n = 309). São 110 nos novos, 54 aprovados pela atual.
    - **"renda declarada não aparece na conta"** (renda conta/declarada 0,18): 73,6% (n = 41).

    O núcleo (score 771, finanças limpas) tem 8,3% [7,2–9,3] (n = 4.582). O cluster de **score baixo com cadastro novo no birô e finanças limpas** tem 10,8% [5,5–16,2] (n = 274), mas a taxa de aprovação é só 15,4%: são 339 nos novos e a atual aprova 11.
11. **"Renda pela conta < 60% da declarada" é quase só conta nova.** 304 dos 351 pedidos assim têm só 1–2 meses de movimentação. Dentro desses, PD 83,5% [67,8–99,2] (n = 43), contra 11,6% (n = 133) quando a renda aparece. Contas com 12 meses quase nunca têm esse sinal (38 pedidos). Leitura: "conta recém-aberta cuja renda declarada não entra". Conta com ≤ 3 meses tem 28,3% [19,9–36,6] (n = 168).
12. **Sinais de deterioração: os fortes já estão nos filtros conhecidos.** Brutos, cheque especial só nos últimos 3 meses dá 76,5% (n = 186) e saídas/entradas 3m ≥ 90% dá ~100% (n = 156). Mas, depois dos filtros conhecidos (base limpa com 5.256 contratos e 8,8%), o cheque novo não acrescenta nada (9,3%, n = 44). **Ainda acrescentam:**
    - saídas dos últimos 3 meses subindo ≥ 10%: 13,1% [9,6–16,5] (n = 633), contra 8,2%;
    - pico de saídas ≥ 2× a mediana: 16,1% [9,5–22,6] (n = 185), contra 8,5%.

    As margens continuam positivas (+0,033 e +0,010). Servem para revisão manual ou redução de valor, não para negar.
13. **Gênero não muda o comportamento de compra.** Ticket médio de R$ 8.100 (F) contra R$ 8.027 (M), Mann-Whitney p = 0,53; prazo e valor/renda iguais. **O ticket muda por região** (Kruskal-Wallis p < 0,001: PR/SC R$ 9.720 e DF/GO R$ 9.137, contra BA/SE R$ 7.246), mas valor/renda não muda (p = 0,62). A diferença de ticket entre regiões é diferença de renda.
14. **Atraso e calote não andam juntos em todo grupo.** Aposentado e viúvo têm calote baixo, mas mais atraso: 21,2% e 27,7% dos contratos pagam com atraso, contra 19,9% na média. No piloto, score ≤ 600 com finanças boas tem 32% de atraso, contra 22% em score > 600. Isso baixa o ponto de equilíbrio desses grupos.

**Limites:** toda PD é condicional à aprovação. Score ≤ 600, restrição e renda < 2k só existem no piloto (out/25–mar/26), que como um todo roda a 21,8%. As células com n < 50 não foram estimadas.


## 1. Perfil descritivo: 10.000 históricos × 2.000 novos

Distribuição (% das linhas). `Δ p.p.` = novos − históricos. Teste qui-quadrado de homogeneidade por variável.

**genero** (qui² p = 0.619)

| genero        |   históricos |   novos |   Δ p.p. |
|:--------------|-------------:|--------:|---------:|
| feminino      |         49.7 |    49.8 |      0.1 |
| masculino     |         49.3 |    48.9 |     -0.4 |
| nao_informado |          1.0 |     1.2 |      0.2 |

**regiao** (qui² p = 0.706)

| regiao                  |   históricos |   novos |   Δ p.p. |
|:------------------------|-------------:|--------:|---------:|
| BA/SE                   |         15.2 |    14.8 |     -0.4 |
| CE/PI/MA/PA/AM/AP/RR/AC |         14.0 |    15.2 |      1.2 |
| RS                      |         11.5 |    11.5 |     -0.0 |
| RJ/ES                   |         11.4 |    11.9 |      0.5 |
| MG                      |         11.0 |    11.8 |      0.8 |
| SP capital/RM           |          9.1 |     8.4 |     -0.7 |
| PR/SC                   |          9.0 |     8.4 |     -0.6 |
| PE/AL/PB/RN             |          8.0 |     7.2 |     -0.8 |
| DF/GO/TO/MT/MS/RO       |          5.6 |     5.6 |      0.1 |
| SP interior             |          5.1 |     5.1 |     -0.0 |

**tipo_vinculo** (qui² p = 0.191)

| tipo_vinculo   |   históricos |   novos |   Δ p.p. |
|:---------------|-------------:|--------:|---------:|
| assalariado    |         55.0 |    53.4 |     -1.5 |
| autonomo       |         24.4 |    26.8 |      2.3 |
| empresario     |         10.4 |    10.0 |     -0.4 |
| aposentado     |         10.2 |     9.8 |     -0.4 |

**estado_civil** (qui² p = 0.973)

| estado_civil   |   históricos |   novos |   Δ p.p. |
|:---------------|-------------:|--------:|---------:|
| solteiro       |         39.2 |    39.0 |     -0.2 |
| casado         |         35.9 |    35.4 |     -0.5 |
| uniao_estavel  |         11.8 |    12.0 |      0.2 |
| divorciado     |         10.0 |    10.4 |      0.4 |
| viuvo          |          3.1 |     3.1 |     -0.0 |

**faixa_idade** (qui² p = 0.739)

| faixa_idade   |   históricos |   novos |   Δ p.p. |
|:--------------|-------------:|--------:|---------:|
| 55-64         |         23.6 |    24.8 |      1.3 |
| 25-34         |         20.2 |    20.2 |      0.1 |
| 35-44         |         20.0 |    20.3 |      0.3 |
| 45-54         |         19.9 |    19.2 |     -0.7 |
| <25           |         10.4 |     9.6 |     -0.9 |
| 65+           |          5.9 |     5.9 |     -0.0 |

**faixa_renda** (qui² p = 0.028)

| faixa_renda   |   históricos |   novos |   Δ p.p. |
|:--------------|-------------:|--------:|---------:|
| 5-10k         |         34.7 |    33.4 |     -1.3 |
| 3-5k          |         32.7 |    31.8 |     -0.9 |
| 2-3k          |         16.4 |    19.0 |      2.6 |
| 10k+          |          9.3 |     8.2 |     -1.1 |
| <2k           |          7.0 |     7.6 |      0.6 |

**renda_conta_decl** (qui² p = 0.456)

| renda_conta_decl   |   históricos |   novos |   Δ p.p. |
|:-------------------|-------------:|--------:|---------:|
| 80-95%             |         52.2 |    50.6 |     -1.7 |
| 60-80%             |         25.4 |    26.6 |      1.1 |
| 95-105%            |         13.7 |    14.0 |      0.2 |
| >105%              |          5.1 |     4.9 |     -0.3 |
| <60%               |          3.5 |     4.1 |      0.6 |

**tempo_conta** (qui² p = 0.232)

| tempo_conta   |   históricos |   novos |   Δ p.p. |
|:--------------|-------------:|--------:|---------:|
| 5a+           |         36.7 |    34.6 |     -2.1 |
| 1-3a          |         24.4 |    24.4 |      0.0 |
| 3-5a          |         24.3 |    25.0 |      0.7 |
| <1a           |         14.6 |    16.0 |      1.4 |

**faixa_valor** (qui² p = 0.030)

| faixa_valor   |   históricos |   novos |   Δ p.p. |
|:--------------|-------------:|--------:|---------:|
| 3-6k          |         34.4 |    34.2 |     -0.1 |
| 6-10k         |         24.9 |    24.6 |     -0.3 |
| <3k           |         14.9 |    17.5 |      2.6 |
| 10-15k        |         13.0 |    11.7 |     -1.3 |
| 15k+          |         12.9 |    12.0 |     -0.9 |

**prazo_meses** (qui² p = 0.892)

|   prazo_meses |   históricos |   novos |   Δ p.p. |
|--------------:|-------------:|--------:|---------:|
|            24 |         29.4 |    29.0 |     -0.4 |
|            36 |         25.6 |    26.2 |      0.6 |
|            12 |         20.1 |    20.7 |      0.6 |
|            18 |         19.8 |    19.0 |     -0.8 |
|             6 |          5.1 |     5.1 |      0.0 |

**faixa_score** (qui² p = 0.094)

| faixa_score   |   históricos |   novos |   Δ p.p. |
|:--------------|-------------:|--------:|---------:|
| 800+          |         30.6 |    29.6 |     -1.0 |
| 701-800       |         29.4 |    32.1 |      2.7 |
| 601-700       |         16.2 |    16.0 |     -0.2 |
| 500-600       |         16.1 |    15.7 |     -0.4 |
| <500          |          7.7 |     6.6 |     -1.2 |

**Variáveis numéricas**

|                  |   históricos (mediana) |   novos (mediana) |   históricos (média) |   novos (média) |
|:-----------------|-----------------------:|------------------:|---------------------:|----------------:|
| renda_declarada  |                4600.00 |           4350.00 |              5430.90 |         5230.55 |
| renda_mov        |                3795.29 |           3626.59 |              4542.73 |         4342.01 |
| renda_ratio      |                   0.86 |              0.85 |                 0.85 |            0.85 |
| idade            |                  44.72 |             44.93 |                44.74 |           45.10 |
| meses_conta      |                  47.08 |             46.02 |                47.21 |           46.12 |
| valor_solicitado |                6000.00 |           5700.00 |              8077.15 |         7673.40 |
| prazo_meses      |                  24.00 |             24.00 |                22.56 |           22.61 |
| comp_real_solic  |                   0.10 |              0.10 |                 0.15 |            0.15 |
| comp_total_solic |                   0.22 |              0.23 |                 0.28 |            0.28 |
| sai_ent          |                   0.32 |              0.32 |                 0.35 |            0.35 |
| score            |                 736.00 |            742.00 |               718.61 |          722.05 |

Profissões: 46 distintas; as 10 mais comuns nos históricos:

| profissao               |   históricos |   novos |
|:------------------------|-------------:|--------:|
| Aposentado              |          658 |     134 |
| Assistente financeiro   |          543 |      94 |
| Analista administrativo |          533 |     109 |
| Técnico em informática  |          528 |      84 |
| Vendedor                |          518 |     109 |
| Professor               |          499 |      89 |
| Técnico de enfermagem   |          485 |      90 |
| Servidor aposentado     |          358 |      62 |
| Recepcionista           |          321 |      57 |
| Atendente               |          315 |      53 |

## 2. Inadimplência por segmento (aprovados do histórico, PD de vida inteira por KM)

`taxa_aprov` = aprovados / pedidos no segmento (atual + piloto); `taxa_aprov_atual` = só pedidos avaliados pela política atual. `ingenua` = parou / contratos (subestima). `pd_vida` corrige a censura. `margem_R$` = ganho esperado por R$ aprovado. Média da carteira: ver linha 'todos'.

|       |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | IC95          |
|:------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------------|
| todos |        6033 |       626 | 10.4%     | 15.4%     | 19.9%      |       0.014 | 48.34 mi | 14.3% – 16.6% |

**3.1 Faixa de renda declarada**

| grupo   |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:--------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| <2k     |       696 | 9.5%         | 0.0%               |          66 |        10 | 15.2%     | 25.0%     | 25.6%      |      -0.063 | 0.23 mi  |         | 9.0% – 41.0%  |
| 2-3k    |      1637 | 63.8%        | 60.1%              |        1045 |       130 | 12.4%     | 18.9%     | 20.4%      |      -0.012 | 4.94 mi  |         | 15.8% – 22.0% |
| 3-5k    |      3267 | 65.7%        | 61.5%              |        2148 |       228 | 10.6%     | 15.6%     | 19.9%      |       0.013 | 13.18 mi |         | 13.6% – 17.5% |
| 5-10k   |      3472 | 63.4%        | 60.0%              |        2201 |       199 | 9.0%      | 13.6%     | 19.3%      |       0.029 | 20.11 mi |         | 11.7% – 15.4% |
| 10k+    |       928 | 61.7%        | 57.9%              |         573 |        59 | 10.3%     | 14.7%     | 20.5%      |       0.019 | 9.88 mi  |         | 11.1% – 18.4% |

**3.2 Profissão (profissões com < 100 clientes na base agrupadas por vínculo)**

| grupo                   |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:------------------------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| Advogado                |       174 | 63.8%        | 60.8%              |         111 |        10 | 9.0%      | 15.0%     | 21.7%      |       0.016 | 1.78 mi  |         | 5.9% – 24.2%  |
| Analista administrativo |       533 | 65.7%        | 63.0%              |         350 |        23 | 6.6%      | 10.1%     | 19.9%      |       0.054 | 2.68 mi  |         | 6.0% – 14.2%  |
| Analista de sistemas    |       104 | 63.5%        | 60.4%              |          66 |         6 | 9.1%      | 14.1%     | 19.6%      |       0.025 | 1.08 mi  |         | 3.1% – 25.1%  |
| Aposentado              |       658 | 55.8%        | 52.5%              |         367 |        31 | 8.4%      | 11.5%     | 24.4%      |       0.04  | 2.65 mi  |         | 7.6% – 15.4%  |
| Assistente financeiro   |       543 | 69.6%        | 65.7%              |         378 |        32 | 8.5%      | 12.0%     | 17.4%      |       0.043 | 2.80 mi  |         | 7.9% – 16.1%  |
| Atendente               |       315 | 49.5%        | 45.1%              |         156 |        19 | 12.2%     | 19.0%     | 13.3%      |      -0.006 | 0.73 mi  |         | 10.7% – 27.2% |
| Auxiliar administrativo |       261 | 52.5%        | 48.0%              |         137 |        16 | 11.7%     | 19.8%     | 21.0%      |      -0.02  | 0.70 mi  |         | 10.2% – 29.5% |
| Auxiliar de produção    |       266 | 47.0%        | 40.7%              |         125 |        26 | 20.8%     | 31.1%     | 21.0%      |      -0.104 | 0.58 mi  |         | 20.5% – 41.7% |
| Cabeleireiro            |       235 | 63.4%        | 60.4%              |         149 |        12 | 8.1%      | 11.4%     | 16.7%      |       0.048 | 1.06 mi  |         | 5.1% – 17.8%  |
| Comerciante             |       114 | 42.1%        | 38.8%              |          48 |         7 | 14.6%     | 18.6%     | 36.4%      |      -0.026 | 0.22 mi  |         | 5.9% – 31.3%  |
| Coordenador de projetos |       109 | 67.0%        | 65.0%              |          73 |         4 | 5.5%      | 7.0%      | 34.7%      |       0.063 | 1.12 mi  |         | 0.2% – 13.7%  |
| Corretor de imóveis     |       225 | 61.8%        | 56.6%              |         139 |        10 | 7.2%      | 9.2%      | 21.5%      |       0.059 | 0.98 mi  |         | 3.7% – 14.7%  |
| Costureira              |       132 | 42.4%        | 34.8%              |          56 |         8 | 14.3%     | 21.4%     | 15.5%      |      -0.026 | 0.27 mi  |         | 7.6% – 35.3%  |
| Designer                |       237 | 59.1%        | 54.3%              |         140 |        18 | 12.9%     | 20.6%     | 20.7%      |      -0.025 | 1.10 mi  |         | 11.4% – 29.8% |
| Diarista                |       142 | 45.8%        | 40.9%              |          65 |        11 | 16.9%     | 22.4%     | 17.7%      |      -0.036 | 0.29 mi  |         | 10.4% – 34.4% |
| Dono de lanchonete      |       103 | 48.5%        | 42.0%              |          50 |         5 | 10.0%     | 17.1%     | 13.7%      |       0.008 | 0.25 mi  |         | 2.1% – 32.2%  |
| Dono de loja            |       204 | 67.6%        | 62.4%              |         138 |        16 | 11.6%     | 16.4%     | 22.4%      |       0.005 | 1.01 mi  |         | 8.8% – 24.0%  |
| Dono de restaurante     |       191 | 64.4%        | 60.7%              |         123 |        16 | 13.0%     | 18.9%     | 23.2%      |      -0.015 | 0.96 mi  |         | 10.3% – 27.5% |
| Eletricista             |       189 | 60.8%        | 56.3%              |         115 |        14 | 12.2%     | 16.8%     | 11.9%      |       0.012 | 0.86 mi  |         | 8.4% – 25.3%  |
| Engenheiro              |        90 | 72.2%        | 67.1%              |          65 |         5 | 7.7%      | 15.1%     | 27.2%      |       0.01  | 1.04 mi  |         | 2.5% – 27.7%  |
| Fotógrafo               |       222 | 60.8%        | 56.6%              |         135 |        14 | 10.4%     | 15.3%     | 25.5%      |       0.01  | 1.05 mi  |         | 7.6% – 23.0%  |
| Gerente comercial       |       119 | 58.0%        | 50.5%              |          69 |         4 | 5.8%      | 6.2%      | 27.9%      |       0.075 | 1.13 mi  |         | 0.3% – 12.2%  |
| Manicure                |       144 | 38.2%        | 32.0%              |          55 |         7 | 12.7%     | 19.5%     | 17.5%      |      -0.013 | 0.26 mi  |         | 5.2% – 33.8%  |
| Microempreendedor       |        97 | 50.5%        | 43.4%              |          49 |         8 | 16.3%     | 23.5%     | 17.8%      |      -0.044 | 0.23 mi  |         | 8.2% – 38.8%  |
| Motorista               |       286 | 44.4%        | 38.2%              |         127 |        16 | 12.6%     | 18.4%     | 12.3%      |      -0     | 0.66 mi  |         | 9.7% – 27.1%  |
| Motorista de aplicativo |       129 | 45.7%        | 43.6%              |          59 |        12 | 20.3%     | 31.3%     | 10.9%      |      -0.096 | 0.38 mi  |         | 15.6% – 47.0% |
| Médico                  |       128 | 71.1%        | 66.1%              |          91 |         6 | 6.6%      | 9.0%      | 15.2%      |       0.067 | 1.45 mi  |         | 2.0% – 16.0%  |
| Operador de caixa       |       277 | 50.9%        | 45.7%              |         141 |        18 | 12.8%     | 20.1%     | 27.0%      |      -0.028 | 0.70 mi  |         | 11.4% – 28.8% |
| Pedreiro                |       122 | 41.8%        | 38.9%              |          51 |         7 | 13.7%     | 25.2%     | 27.2%      |      -0.066 | 0.29 mi  |         | 7.2% – 43.2%  |
| Personal trainer        |       237 | 64.1%        | 61.2%              |         152 |        24 | 15.8%     | 22.6%     | 14.8%      |      -0.034 | 1.16 mi  |         | 14.4% – 30.7% |
| Professor               |       499 | 66.1%        | 62.4%              |         330 |        27 | 8.2%      | 12.6%     | 21.6%      |       0.034 | 2.55 mi  |         | 7.9% – 17.3%  |
| Proprietário de oficina |       210 | 62.9%        | 59.9%              |         132 |        19 | 14.4%     | 19.6%     | 18.5%      |      -0.016 | 1.03 mi  |         | 11.3% – 28.0% |
| Recepcionista           |       321 | 51.1%        | 45.7%              |         164 |        26 | 15.9%     | 24.2%     | 19.5%      |      -0.051 | 0.75 mi  |         | 15.3% – 33.2% |
| Servidor aposentado     |       358 | 68.4%        | 65.5%              |         245 |        16 | 6.5%      | 9.7%      | 16.0%      |       0.062 | 2.14 mi  |         | 5.0% – 14.3%  |
| Técnico de enfermagem   |       485 | 69.9%        | 65.5%              |         339 |        41 | 12.1%     | 17.6%     | 17.8%      |       0     | 2.57 mi  |         | 12.5% – 22.8% |
| Técnico em informática  |       528 | 70.1%        | 66.4%              |         370 |        32 | 8.6%      | 14.1%     | 19.7%      |       0.025 | 2.76 mi  |         | 9.3% – 19.0%  |
| Vendedor                |       518 | 71.2%        | 67.6%              |         369 |        26 | 7.0%      | 11.3%     | 19.3%      |       0.046 | 2.74 mi  |         | 7.0% – 15.6%  |
| Vendedor ambulante      |       132 | 49.2%        | 42.9%              |          65 |         7 | 10.8%     | 15.9%     | 18.3%      |       0.013 | 0.27 mi  |         | 4.7% – 27.0%  |
| outras (autonomo)       |       239 | 65.7%        | 61.7%              |         157 |        13 | 8.3%      | 11.7%     | 22.6%      |       0.04  | 2.62 mi  |         | 5.6% – 17.9%  |
| outras (empresario)     |       124 | 66.1%        | 64.9%              |          82 |        14 | 17.1%     | 27.9%     | 11.9%      |      -0.071 | 1.42 mi  |         | 14.2% – 41.6% |

**3.3 Tipo de vínculo**

| grupo       |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:------------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| aposentado  |      1016 | 60.2%        | 57.0%              |         612 |        47 | 7.7%      | 10.7%     | 21.2%      |       0.048 | 4.80 mi  |         | 7.7% – 13.7%  |
| assalariado |      5496 | 62.3%        | 58.1%              |        3426 |       332 | 9.7%      | 14.7%     | 20.0%      |       0.02  | 27.25 mi |         | 13.2% – 16.3% |
| autonomo    |      2445 | 56.2%        | 51.8%              |        1373 |       162 | 11.8%     | 17.5%     | 18.7%      |      -0     | 11.17 mi |         | 14.9% – 20.1% |
| empresario  |      1043 | 59.6%        | 55.5%              |         622 |        85 | 13.7%     | 19.9%     | 20.1%      |      -0.019 | 5.13 mi  |         | 15.9% – 23.9% |

**3.4 Estado civil**

| grupo         |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:--------------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| casado        |      3588 | 60.2%        | 56.0%              |        2161 |       228 | 10.6%     | 15.8%     | 20.0%      |       0.011 | 17.45 mi |         | 13.8% – 17.8% |
| divorciado    |      1002 | 59.0%        | 54.3%              |         591 |        63 | 10.7%     | 16.1%     | 22.1%      |       0.007 | 4.71 mi  |         | 12.2% – 19.9% |
| solteiro      |      3916 | 61.2%        | 57.1%              |        2395 |       261 | 10.9%     | 16.2%     | 18.0%      |       0.011 | 18.97 mi |         | 14.3% – 18.0% |
| uniao_estavel |      1181 | 60.0%        | 56.1%              |         709 |        65 | 9.2%      | 13.4%     | 22.1%      |       0.027 | 5.76 mi  |         | 10.2% – 16.6% |
| viuvo         |       313 | 56.5%        | 52.5%              |         177 |         9 | 5.1%      | 7.3%      | 27.7%      |       0.067 | 1.45 mi  |         | 2.4% – 12.3%  |

**3.5a Região postal (1º dígito do CEP)**

| grupo                   |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:------------------------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| BA/SE                   |      1523 | 58.2%        | 54.4%              |         886 |        82 | 9.3%      | 13.5%     | 18.2%      |       0.03  | 6.25 mi  |         | 10.6% – 16.4% |
| CE/PI/MA/PA/AM/AP/RR/AC |      1404 | 57.8%        | 53.4%              |         811 |        85 | 10.5%     | 16.1%     | 19.4%      |       0.01  | 6.39 mi  |         | 12.8% – 19.4% |
| DF/GO/TO/MT/MS/RO       |       560 | 65.2%        | 61.6%              |         365 |        40 | 11.0%     | 16.2%     | 17.5%      |       0.011 | 3.32 mi  |         | 11.4% – 20.9% |
| MG                      |      1103 | 64.7%        | 61.4%              |         714 |        77 | 10.8%     | 16.0%     | 20.7%      |       0.009 | 5.65 mi  |         | 12.6% – 19.4% |
| PE/AL/PB/RN             |       796 | 59.0%        | 54.8%              |         470 |        42 | 8.9%      | 13.1%     | 23.5%      |       0.028 | 3.62 mi  |         | 9.2% – 16.9%  |
| PR/SC                   |       900 | 59.2%        | 54.7%              |         533 |        52 | 9.8%      | 14.1%     | 19.9%      |       0.024 | 5.36 mi  |         | 10.4% – 17.9% |
| RJ/ES                   |      1140 | 61.6%        | 57.0%              |         702 |        80 | 11.4%     | 17.3%     | 19.9%      |       0     | 5.24 mi  |         | 13.6% – 21.0% |
| RS                      |      1147 | 63.4%        | 59.0%              |         727 |        70 | 9.6%      | 14.4%     | 20.6%      |       0.021 | 5.87 mi  |         | 11.1% – 17.7% |
| SP capital/RM           |       914 | 60.0%        | 55.8%              |         548 |        55 | 10.0%     | 15.0%     | 20.6%      |       0.017 | 4.32 mi  |         | 11.2% – 18.9% |
| SP interior             |       513 | 54.0%        | 48.8%              |         277 |        43 | 15.5%     | 22.4%     | 17.9%      |      -0.035 | 2.32 mi  |         | 16.1% – 28.6% |

**3.5b UF (pelo CEP; n<30 não estimado)**

| grupo   |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:--------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| AM      |        61 | 63.9%        | 59.3%              |          39 |         5 | 12.8%     | 24.8%     | 26.0%      |      -0.062 | 0.48 mi  |         | 5.8% – 43.9%  |
| BA      |      1410 | 59.0%        | 55.3%              |         832 |        77 | 9.3%      | 13.4%     | 18.2%      |       0.031 | 5.89 mi  |         | 10.5% – 16.4% |
| CE      |       674 | 56.2%        | 52.0%              |         379 |        33 | 8.7%      | 13.5%     | 20.4%      |       0.029 | 2.83 mi  |         | 9.0% – 18.0%  |
| DF      |        62 | 67.7%        | 66.1%              |          42 |         3 | 7.1%      | 10.4%     | 19.1%      |       0.053 | 0.51 mi  |         | 0.0% – 22.4%  |
| GO      |       242 | 62.8%        | 58.2%              |         152 |        16 | 10.5%     | 14.5%     | 17.3%      |       0.024 | 1.30 mi  |         | 7.7% – 21.2%  |
| MA      |       620 | 58.4%        | 53.7%              |         362 |        44 | 12.2%     | 17.6%     | 18.1%      |       0     | 2.73 mi  |         | 12.6% – 22.5% |
| MG      |      1103 | 64.7%        | 61.4%              |         714 |        77 | 10.8%     | 16.0%     | 20.7%      |       0.009 | 5.65 mi  |         | 12.6% – 19.4% |
| MT      |        78 | 65.4%        | 62.0%              |          51 |         4 | 7.8%      | 13.8%     | 25.4%      |       0.021 | 0.63 mi  |         | 0.4% – 27.2%  |
| PE      |       796 | 59.0%        | 54.8%              |         470 |        42 | 8.9%      | 13.1%     | 23.5%      |       0.028 | 3.62 mi  |         | 9.2% – 16.9%  |
| PR      |       845 | 59.2%        | 54.6%              |         500 |        46 | 9.2%      | 13.4%     | 20.3%      |       0.029 | 4.88 mi  |         | 9.6% – 17.2%  |
| RJ      |      1140 | 61.6%        | 57.0%              |         702 |        80 | 11.4%     | 17.3%     | 19.9%      |       0     | 5.24 mi  |         | 13.6% – 21.0% |
| RR      |        49 | 63.3%        | 61.4%              |          31 |         3 | 9.7%      | 15.6%     | 8.8%       |       0.024 | 0.35 mi  |         | 0.0% – 31.9%  |
| RS      |      1147 | 63.4%        | 59.0%              |         727 |        70 | 9.6%      | 14.4%     | 20.6%      |       0.021 | 5.87 mi  |         | 11.1% – 17.7% |
| SC      |        55 | 60.0%        | 56.5%              |          33 |         6 | 18.2%     | 25.5%     | 14.4%      |      -0.056 | 0.48 mi  |         | 6.9% – 44.2%  |
| SE      |       113 | 47.8%        | 42.7%              |          54 |         5 | 9.3%      | 14.8%     | 18.8%      |       0.02  | 0.36 mi  |         | 1.9% – 27.7%  |
| SP      |      1427 | 57.8%        | 53.3%              |         825 |        98 | 11.9%     | 17.4%     | 19.7%      |      -0.001 | 6.64 mi  |         | 14.2% – 20.7% |
| TO      |       178 | 67.4%        | 64.2%              |         120 |        17 | 14.2%     | 21.5%     | 12.6%      |      -0.024 | 0.88 mi  |         | 12.1% – 31.0% |

**Gênero**

| grupo         |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:--------------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| feminino      |      4969 | 60.3%        | 56.0%              |        2995 |       313 | 10.5%     | 15.6%     | 20.2%      |       0.013 | 24.06 mi |         | 13.9% – 17.3% |
| masculino     |      4930 | 60.2%        | 56.2%              |        2969 |       302 | 10.2%     | 15.1%     | 19.6%      |       0.017 | 23.68 mi |         | 13.4% – 16.7% |
| nao_informado |       101 | 68.3%        | 64.3%              |          69 |        11 | 15.9%     | 22.3%     | 17.2%      |      -0.034 | 0.60 mi  |         | 10.1% – 34.5% |

**Faixa etária**

| grupo   |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:--------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| <25     |      1042 | 58.3%        | 53.5%              |         607 |        59 | 9.7%      | 14.9%     | 19.7%      |       0.019 | 4.79 mi  |         | 11.1% – 18.6% |
| 25-34   |      2015 | 59.8%        | 56.0%              |        1205 |       136 | 11.3%     | 17.1%     | 19.3%      |       0.002 | 9.89 mi  |         | 14.4% – 19.9% |
| 35-44   |      2003 | 60.5%        | 56.0%              |        1212 |       132 | 10.9%     | 16.0%     | 19.7%      |       0.01  | 9.74 mi  |         | 13.3% – 18.7% |
| 45-54   |      1990 | 60.1%        | 56.2%              |        1195 |       122 | 10.2%     | 15.1%     | 21.2%      |       0.016 | 9.53 mi  |         | 12.5% – 17.7% |
| 55-64   |      2360 | 61.7%        | 57.4%              |        1455 |       148 | 10.2%     | 15.3%     | 18.7%      |       0.016 | 11.58 mi |         | 12.9% – 17.7% |
| 65+     |       590 | 60.8%        | 57.3%              |         359 |        29 | 8.1%      | 10.9%     | 22.2%      |       0.046 | 2.80 mi  |         | 7.1% – 14.8%  |

**Tempo de conta (relacionamento)**

| grupo   |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:--------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| <1a     |      1460 | 52.5%        | 48.1%              |         766 |        75 | 9.8%      | 14.1%     | 18.8%      |       0.025 | 6.03 mi  |         | 11.0% – 17.2% |
| 1-3a    |      2438 | 61.9%        | 57.5%              |        1509 |       183 | 12.1%     | 17.8%     | 18.9%      |      -0.002 | 11.97 mi |         | 15.3% – 20.3% |
| 3-5a    |      2432 | 63.7%        | 59.7%              |        1548 |       141 | 9.1%      | 13.6%     | 19.3%      |       0.028 | 12.87 mi |         | 11.4% – 15.9% |
| 5a+     |      3670 | 60.2%        | 56.1%              |        2210 |       227 | 10.3%     | 15.5%     | 21.3%      |       0.012 | 17.47 mi |         | 13.6% – 17.5% |

**Renda pela conta / renda declarada**

| grupo   |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:--------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| <60%    |       351 | 19.1%        | 11.8%              |          67 |        29 | 43.3%     | 65.1%     | 15.4%      |      -0.354 | 0.42 mi  |         | 49.5% – 80.8% |
| 60-80%  |      2542 | 63.9%        | 60.3%              |        1625 |       169 | 10.4%     | 15.7%     | 19.8%      |       0.012 | 13.19 mi |         | 13.4% – 18.1% |
| 80-95%  |      5223 | 61.9%        | 57.7%              |        3231 |       312 | 9.7%      | 14.3%     | 20.6%      |       0.022 | 26.06 mi |         | 12.7% – 15.8% |
| 95-105% |      1372 | 59.1%        | 54.7%              |         811 |        81 | 10.0%     | 15.2%     | 17.8%      |       0.018 | 6.31 mi  |         | 12.0% – 18.4% |
| >105%   |       512 | 58.4%        | 54.6%              |         299 |        35 | 11.7%     | 16.9%     | 18.8%      |       0.004 | 2.37 mi  |         | 11.6% – 22.3% |

**Score do birô**

| grupo   |   pedidos | taxa_aprov   | taxa_aprov_atual   |   contratos |   pararam | ingenua   | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95          |
|:--------|----------:|:-------------|:-------------------|------------:|----------:|:----------|:----------|:-----------|------------:|:---------|:--------|:--------------|
| <500    |       773 | 12.4%        | 0.0%               |          96 |        11 | 11.5%     | 17.6%     | 33.8%      |      -0.016 | 0.72 mi  |         | 6.2% – 29.0%  |
| 500-600 |      1612 | 11.3%        | 0.0%               |         182 |        30 | 16.5%     | 28.8%     | 23.1%      |      -0.089 | 1.31 mi  |         | 18.1% – 39.6% |
| 601-700 |      1622 | 72.6%        | 70.7%              |        1178 |       121 | 10.3%     | 14.7%     | 20.9%      |       0.019 | 9.43 mi  |         | 12.2% – 17.2% |
| 701-800 |      2938 | 77.1%        | 75.3%              |        2266 |       224 | 9.9%      | 15.3%     | 18.9%      |       0.016 | 18.08 mi |         | 13.4% – 17.3% |
| 800+    |      3055 | 75.6%        | 73.8%              |        2311 |       240 | 10.4%     | 15.1%     | 19.7%      |       0.017 | 18.81 mi |         | 13.2% – 16.9% |

## 3. Renda × profissão × capacidade de pagamento; perfil × ticket; perfil × comprometimento

**3.6 Vínculo × faixa de renda: capacidade de pagamento (todos os 10.000 pedidos) e PD (aprovados, n≥50)**

|                     |   pedidos |   renda_conta/decl (med) |   sobra mensal R$ (med) |   saídas/entradas (med) |   parcela pedida/renda est. (med) |   (parcela+outras)/renda est. (med) | taxa_aprov   |   aprovados | pd_vida   | IC95          |   margem_R$ |
|:--------------------|----------:|-------------------------:|------------------------:|------------------------:|----------------------------------:|------------------------------------:|:-------------|------------:|:----------|:--------------|------------:|
| aposentado · <2k    |        75 |                     0.85 |                 1024.95 |                    0.32 |                              0.11 |                                0.23 | 10.7%        |      nan    | nan       | nan           |      nan    |
| aposentado · 2-3k   |       168 |                     0.85 |                 1563.06 |                    0.32 |                              0.11 |                                0.29 | 61.9%        |      104.00 | 11.7%     | 4.4% – 19.0%  |        0.03 |
| aposentado · 3-5k   |       324 |                     0.83 |                 2373.98 |                    0.32 |                              0.11 |                                0.22 | 68.5%        |      222.00 | 10.2%     | 5.5% – 14.8%  |        0.05 |
| aposentado · 5-10k  |       364 |                     0.82 |                 3937.90 |                    0.32 |                              0.10 |                                0.23 | 61.0%        |      222.00 | 9.5%      | 4.5% – 14.5%  |        0.06 |
| aposentado · 10k+   |        85 |                     0.80 |                 6963.18 |                    0.32 |                              0.10 |                                0.25 | 65.9%        |       56.00 | 15.3%     | 3.6% – 27.0%  |        0.02 |
| assalariado · <2k   |       365 |                     0.87 |                 1042.63 |                    0.32 |                              0.11 |                                0.27 | 11.2%        |      nan    | nan       | nan           |      nan    |
| assalariado · 2-3k  |       902 |                     0.85 |                 1519.81 |                    0.32 |                              0.11 |                                0.25 | 65.4%        |      590.00 | 19.5%     | 15.3% – 23.8% |       -0.01 |
| assalariado · 3-5k  |      1807 |                     0.84 |                 2378.05 |                    0.32 |                              0.10 |                                0.23 | 67.3%        |     1216.00 | 15.6%     | 12.9% – 18.3% |        0.01 |
| assalariado · 5-10k |      1918 |                     0.83 |                 3936.17 |                    0.32 |                              0.10 |                                0.22 | 66.3%        |     1272.00 | 12.0%     | 9.7% – 14.3%  |        0.04 |
| assalariado · 10k+  |       504 |                     0.81 |                 7319.04 |                    0.32 |                              0.10 |                                0.23 | 60.9%        |      307.00 | 10.9%     | 6.7% – 15.0%  |        0.04 |
| autonomo · <2k      |       190 |                     0.95 |                 1023.33 |                    0.32 |                              0.11 |                                0.22 | 6.8%         |      nan    | nan       | nan           |      nan    |
| autonomo · 2-3k     |       405 |                     0.92 |                 1528.45 |                    0.32 |                              0.10 |                                0.26 | 60.2%        |      244.00 | 23.0%     | 15.9% – 30.2% |       -0.04 |
| autonomo · 3-5k     |       781 |                     0.91 |                 2379.45 |                    0.32 |                              0.10 |                                0.21 | 62.5%        |      488.00 | 15.8%     | 11.8% – 19.7% |        0.01 |
| autonomo · 5-10k    |       827 |                     0.90 |                 3918.83 |                    0.32 |                              0.10 |                                0.20 | 57.8%        |      478.00 | 17.0%     | 12.6% – 21.4% |        0.00 |
| autonomo · 10k+     |       242 |                     0.87 |                 7368.22 |                    0.33 |                              0.10 |                                0.21 | 62.0%        |      150.00 | 17.0%     | 9.2% – 24.7%  |        0.00 |
| empresario · <2k    |        66 |                     0.93 |                 1080.75 |                    0.32 |                              0.10 |                                0.19 | 6.1%         |      nan    | nan       | nan           |      nan    |
| empresario · 2-3k   |       162 |                     0.90 |                 1526.00 |                    0.32 |                              0.11 |                                0.26 | 66.0%        |      107.00 | 14.3%     | 6.2% – 22.5%  |        0.02 |
| empresario · 3-5k   |       355 |                     0.89 |                 2353.20 |                    0.32 |                              0.10 |                                0.22 | 62.5%        |      222.00 | 21.5%     | 14.4% – 28.5% |       -0.04 |
| empresario · 5-10k  |       363 |                     0.89 |                 3929.67 |                    0.32 |                              0.10 |                                0.20 | 63.1%        |      229.00 | 19.2%     | 12.8% – 25.5% |       -0.01 |
| empresario · 10k+   |        97 |                     0.88 |                 7590.65 |                    0.33 |                              0.10 |                                0.14 | 61.9%        |       60.00 | 28.6%     | 13.0% – 44.2% |       -0.08 |

**3.7 Gênero × comportamento de compra (10.000 pedidos históricos)**

| genero        |   pedidos |   valor pedido médio |   valor pedido mediano |   prazo médio |   renda declarada med |   valor pedido / renda (med) |   parcela/renda est. (med) | taxa_aprov   |   valor aprovado médio |
|:--------------|----------:|---------------------:|-----------------------:|--------------:|----------------------:|-----------------------------:|---------------------------:|:-------------|-----------------------:|
| feminino      |      4969 |              8100.16 |                6000.00 |         22.45 |               4600.00 |                         1.21 |                       0.10 | 60.3%        |                8034.84 |
| masculino     |      4930 |              8026.84 |                6000.00 |         22.69 |               4550.00 |                         1.22 |                       0.10 | 60.2%        |                7975.41 |
| nao_informado |       101 |              9400.99 |                6000.00 |         21.56 |               4050.00 |                         1.49 |                       0.12 | 68.3%        |                8710.04 |

Mann-Whitney valor pedido feminino × masculino: p = 0.532.

**3.8 Localização × volume (históricos)**

| regiao                  |   pedidos |   % pedidos |   volume pedido (R$ mi) |   ticket pedido médio |   aprovados |   volume aprovado (R$ mi) |   ticket aprovado médio |   renda declarada med |
|:------------------------|----------:|------------:|------------------------:|----------------------:|------------:|--------------------------:|------------------------:|----------------------:|
| BA/SE                   |   1523.00 |       15.23 |                   11.04 |               7245.76 |      886.00 |                      6.25 |                 7059.30 |               4200.00 |
| CE/PI/MA/PA/AM/AP/RR/AC |   1404.00 |       14.04 |                   11.18 |               7962.61 |      811.00 |                      6.39 |                 7884.37 |               4250.00 |
| RS                      |   1147.00 |       11.47 |                    9.40 |               8192.59 |      727.00 |                      5.87 |                 8070.90 |               4850.00 |
| RJ/ES                   |   1140.00 |       11.40 |                    8.70 |               7634.65 |      702.00 |                      5.24 |                 7457.89 |               4250.00 |
| MG                      |   1103.00 |       11.03 |                    8.89 |               8055.58 |      714.00 |                      5.65 |                 7910.21 |               4950.00 |
| SP capital/RM           |    914.00 |        9.14 |                    7.29 |               7976.04 |      548.00 |                      4.32 |                 7875.43 |               4650.00 |
| PR/SC                   |    900.00 |        9.00 |                    8.75 |               9720.22 |      533.00 |                      5.36 |                10058.69 |               5475.00 |
| PE/AL/PB/RN             |    796.00 |        7.96 |                    6.09 |               7647.24 |      470.00 |                      3.62 |                 7700.34 |               4300.00 |
| DF/GO/TO/MT/MS/RO       |    560.00 |        5.60 |                    5.12 |               9136.96 |      365.00 |                      3.32 |                 9108.10 |               5650.00 |
| SP interior             |    513.00 |        5.13 |                    4.33 |               8438.21 |      277.00 |                      2.32 |                 8390.05 |               3350.00 |

Kruskal-Wallis ticket pedido entre regiões: p = 0.000; valor pedido/renda entre regiões: p = 0.617.

**3.9 / 3.10 Perfil × ticket médio × comprometimento (históricos)**

_tipo_vinculo_

| tipo_vinculo   |   pedidos |   ticket pedido médio |   prazo médio |   valor/renda (med) |   parcela pedida/renda est. (med) |   % parcela pedida > 28% renda est. |   outras parcelas/renda est. (med) |   (parcela+outras)/renda est. (med) |   % (parcela+outras) > 50% |   saídas/entradas (med) |
|:---------------|----------:|----------------------:|--------------:|--------------------:|----------------------------------:|------------------------------------:|-----------------------------------:|------------------------------------:|---------------------------:|------------------------:|
| aposentado     |   1016.00 |               7907.09 |         22.42 |                1.18 |                              0.10 |                                9.45 |                               0.10 |                                0.23 |                      14.07 |                    0.32 |
| assalariado    |   5496.00 |               8078.29 |         22.72 |                1.22 |                              0.10 |                                9.37 |                               0.09 |                                0.23 |                      13.39 |                    0.32 |
| autonomo       |   2445.00 |               8007.40 |         22.40 |                1.21 |                              0.10 |                                9.00 |                               0.07 |                                0.21 |                      11.74 |                    0.32 |
| empresario     |   1043.00 |               8400.29 |         22.26 |                1.26 |                              0.10 |                                9.49 |                               0.05 |                                0.20 |                      11.70 |                    0.32 |

_faixa_renda_

| faixa_renda   |   pedidos |   ticket pedido médio |   prazo médio |   valor/renda (med) |   parcela pedida/renda est. (med) |   % parcela pedida > 28% renda est. |   outras parcelas/renda est. (med) |   (parcela+outras)/renda est. (med) |   % (parcela+outras) > 50% |   saídas/entradas (med) |
|:--------------|----------:|----------------------:|--------------:|--------------------:|----------------------------------:|------------------------------------:|-----------------------------------:|------------------------------------:|---------------------------:|------------------------:|
| <2k           |    696.00 |               4165.37 |         23.24 |                1.38 |                              0.11 |                               18.39 |                               0.07 |                                0.24 |                      18.53 |                    0.32 |
| 2-3k          |   1637.00 |               5802.75 |         22.51 |                1.30 |                              0.11 |                               17.65 |                               0.08 |                                0.26 |                      19.98 |                    0.32 |
| 3-5k          |   3267.00 |               6632.72 |         22.59 |                1.23 |                              0.10 |                                9.43 |                               0.08 |                                0.22 |                      12.83 |                    0.32 |
| 5-10k         |   3472.00 |               9053.72 |         22.54 |                1.15 |                              0.10 |                                4.32 |                               0.09 |                                0.21 |                       8.90 |                    0.32 |
| 10k+          |    928.00 |              16454.42 |         22.11 |                1.16 |                              0.10 |                                5.93 |                               0.07 |                                0.21 |                      11.21 |                    0.32 |

_estado_civil_

| estado_civil   |   pedidos |   ticket pedido médio |   prazo médio |   valor/renda (med) |   parcela pedida/renda est. (med) |   % parcela pedida > 28% renda est. |   outras parcelas/renda est. (med) |   (parcela+outras)/renda est. (med) |   % (parcela+outras) > 50% |   saídas/entradas (med) |
|:---------------|----------:|----------------------:|--------------:|--------------------:|----------------------------------:|------------------------------------:|-----------------------------------:|------------------------------------:|---------------------------:|------------------------:|
| casado         |   3588.00 |               8137.35 |         22.44 |                1.23 |                              0.10 |                                9.42 |                               0.08 |                                0.22 |                      12.74 |                    0.32 |
| divorciado     |   1002.00 |               7779.14 |         22.53 |                1.22 |                              0.10 |                                8.18 |                               0.10 |                                0.23 |                      13.57 |                    0.32 |
| solteiro       |   3916.00 |               8022.27 |         22.52 |                1.21 |                              0.10 |                                9.65 |                               0.08 |                                0.22 |                      12.87 |                    0.32 |
| uniao_estavel  |   1181.00 |               8237.76 |         23.14 |                1.21 |                              0.10 |                                8.47 |                               0.08 |                                0.22 |                      11.94 |                    0.32 |
| viuvo          |    313.00 |               8421.73 |         22.37 |                1.17 |                              0.10 |                               10.22 |                               0.08 |                                0.25 |                      15.97 |                    0.32 |

_faixa_idade_

| faixa_idade   |   pedidos |   ticket pedido médio |   prazo médio |   valor/renda (med) |   parcela pedida/renda est. (med) |   % parcela pedida > 28% renda est. |   outras parcelas/renda est. (med) |   (parcela+outras)/renda est. (med) |   % (parcela+outras) > 50% |   saídas/entradas (med) |
|:--------------|----------:|----------------------:|--------------:|--------------------:|----------------------------------:|------------------------------------:|-----------------------------------:|------------------------------------:|---------------------------:|------------------------:|
| <25           |   1042.00 |               7948.37 |         23.38 |                1.22 |                              0.10 |                                9.02 |                               0.08 |                                0.23 |                      12.76 |                    0.32 |
| 25-34         |   2015.00 |               8129.53 |         22.81 |                1.21 |                              0.10 |                                9.48 |                               0.07 |                                0.22 |                      12.11 |                    0.32 |
| 35-44         |   2003.00 |               8194.41 |         22.23 |                1.23 |                              0.10 |                                9.99 |                               0.07 |                                0.22 |                      12.98 |                    0.32 |
| 45-54         |   1990.00 |               8030.65 |         22.63 |                1.21 |                              0.10 |                                9.15 |                               0.08 |                                0.22 |                      12.41 |                    0.33 |
| 55-64         |   2360.00 |               8096.78 |         22.21 |                1.21 |                              0.10 |                                8.94 |                               0.09 |                                0.23 |                      13.43 |                    0.32 |
| 65+           |    590.00 |               7805.93 |         22.57 |                1.17 |                              0.10 |                                8.81 |                               0.10 |                                0.23 |                      14.75 |                    0.32 |

_genero_

| genero        |   pedidos |   ticket pedido médio |   prazo médio |   valor/renda (med) |   parcela pedida/renda est. (med) |   % parcela pedida > 28% renda est. |   outras parcelas/renda est. (med) |   (parcela+outras)/renda est. (med) |   % (parcela+outras) > 50% |   saídas/entradas (med) |
|:--------------|----------:|----------------------:|--------------:|--------------------:|----------------------------------:|------------------------------------:|-----------------------------------:|------------------------------------:|---------------------------:|------------------------:|
| feminino      |   4969.00 |               8100.16 |         22.45 |                1.21 |                              0.10 |                                9.30 |                               0.08 |                                0.22 |                      12.94 |                    0.32 |
| masculino     |   4930.00 |               8026.84 |         22.69 |                1.22 |                              0.10 |                                9.25 |                               0.08 |                                0.22 |                      12.64 |                    0.32 |
| nao_informado |    101.00 |               9400.99 |         21.56 |                1.49 |                              0.12 |                               11.88 |                               0.13 |                                0.30 |                      21.78 |                    0.33 |

## 4. Interações entre variáveis

**Faixa de renda × vínculo × região**: com 5 × 4 × 10 = 200 células e 6.033 aprovados, quase nenhuma célula tem n ≥ 50. Abaixo as interações 2 a 2 com n ≥ 50 (PD vida; vazio = n < 50).

_faixa_renda × tipo_vinculo_

|       | aposentado    | assalariado    | autonomo      | empresario    |
|:------|:--------------|:---------------|:--------------|:--------------|
| 2-3k  | 11.7% (n=104) | 19.5% (n=590)  | 23.0% (n=244) | 14.3% (n=107) |
| 3-5k  | 10.2% (n=222) | 15.6% (n=1216) | 15.8% (n=488) | 21.5% (n=222) |
| 5-10k | 9.5% (n=222)  | 12.0% (n=1272) | 17.0% (n=478) | 19.2% (n=229) |
| 10k+  | 15.3% (n=56)  | 10.9% (n=307)  | 17.0% (n=150) | 28.6% (n=60)  |

_regiao × tipo_vinculo_

|                         | aposentado   | assalariado   | autonomo      | empresario   |
|:------------------------|:-------------|:--------------|:--------------|:-------------|
| BA/SE                   | 13.3% (n=83) | 11.8% (n=500) | 17.2% (n=219) | 15.3% (n=84) |
| CE/PI/MA/PA/AM/AP/RR/AC | 6.1% (n=89)  | 19.2% (n=442) | 14.7% (n=181) | 14.7% (n=99) |
| DF/GO/TO/MT/MS/RO       |              | 15.6% (n=213) | 18.8% (n=78)  |              |
| MG                      | 10.0% (n=75) | 11.1% (n=409) | 26.8% (n=155) | 28.8% (n=75) |
| PE/AL/PB/RN             |              | 9.7% (n=260)  | 21.1% (n=113) | 20.9% (n=50) |
| PR/SC                   |              | 12.3% (n=293) | 16.3% (n=132) | 21.8% (n=63) |
| RJ/ES                   | 18.5% (n=72) | 17.8% (n=406) | 15.0% (n=147) | 19.1% (n=77) |
| RS                      | 7.9% (n=79)  | 15.4% (n=424) | 13.6% (n=162) | 18.2% (n=62) |
| SP capital/RM           | 13.7% (n=53) | 15.4% (n=324) | 13.8% (n=118) | 17.7% (n=53) |
| SP interior             |              | 21.7% (n=155) | 22.4% (n=68)  |              |

_faixa_renda × regiao_

|       | BA/SE         | CE/PI/MA/PA/AM/AP/RR/AC   | PE/AL/PB/RN   | PR/SC         | RJ/ES         | RS            | SP capital/RM   | SP interior   | DF/GO/TO/MT/MS/RO   | MG            |
|:------|:--------------|:--------------------------|:--------------|:--------------|:--------------|:--------------|:----------------|:--------------|:--------------------|:--------------|
| 2-3k  | 15.3% (n=206) | 9.6% (n=174)              | 17.8% (n=112) | 30.4% (n=77)  | 20.3% (n=146) | 20.1% (n=98)  | 23.0% (n=82)    | 25.5% (n=86)  |                     |               |
| 3-5k  | 12.3% (n=314) | 21.6% (n=283)             | 11.7% (n=158) | 13.1% (n=135) | 18.0% (n=263) | 12.1% (n=277) | 13.1% (n=202)   | 18.6% (n=80)  | 16.1% (n=119)       | 17.3% (n=317) |
| 5-10k | 13.3% (n=330) | 13.5% (n=263)             | 13.2% (n=156) | 7.0% (n=173)  | 14.4% (n=250) | 14.7% (n=285) | 14.8% (n=206)   | 17.1% (n=53)  | 16.9% (n=169)       | 12.8% (n=316) |
| 10k+  |               | 17.0% (n=78)              |               | 14.1% (n=140) |               | 12.4% (n=60)  | 13.0% (n=56)    | 31.3% (n=53)  | 12.3% (n=57)        |               |

_faixa_comp × tipo_vinculo_

|        | aposentado   | assalariado    | autonomo      | empresario    |
|:-------|:-------------|:---------------|:--------------|:--------------|
| <10%   | 5.2% (n=291) | 9.2% (n=1667)  | 11.7% (n=717) | 17.3% (n=320) |
| 10-20% | 7.3% (n=230) | 11.9% (n=1210) | 11.6% (n=451) | 15.8% (n=205) |
| 20-28% |              | 13.0% (n=260)  | 18.8% (n=90)  |               |
| 28-40% |              | 40.4% (n=242)  | 55.4% (n=100) |               |

_faixa_comp × faixa_renda_

|        | 2-3k          | 3-5k          | 5-10k          | 10k+          |
|:-------|:--------------|:--------------|:---------------|:--------------|
| <10%   | 8.4% (n=455)  | 9.1% (n=1051) | 11.2% (n=1173) | 12.6% (n=286) |
| 10-20% | 10.1% (n=330) | 11.5% (n=739) | 11.9% (n=802)  | 14.9% (n=207) |
| 20-28% | 13.9% (n=73)  | 12.4% (n=166) | 18.5% (n=144)  | 10.4% (n=50)  |
| 28-40% | 48.5% (n=162) | 51.0% (n=156) | 30.1% (n=73)   |               |

_genero × faixa_comp_

|           | <10%           | 10-20%         | 20-28%        | 28-40%        |
|:----------|:---------------|:---------------|:--------------|:--------------|
| feminino  | 11.4% (n=1497) | 11.9% (n=1030) | 11.4% (n=219) | 43.3% (n=209) |
| masculino | 9.1% (n=1474)  | 11.4% (n=1035) | 16.1% (n=210) | 45.7% (n=215) |

_estado_civil × faixa_comp_

|               | <10%           | 10-20%        | 20-28%        | 28-40%        |
|:--------------|:---------------|:--------------|:--------------|:--------------|
| casado        | 11.2% (n=1046) | 11.9% (n=781) | 17.2% (n=167) | 45.1% (n=146) |
| divorciado    | 11.3% (n=286)  | 11.8% (n=212) |               |               |
| solteiro      | 9.6% (n=1212)  | 12.5% (n=802) | 15.8% (n=162) | 47.5% (n=183) |
| uniao_estavel | 10.6% (n=368)  | 9.9% (n=231)  | 7.7% (n=51)   | 32.8% (n=51)  |
| viuvo         | 3.0% (n=83)    | 5.9% (n=70)   |               |               |

**Árvore rasa só com perfil (renda declarada, vínculo, região, gênero, estado civil, idade, tempo de conta)** — alvo: parou, peso = fração observada da janela (censura), profundidade 3, folha ≥ 150. PD de cada folha recalculada por KM.

| grupo                                                               |   contratos |   pararam | pd_vida   |   margem_R$ | aviso   | IC95          |
|:--------------------------------------------------------------------|------------:|----------:|:----------|------------:|:--------|:--------------|
| meses_conta > 3 e renda_declarada > 2,525 e meses_conta > 14        |        4642 |       470 | 15.1%     |       0.017 |         | 13.8% – 16.4% |
| meses_conta > 3 e renda_declarada > 2,525 e meses_conta ≤ 14        |         635 |        37 | 8.8%      |       0.064 |         | 6.0% – 11.6%  |
| meses_conta > 3 e renda_declarada ≤ 2,525 e estado_civil_casado     |         219 |        22 | 15.1%     |       0.016 |         | 9.0% – 21.2%  |
| meses_conta > 3 e renda_declarada ≤ 2,525 e não estado_civil_casado |         369 |        62 | 25.2%     |      -0.055 |         | 19.3% – 31.0% |
| meses_conta ≤ 3                                                     |         168 |        35 | 28.3%     |      -0.086 |         | 19.9% – 36.6% |

## 5. Gênero, estado civil, região e idade carregam sinal DEPOIS das variáveis financeiras?

Modelo de hazard em tempo discreto (regressão logística por parcela; 50,957 parcelas-período de 5,771 contratos, 626 paradas). Controles financeiros: 33 termos (comprometimento com valor aprovado e degraus 28%/50%, renda, renda conta/declarada, saídas/entradas, déficit, cheque especial, saldo mínimo, volatilidade, score, restrições, consultas, histórico no birô, tempo de conta, prazo, vínculo, tempo do contrato). Teste da razão de verossimilhança (LR) para cada bloco; AUC e log-loss fora da dobra (5 dobras agrupadas por contrato).

| bloco                   |   parâmetros extras |   LR χ² |   p-valor |   AUC fora da dobra |   log-loss fora da dobra |
|:------------------------|--------------------:|--------:|----------:|--------------------:|-------------------------:|
| só financeiro (base)    |                   0 |         |           |              0.7927 |                  0.05708 |
| + gênero                |                   2 |     0.6 |     0.746 |              0.7926 |                  0.05712 |
| + estado civil          |                   4 |     5   |     0.288 |              0.7922 |                  0.05707 |
| + região (CEP)          |                   9 |     6.4 |     0.697 |              0.7947 |                  0.05715 |
| + idade                 |                   2 |     0   |     0.986 |              0.7916 |                  0.05713 |
| + todos os demográficos |                  17 |    12.3 |     0.782 |              0.7932 |                  0.05721 |

Coeficientes dos termos demográficos no modelo completo (log-odds por 1 desvio-padrão; referência: feminino, casado, SP capital/RM):

|      |   gen_masculino |   gen_nao_informado |   ec_divorciado |   ec_solteiro |   ec_uniao_estavel |   ec_viuvo |   reg_BA/SE |   reg_CE/PI/MA/PA/AM/AP/RR/AC |   reg_DF/GO/TO/MT/MS/RO |   reg_MG |   reg_PE/AL/PB/RN |   reg_PR/SC |   reg_RJ/ES |   reg_RS |   reg_SP interior |   idade |   idade2 |
|:-----|----------------:|--------------------:|----------------:|--------------:|-------------------:|-----------:|------------:|------------------------------:|------------------------:|---------:|------------------:|------------:|------------:|---------:|------------------:|--------:|---------:|
| coef |          -0.029 |               0.011 |          -0.028 |          0.01 |             -0.029 |     -0.108 |       0.016 |                         0.033 |                   0.009 |    0.041 |            -0.032 |      -0.002 |       0.007 |    0.031 |             0.088 |   0.012 |    0.002 |

Mesmo teste com gradient boosting (captura não linearidades): AUC fora da dobra 0.7922 → 0.7895; log-loss 0.05601 → 0.05620.

**Estratificação:** dentro do perfil financeiro limpo (saídas/entradas < 80%, < 3 meses de cheque especial, parcela ≤ 28% da renda estimada, renda conta/declarada ≥ 60%, sem restrição; n = 5,256 aprovados), a PD de vida por grupo demográfico:

_genero_

| grupo         |   contratos |   pararam | pd_vida   |   margem_R$ | aviso   | IC95         |
|:--------------|------------:|----------:|:----------|------------:|:--------|:-------------|
| feminino      |        2610 |       168 | 9.7%      |       0.057 |         | 8.2% – 11.1% |
| masculino     |        2590 |       138 | 7.9%      |       0.07  |         | 6.5% – 9.2%  |
| nao_informado |          56 |         3 | 7.8%      |       0.073 |         | 0.0% – 16.5% |

_estado_civil_

| grupo         |   contratos |   pararam | pd_vida   |   margem_R$ | aviso   | IC95         |
|:--------------|------------:|----------:|:----------|------------:|:--------|:-------------|
| casado        |        1888 |       119 | 9.1%      |       0.061 |         | 7.5% – 10.7% |
| divorciado    |         513 |        28 | 8.0%      |       0.067 |         | 5.0% – 11.0% |
| solteiro      |        2074 |       124 | 9.1%      |       0.063 |         | 7.5% – 10.7% |
| uniao_estavel |         622 |        34 | 8.5%      |       0.064 |         | 5.6% – 11.4% |
| viuvo         |         159 |         4 | 3.7%      |       0.092 |         | 0.0% – 7.6%  |

_regiao_

| grupo                   |   contratos |   pararam | pd_vida   |   margem_R$ | aviso   | IC95         |
|:------------------------|------------:|----------:|:----------|------------:|:--------|:-------------|
| BA/SE                   |         785 |        43 | 8.3%      |       0.069 |         | 5.8% – 10.8% |
| CE/PI/MA/PA/AM/AP/RR/AC |         699 |        41 | 9.1%      |       0.062 |         | 6.4% – 11.9% |
| DF/GO/TO/MT/MS/RO       |         323 |        21 | 9.3%      |       0.061 |         | 5.4% – 13.2% |
| MG                      |         632 |        48 | 11.0%     |       0.046 |         | 8.0% – 14.1% |
| PE/AL/PB/RN             |         412 |        16 | 5.8%      |       0.081 |         | 2.9% – 8.7%  |
| PR/SC                   |         462 |        23 | 6.9%      |       0.079 |         | 4.0% – 9.7%  |
| RJ/ES                   |         583 |        26 | 7.1%      |       0.074 |         | 4.3% – 9.8%  |
| RS                      |         639 |        40 | 9.4%      |       0.06  |         | 6.4% – 12.3% |
| SP capital/RM           |         486 |        26 | 7.9%      |       0.069 |         | 4.8% – 10.9% |
| SP interior             |         235 |        25 | 15.6%     |       0.016 |         | 9.7% – 21.5% |

_faixa_idade_

| grupo   |   contratos |   pararam | pd_vida   |   margem_R$ | aviso   | IC95         |
|:--------|------------:|----------:|:----------|------------:|:--------|:-------------|
| <25     |         522 |        28 | 8.6%      |       0.065 |         | 5.4% – 11.8% |
| 25-34   |        1050 |        75 | 10.8%     |       0.049 |         | 8.4% – 13.2% |
| 35-44   |        1043 |        56 | 7.7%      |       0.071 |         | 5.6% – 9.7%  |
| 45-54   |        1041 |        61 | 8.8%      |       0.063 |         | 6.5% – 11.0% |
| 55-64   |        1282 |        79 | 9.3%      |       0.061 |         | 7.2% – 11.3% |
| 65+     |         318 |        10 | 4.3%      |       0.095 |         | 1.7% – 7.0%  |

## 6. Segmentação (k-means em variáveis financeiras e de birô, padronizadas)

Silhueta por k (amostra de 4.000): k=3: 0.217, k=4: 0.224, k=5: 0.222, k=6: 0.233, k=7: 0.178, k=8: 0.182

k = 6 (escolhido por interpretabilidade; a silhueta é baixa em todos os k — os clientes formam um contínuo, não grupos naturais bem separados). Medianas por cluster:

|   cluster |   renda_est (R$) |   renda_ratio |   parcela_pedida/renda |   outras_parc/renda |   saidas/entradas |   cv_entradas |   dias_cheque_mes |   meses_deficit |   score |   consultas_90d |   hist_bureau (meses) |   restricoes |
|----------:|-----------------:|--------------:|-----------------------:|--------------------:|------------------:|--------------:|------------------:|----------------:|--------:|----------------:|----------------------:|-------------:|
|         0 |          3959.00 |          0.86 |                   0.10 |                0.08 |              0.32 |          0.08 |              0.00 |            0.00 |  522.00 |            1.00 |                  6.00 |         0.00 |
|         1 |          4019.00 |          0.85 |                   0.10 |                0.09 |              0.32 |          0.08 |              0.00 |            0.00 |  771.00 |            1.00 |                 99.00 |         0.00 |
|         2 |          4049.00 |          0.86 |                   0.10 |                0.09 |              1.02 |          0.08 |              4.75 |            2.00 |  744.50 |            6.00 |                 75.00 |         1.00 |
|         3 |          3813.00 |          0.90 |                   0.10 |                0.06 |              0.31 |          0.50 |              0.00 |            0.00 |  756.50 |            1.00 |                 87.00 |         0.00 |
|         4 |          2300.00 |          0.85 |                   0.56 |                0.08 |              0.31 |          0.08 |              0.00 |            0.00 |  747.00 |            1.00 |                 78.00 |         0.00 |
|         5 |          1298.00 |          0.18 |                   0.11 |                0.10 |              0.31 |          0.00 |              0.00 |            0.00 |  720.00 |            1.00 |                 70.00 |         1.00 |

|   cluster |   pedidos hist | taxa_aprov   |   novos |   novos: atual aprova |   contratos |   pararam | pd_vida   | p_atraso   |   margem_R$ | volume   | aviso   | IC95            |
|----------:|---------------:|:-------------|--------:|----------------------:|------------:|----------:|:----------|:-----------|------------:|:---------|:--------|:----------------|
|         0 |           1780 | 15.4%        |     339 |                    11 |         274 |        20 | 10.8%     | 22.7%      |       0.046 | 1.87 mi  |         | 5.5% – 16.2%    |
|         1 |           5688 | 80.6%        |    1148 |                   923 |        4582 |       250 | 8.3%      | 20.8%      |       0.067 | 35.49 mi |         | 7.2% – 9.3%     |
|         2 |            490 | 32.0%        |      97 |                    24 |         157 |       102 | 100.0%    | 0.0%       |      -0.6   | 1.37 mi  |         | 100.0% – 100.0% |
|         3 |           1200 | 55.8%        |     241 |                   126 |         670 |        85 | 18.6%     | 20.9%      |      -0.01  | 5.39 mi  |         | 14.8% – 22.4%   |
|         4 |            538 | 57.4%        |     110 |                    54 |         309 |       146 | 63.9%     | 12.1%      |      -0.341 | 4.04 mi  |         | 57.2% – 70.6%   |
|         5 |            304 | 13.5%        |      65 |                     7 |          41 |        23 | 73.6%     | 19.8%      |      -0.422 | 0.17 mi  |         | 56.1% – 91.1%   |

## 7. Segmentos de oportunidade e de atenção (seção 9)

Definidos só com informação da data do pedido (valor PEDIDO para comprometimento, porque é o que se conhece antes de decidir). PD medida nos aprovados do histórico; contagem nos 2.000 novos com a política atual (score > 600, renda > 2.000, sem restrição, valor reduzido até a parcela caber em 30% da renda).

| segmento                                                   |   pedidos hist | taxa_aprov   |   aprovados | pd_vida   | IC95            |   margem_R$ | aviso   |   novos |   novos: atual aprova |   novos: atual nega |   novos: atual reduz valor |
|:-----------------------------------------------------------|---------------:|:-------------|------------:|:----------|:----------------|------------:|:--------|--------:|----------------------:|--------------------:|---------------------------:|
| S1 score ≤ 600 com finanças boas                           |           1190 | 12.5%        |         149 | 9.6%      | 2.8% – 16.5%    |       0.046 |         |     235 |                     0 |                 235 |                          0 |
| S1b score ≤ 600 sem finanças boas                          |           1195 | 10.8%        |         129 | 40.8%     | 27.1% – 54.5%   |      -0.177 |         |     210 |                     0 |                 210 |                          0 |
| S2 score > 700 com comprometimento excessivo               |           1343 | 55.5%        |         746 | 46.1%     | 41.7% – 50.5%   |      -0.214 |         |     273 |                   141 |                 132 |                         48 |
| S2b score > 700 sem comprometimento excessivo              |           4650 | 82.4%        |        3831 | 8.3%      | 7.1% – 9.4%     |       0.068 |         |     961 |                   777 |                 184 |                          0 |
| S3 bom histórico e baixa exposição                         |           1260 | 93.1%        |        1173 | 6.1%      | 4.3% – 7.8%     |       0.084 |         |     236 |                   215 |                  21 |                          0 |
| S4 aposentado/servidor com finanças boas                   |            506 | 71.7%        |         363 | 5.6%      | 2.7% – 8.5%     |       0.085 |         |      99 |                    72 |                  27 |                          0 |
| S5 deterioração: entradas últimos 3m caíram ≥ 10%          |           1029 | 56.6%        |         582 | 19.4%     | 15.3% – 23.6%   |      -0.016 |         |     216 |                   119 |                  97 |                          7 |
| S5b deterioração: saídas últimos 3m subiram ≥ 10%          |           1651 | 52.0%        |         859 | 31.8%     | 27.7% – 35.9%   |      -0.104 |         |     325 |                   136 |                 189 |                          5 |
| S5c deterioração: cheque especial novo (só nos últimos 3m) |            527 | 35.3%        |         186 | 76.5%     | 67.9% – 85.1%   |      -0.431 |         |     114 |                    33 |                  81 |                          1 |
| S5d deterioração: saídas/entradas 3m ≥ 90%                 |            490 | 31.8%        |         156 | 100.0%    | 100.0% – 100.0% |      -0.6   |         |      97 |                    24 |                  73 |                          0 |
| S6 atípico: renda pela conta > 105% da declarada           |            512 | 58.4%        |         299 | 16.9%     | 11.6% – 22.3%   |       0.004 |         |      97 |                    59 |                  38 |                          3 |
| S6b atípico: entradas não salariais > 50% (assalariado)    |              0 |              |           0 | n<30      |                 |             |         |       0 |                     0 |                   0 |                          0 |
| S6c atípico: pico de saídas ≥ 2× a mediana                 |            982 | 39.6%        |         389 | 51.7%     | 45.0% – 58.4%   |      -0.252 |         |     204 |                    68 |                 136 |                          2 |
| S7 conta < 12 meses de movimentação                        |           1429 | 52.1%        |         744 | 14.3%     | 11.2% – 17.5%   |       0.025 |         |     307 |                   155 |                 152 |                         13 |
| S8 1+ restrição ativa                                      |           1986 | 6.4%         |         127 | 40.2%     | 24.9% – 55.6%   |      -0.185 |         |     377 |                     0 |                 377 |                          0 |

S6b não tem nenhum caso: em todo assalariado as entradas de salário são a maior parte das entradas (a base não traz o padrão 'assalariado vivendo de outras entradas').

**Sinais líquidos:** dentro dos aprovados que já passam pelos filtros conhecidos (saídas/entradas 12m < 80% e 3m < 90%, < 3 meses de cheque especial, parcela aprovada ≤ 28% da renda estimada, renda conta/declarada ≥ 60%, sem restrição; n = 5,256, PD 8.8%), quanto cada sinal ainda acrescenta:

|                                                                          |   contratos |   pararam | pd_vida   | IC95         |   margem_R$ |
|:-------------------------------------------------------------------------|------------:|----------:|:----------|:-------------|------------:|
| S5 deterioração: entradas últimos 3m caíram ≥ 10% · com o sinal          |         494 |        37 | 10.7%     | 7.3% – 14.2% |       0.049 |
| S5 deterioração: entradas últimos 3m caíram ≥ 10% · sem o sinal          |        4762 |       272 | 8.5%      | 7.5% – 9.6%  |       0.065 |
| S5b deterioração: saídas últimos 3m subiram ≥ 10% · com o sinal          |         633 |        55 | 13.1%     | 9.6% – 16.5% |       0.033 |
| S5b deterioração: saídas últimos 3m subiram ≥ 10% · sem o sinal          |        4623 |       254 | 8.2%      | 7.2% – 9.2%  |       0.068 |
| S5c deterioração: cheque especial novo (só nos últimos 3m) · com o sinal |          44 |         3 | 9.3%      | 0.0% – 19.6% |       0.066 |
| S5c deterioração: cheque especial novo (só nos últimos 3m) · sem o sinal |        5212 |       306 | 8.7%      | 7.8% – 9.7%  |       0.064 |
| S6c atípico: pico de saídas ≥ 2× a mediana · com o sinal                 |         185 |        21 | 16.1%     | 9.5% – 22.6% |       0.01  |
| S6c atípico: pico de saídas ≥ 2× a mediana · sem o sinal                 |        5071 |       288 | 8.5%      | 7.5% – 9.5%  |       0.066 |
| S7 conta < 12 meses de movimentação · com o sinal                        |         634 |        30 | 6.8%      | 4.4% – 9.3%  |       0.08  |
| S7 conta < 12 meses de movimentação · sem o sinal                        |        4622 |       279 | 9.0%      | 8.0% – 10.1% |       0.061 |

**Renda pela conta < 60% da declarada × meses de movimentação** (pedidos históricos; PD nos aprovados, n ≥ 20):

| mm         | renda conta < 60% decl.       | ≥ 60%                            |
|:-----------|:------------------------------|:---------------------------------|
| 1-2 meses  | 304 pedidos · PD 83.5% (n=43) | 196 pedidos · PD 11.6% (n=133)   |
| 12 meses   | 38 pedidos · PD n=19          | 8533 pedidos · PD 15.5% (n=5270) |
| 3-11 meses | 9 pedidos · PD n=5            | 920 pedidos · PD 10.0% (n=563)   |

**Score × meses de histórico no birô** (10.000 pedidos históricos): o score baixo é, na prática, cadastro novo no birô.

| meses_historico_bureau   |   <500 |   500-600 |   601-700 |   701-800 |   800+ |
|:-------------------------|-------:|----------:|----------:|----------:|-------:|
| 0-6                      |    426 |       735 |         0 |         0 |      0 |
| 7-12                     |    312 |       521 |        11 |        11 |     18 |
| 13-24                    |      1 |        23 |       120 |       214 |    217 |
| 25-60                    |      2 |        79 |       372 |       613 |    656 |
| 60+                      |     32 |       254 |      1119 |      2100 |   2164 |

Referência: todos os aprovados, n = 6,033, PD vida 15.4% [14.3% – 16.6%], margem +0.014 por R$.

**Controle de safra para S1:** score ≤ 600 só foi aprovado no piloto (out/25–mar/26). Comparação justa é com o piloto de score > 600 nas mesmas condições de finanças:

|                                    |   contratos |   pararam | pd_vida   | p_atraso   |   margem_R$ | aviso   | IC95          |
|:-----------------------------------|------------:|----------:|:----------|:-----------|------------:|:--------|:--------------|
| piloto, score ≤ 600, finanças boas |         149 |        10 | 9.6%      | 32.0%      |       0.046 |         | 2.8% – 16.5%  |
| piloto, score > 600, finanças boas |         464 |        23 | 6.0%      | 22.3%      |       0.082 |         | 3.3% – 8.7%   |
| piloto, score ≤ 600, sem restrição |         250 |        34 | 23.6%     | 25.1%      |      -0.052 |         | 14.9% – 32.2% |
| piloto, score > 600, sem restrição |         749 |        83 | 18.0%     | 17.8%      |      -0.003 |         | 13.4% – 22.6% |
| piloto, score ≤ 600, todos         |         278 |        41 | 25.7%     | 25.8%      |      -0.069 |         | 17.1% – 34.2% |
| piloto, score > 600, todos         |         848 |       105 | 20.6%     | 19.9%      |      -0.024 |         | 15.9% – 25.2% |
