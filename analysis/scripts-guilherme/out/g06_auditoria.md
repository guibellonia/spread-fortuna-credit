# Auditoria dos cenários A–H e da tabela de inadimplência por grupo

Script: `analysis/scripts-guilherme/g06_auditoria_cenarios.py` (só leitura; reproduz `src/cenarios.py` com as saídas redirecionadas para `out/g06_saida/`). Birô dos novos: cache `data/cache/bureau/` (2.000/2.000).

Modelo 'antigo' (3 classes, `src/modelo.py`): (HistGradientBoostingClassifier(l2_regularization=1.0, learning_rate=0.04,
                               max_iter=300, max_leaf_nodes=15,
                               min_samples_leaf=40, random_state=42), {'auc_inadimplencia_validacao_temporal': 0.775, 'n_treino': 4664, 'taxa_inadimplencia_treino': 0.1229}). Modelo corrigido (`src/cenarios.py`): {'auc': 0.75, 'inad_projetada_base': 0.1429, 'inad_media_modelo': 0.1429}.

## Resumo da auditoria (números desta execução; detalhe e fonte nas seções 1–6)

1. **Reprodução:** os 8 cenários batem com o código de `src/cenarios.py` (aprovados e volume exatos; resultado ±R$ 1 mil).
   O `validacao/final.log` (A = R$ 193 mil, B = 1.559) é outra conta: o resultado de A lá é idêntico (193.174,25) ao que o
   avaliador `tool_risco` dá aqui; o B de lá é outra seleção.
2. **Auto-avaliação infla o resultado.** O modelo corrigido escolhe E–H e também os mede. Nos aprovados de G ele prevê
   PD 5,9%; os avaliadores independentes dão 8,1% (`tool_risco`) e 8,5% (KM por célula). Resultado de G: 859 → 669–694 mil
   (−19% a −22%). O **ganho sobre A** cai menos (568 → 501–526 mil, −7% a −12%) porque o resultado de A também estava
   superestimado (292 → 143–193 mil).
3. **Cada modelo prefere a própria seleção.** G − B: +42 mil pelo corrigido, −52 mil pelo modelo antigo, +6 / +3 mil pelos
   neutros. E − C: +34 mil, −40 mil, +10 / +6 mil. As diferenças B×G×H e C×E estão dentro do viés do avaliador.
   O que é robusto em todos os avaliadores: toda proposta ganha da atual (~350–650 mil) e "sem corte de score" (B, G)
   supera "score > 600" (C, E) em ~130–140 mil nos avaliadores neutros.
4. **Onde está o ganho:** a política atual reduz 61 pedidos novos para parcela = 30% da renda. PD prevista nesses 61:
   52% (corrigido) / 55% (KM). No histórico, os 347 reduzidos têm PD de vida 61,2% [IC 54,8–67,5] e margem −0,32 por R$.
   Só esses 61 tiram 192–213 mil do resultado de A: ~35–40% do ganho de qualquer proposta vem de não emprestar a eles.
5. **Premissas não equivalentes:** B, C e D são escolhidos pelo modelo antigo (rótulo ingênuo, treino até mar/26, risco ≤ 20%)
   e avaliados pelo corrigido; E–H são escolhidos e avaliados pelo corrigido. Todos são vida inteira, mas com 23% fixo de
   pagadores com atraso para qualquer pedido (otimista nos grupos de risco, onde chega a ~50%). O corte de 17,5% está na
   escala do modelo corrigido, que é calibrado no estimador w-90d, e esse estimador subestima (item 7).
6. **D ≈ C e F ≈ E:** os filtros extras pegam 171 novos; 170 já eram negados em C e E (122 restrição, 21 por 2+ meses com
   saldo negativo, 18 score, 9 risco). Sobra 1. Os filtros são redundantes com a v2, não inúteis: na política atual cortariam 31.
7. **Tabela 19,4% / 7,7% / 8,0%:** reproduzida com o estimador `pesos_censura` (evento = 90+ dias; peso = parcelas vencidas
   até o corte / janela). 278 = todos os aprovados com score ≤ 600, **100% do piloto** (out/25–mar/26, mediana jan/26);
   4.833 inclui 208 contratos sem parcela vencida (peso 0): n efetivo 4.625. Esse estimador mistura evento de 90 dias com
   parcelas vencidas há menos de 90 dias e **subestima**: com KM e regra de 61 dias, 19,4% → **25,7%** [17,1–34,2];
   7,7% → **9,0%** [3,2–14,7]; 8,0% → **8,4%** [7,4–9,4]. A queda vem de três filtros: parcela ≤ 20% da renda
   (−26 contratos / −12 paradas), restrição (−28 / −7) e ≤ 1 mês negativo (−11 / −8); os filtros extras tiram 1 / 1.
   Os mesmos filtros levam score > 600 de 15,1% para 8,4%: o score baixo não "melhora", os filtros tiram o mesmo tipo de
   risco dos dois grupos. Diferença pós-filtro (≤ 600 − > 600) = +0,5 p.p., IC95 [−4,4; +6,7]; contra > 600 do próprio
   piloto, +1,1 [−4,6; +7,5]. Indistinguível, mas com 212 contratos e 13 paradas o limite superior (~15%) fica perto do
   equilíbrio (~17,5%): é "consistente com não haver diferença", não "provado igual".
8. **Backtest fora do tempo** (treino até 30/09/25; teste = aprovados de out/25–mar/26; valor ≤ o aprovado na época):
   no horizonte observado, C ganha +180 mil [IC 116; 248] e G +217 mil [131; 297] sobre A. Projetando a vida inteira por KM,
   C +125 mil [31; 239] e G +61 mil [−94; +189]: **G não é estatisticamente melhor que A na vida inteira** nesse teste.
   O modelo treinado em 30/09/25 previa PD 3,1% para os aprovados de G; o KM observado é 16,4%. Mal calibrado, o corte de
   risco não morde e G vira "só filtros". 264 aprovações de G no teste não têm desfecho (negados na época): viés de seleção.
   O piloto como foi rodado (todos os aprovados históricos) perde −306 mil [−494; −150] contra A no mesmo teste.

**O que corrigir na conta do time**
- Apresentar o resultado com avaliador independente e em faixa: ganho de G sobre A ≈ **R$ 500–570 mil** (não 568 cravado);
  resultado absoluto ≈ 670–860 mil.
- Calibrar o modelo corrigido contra KM com regra de 61 dias (como `tool_risco` já faz, isotônica) antes de usar o corte de
  17,5%; ou usar `tool_risco` como modelo de decisão. Unificar o rótulo de calote (61 dias) em todas as contas.
- Usar P(atraso) por pedido (ex.: `tool_risco`) em vez de 23% fixo.
- Não vender B, G e H como diferentes entre si: a diferença é menor que o viés do avaliador. Escolher por robustez.
- Trocar a tabela 19,4 / 7,7 / 8,0 por KM 61 dias com IC (25,7 / 9,0 / 8,4) e n efetivo; dizer que ≤ 600 é só piloto.
- Tirar D e F da comparação, ou explicar que os filtros já estão contidos na v2.
- No pitch: o maior item do ganho é não reduzir para 30% quem não cabe (61 pedidos, ~200 mil).


## 1. Reprodução dos cenários (avaliador original: modelo corrigido de `src/cenarios.py`)

| cenário | aprov. prompt | aprov. reproduzido | volume prompt (mi) | volume reprod. (mi) | resultado prompt (mil) | resultado reprod. (mil) | ganho reprod. (mil) | PD média reprod. |
|---|---|---|---|---|---|---|---|---|
| A | 1,145.00 | 1145 | 8.86 | 8.86 | 292.00 | 291.59 | 0.00 | 12.9% |
| B | 1,550.00 | 1550 | 10.16 | 10.16 | 817.00 | 817.23 | 525.64 | 6.4% |
| C | 1,209.00 | 1209 | 7.97 | 7.97 | 645.00 | 645.47 | 353.88 | 6.3% |
| D | 1,208.00 | 1208 | 7.96 | 7.96 | 645.00 | 645.38 | 353.79 | 6.3% |
| E | 1,192.00 | 1192 | 8.09 | 8.09 | 679.00 | 679.36 | 387.77 | 5.9% |
| F | 1,191.00 | 1191 | 8.08 | 8.08 | 679.00 | 679.27 | 387.68 | 5.9% |
| G | 1,527.00 | 1527 | 10.22 | 10.22 | 859.00 | 859.48 | 567.89 | 5.9% |
| H | 1,435.00 | 1435 | 9.59 | 9.59 | 800.00 | 800.01 | 508.42 | 6.0% |

## 2. Mesmas decisões, avaliadores diferentes (R$ mil, vida inteira, regra +15/+5/−60)

| cenário | corrigido (original) | ganho | corrigido +20% risco | ganho  | KM por célula | ganho   | PD KM | tool_risco (hazard) | ganho    | PD tool | modelo antigo (3 cl.) | ganho     |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 292 | 0 | 126 | 0 | 143 | 0 | 15.4% | 193 | 0 | 14.4% | 337 | 0 |
| B | 817 | 526 | 723 | 597 | 663 | 520 | 8.5% | 692 | 498 | 8.1% | 984 | 647 |
| C | 645 | 354 | 572 | 446 | 527 | 384 | 8.6% | 546 | 353 | 8.1% | 766 | 429 |
| D | 645 | 354 | 572 | 446 | 526 | 383 | 8.6% | 546 | 353 | 8.1% | 765 | 429 |
| E | 679 | 388 | 610 | 484 | 537 | 394 | 8.5% | 552 | 359 | 8.1% | 725 | 389 |
| F | 679 | 388 | 610 | 484 | 536 | 393 | 8.5% | 552 | 359 | 8.1% | 725 | 388 |
| G | 859 | 568 | 772 | 646 | 669 | 526 | 8.5% | 694 | 501 | 8.1% | 932 | 595 |
| H | 800 | 508 | 717 | 590 | 629 | 486 | 8.5% | 652 | 459 | 8.1% | 866 | 530 |

## 3. Reduzidos pela regra dos 30% (política atual)

| grupo | contratos | pararam | ingênua | PD vida (KM) | IC95 | P(em dia) | margem por R$ |
|---|---|---|---|---|---|---|---|
| reduzidos (histórico) | 347 | 159 | 45.8% | 61.2% | 54.8% – 67.5% | 26.7% | -0.321 |
| não reduzidos, política atual | 4617 | 359 | 7.8% | 11.5% | 10.3% – 12.7% | 68.6% | +0.044 |
| todos os aprovados | 6033 | 626 | 10.4% | 15.4% | 14.3% – 16.6% | 64.7% | +0.014 |

Nos 2.000 novos, a política atual aprova 1145 e **reduz o valor de 61** (parcela = 30% da renda declarada). PD média atribuída a esses reduzidos: modelo corrigido **52.4%**, KM por célula **55.2%**; nos não reduzidos: 8.7% vs 11.0%. Resultado de A só nos reduzidos: modelo corrigido R$ -192 mil; KM por célula R$ -213 mil.

## 4. Por que D ≈ C e F ≈ E (filtros de saídas e renda real)

Nos novos: saídas ≥ 80% das entradas = 97; renda real < 60% da declarada = 74; união = 171 pedidos.

| política base | pegos pelos filtros extras | já negados | ainda aprovados (D/F removem) | motivo da negação já existente |
|---|---|---|---|---|
| C | 171 | 170 | 1 | {'restrição ativa no bureau': 122, '2+ meses com saldo negativo na conta': 21, 'score até 600': 18, 'risco acima do limite ou ganho esperado negativo': 9} |
| E | 171 | 170 | 1 | {'restrição ativa no bureau': 122, '2+ meses com saldo negativo na conta': 21, 'score até 600': 18, 'risco acima do limite ou ganho esperado negativo': 9} |
| G | 171 | 168 | 3 | {'restrição ativa no bureau': 122, '2+ meses com saldo negativo na conta': 30, 'risco acima do limite ou ganho esperado negativo': 16} |
| A | 171 | 140 | 31 | {} |

## 5. Tabela "inadimplência projetada por grupo" (19,4% / 7,7% / 8,0%)

**Definição que reproduz os números** (testadas: KM, w do time com regra de 61 dias, cal3×2,92, w com rótulo de 90 dias): é o estimador `pesos_censura` de `src/cenarios.py` — evento = `situacao_final = 'inadimplente'` (90+ dias), peso w = min(parcelas vencidas até o corte, janela)/janela, janela = ⌈2/3 do prazo⌉, inadimplente pesa 1; taxa = eventos / Σw. Filtros = os da v2 (restrição = 0, ≤1 mês com saldo negativo, parcela aprovada ≤ 20% da renda declarada) **mais** os extras de D (saídas ≥ 80% das entradas, renda real < 60% da declarada).

| grupo (aprovados históricos) | contratos | com peso > 0 | pararam (61d) | inadimplente (90d) | w-90d (time) | KM vida (61d) | IC95 KM | % piloto | safra mediana |
|---|---|---|---|---|---|---|---|---|---|
| score ≤ 600, sem filtro | 278 | 278 | 41 | 35 | 19.4% | 25.7% | 17.1% – 34.2% | 100.0% | 2026-01-07 |
| score ≤ 600, filtrado | 212 | 212 | 13 | 10 | 7.7% | 9.0% | 3.2% – 14.7% | 100.0% | 2026-01-08 |
| score > 600, sem filtro | 5755 | 5516 | 585 | 547 | 14.1% | 15.1% | 13.9% – 16.3% | 14.7% | 2025-10-05 |
| score > 600, filtrado | 4833 | 4625 | 273 | 253 | 8.0% | 8.4% | 7.4% – 9.4% | 13.3% | 2025-10-01 |
| score > 600, filtrado, só piloto | 643 | 643 | 36 | 32 | 8.1% | 7.9% | 4.8% – 11.1% | 100.0% | 2025-12-29 |
| score > 600, filtrado, safras 2025T4–2026T1 | 1228 | 1228 | 64 | 56 | 7.4% | 7.7% | 5.3% – 10.1% | 52.4% | 2025-12-30 |

**Decomposição da queda no grupo score ≤ 600** (filtros aplicados em sequência):

| passo | contratos | paradas (61d) | w-90d (time) | KM vida | removidos (contratos / paradas) |
|---|---|---|---|---|---|
| todos (score ≤ 600) | 278 | 41 | 19.4% | 25.7% |  |
| + restrição = 0 | 250 | 34 | 17.3% | 23.6% | 28 contratos / 7 paradas |
| + ≤1 mês com saldo negativo | 239 | 26 | 13.8% | 19.0% | 11 contratos / 8 paradas |
| + parcela ≤ 20% da renda declarada | 213 | 14 | 8.4% | 9.4% | 26 contratos / 12 paradas |
| + saídas < 80% e renda real ≥ 60% | 212 | 13 | 7.7% | 9.0% | 1 contratos / 1 paradas |

| filtro (isolado) | contratos (score ≤ 600) | paradas | KM vida do grupo removido | contratos (score > 600) | KM vida (score > 600) |
|---|---|---|---|---|---|
| restrição ≥ 1 | 28 | 7 | 44.4% | 99 | 37.4% |
| 2+ meses saldo negativo | 16 | 10 | 86.9% | 155 | 80.6% |
| parcela > 20% renda | 27 | 13 | 59.3% | 662 | 39.4% |
| filtros extras de D | 17 | 13 | 100.0% | 194 | 94.5% |

Diferença KM (≤600 − >600), filtrados: **+0.5 p.p.**, IC95 bootstrap [-4.4; +6.7] (500 reamostragens). Contra >600 só do piloto (mesma safra e política): **+1.1 p.p.**, IC95 [-4.6; +7.5].

## 6. Backtest fora do tempo (corte simulado em 30/09/2025)

Treino: 2624 aprovados até 30/09/2025 com desfecho reconstruído nessa data (pagamentos posteriores apagados). Teste: pedidos de out/2025 a mar/2026 (2510; 1820 aprovados com desfecho até 30/09/2026, 6 a 12 parcelas observadas). Valor = o da regra limitado ao aprovado na época, com o desfecho observado daquele contrato (conservador para quem reduz: o risco no valor menor seria igual ou menor).

| regra (valor = aprovado histórico) | aprova com desfecho | dos quais com valor reduzido | aprova sem desfecho (negados no histórico) | volume (mi) | paradas obs. | resultado no horizonte observado (mil) | PD vida KM | resultado vida KM (mil) | PD prevista (modelo em S) | resultado projetado (mil) | ganho vs A no horizonte observado (mil) | ganho vs A vida KM (mil) | ganho vs A projetado (mil) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A (atual) | 1393 | 47 | 0 | 11.5 | 141 | 432.2 | 17.2% | 11.9 | 5.9% | 854.7 | 0.0 | 0.0 | 0.0 |
| C (antigo, risco≤20%, score>600) | 1362 | 169 | 51 | 10.4 | 120 | 612.2 | 15.6% | 136.5 | 3.2% | 1,067.6 | 180.0 | 124.6 | 212.9 |
| G (corrigido, risco≤17,5%, sem score) | 1601 | 193 | 264 | 12.0 | 150 | 649.4 | 16.4% | 72.4 | 3.1% | 1,246.4 | 217.2 | 60.5 | 391.8 |
| aprovados históricos (atual+piloto) | 1820 | 0 | 0 | 14.5 | 211 | 282.8 | 19.8% | -293.9 | 6.8% | 929.3 | -149.4 | -305.8 | 74.6 |

IC95 do ganho sobre A por bootstrap pareado (300 reamostragens de contratos do teste), R$ mil:

- C (antigo, risco≤20%, score>600): vida inteira (KM) [+31; +239] · horizonte observado [+116; +248]
- G (corrigido, risco≤17,5%, sem score): vida inteira (KM) [-94; +189] · horizonte observado [+131; +297]
- aprovados históricos (atual+piloto): vida inteira (KM) [-494; -150] · horizonte observado [-268; -37]

