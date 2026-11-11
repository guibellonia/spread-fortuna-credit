# Análise de crédito, comportamento financeiro e política de aprovação · Guilherme

Base: PostgreSQL `fortuna`, schema `hackathon` (corte 30/09/2026). Tudo aqui sai de código em
`analysis/scripts-guilherme/` (só leitura do banco). Saídas completas em `analysis/scripts-guilherme/out/`.
Complementa `analise-banco.md` (Juliano), `analise-enio.md` e `censura-agregado.md`. Não substitui nenhum deles.

| Script | O que produz | Saída |
|---|---|---|
| `g01_diagnostico.py` | estrutura, volumes, nulos, integridade, consistências | `out/g01_diagnostico.txt` |
| `g02_base.py` | base por pedido (só informação da data do pedido) + desfecho com censura | `out/base.pkl`, `out/periodos.pkl` |
| `g_util.py` | PD de vida inteira por Kaplan-Meier com IC 95% (usada em todas as tabelas) | — |
| `g03_perfil.py` | perfil socioeconômico, cruzamentos, interações, clusters, segmentos | `out/g03_perfil.md` |
| `g04_financeiro.py` | reconstrução financeira, indicadores de endividamento × inadimplência | `out/g04_financeiro.md` |
| `g05*.py` | modelos de risco, validação fora do tempo | `out/g05*_*.md` |
| `g06_auditoria_cenarios.py` | auditoria dos cenários A–H e da tabela 19,4 / 7,7 / 8,0 | `out/g06_auditoria.md` |
| `g07_otimizacao.py` | grade de políticas e fronteira risco × resultado nos 2.000 novos | `out/g07_otimizacao.md` |
| `g08_reducao.py` | teste decisivo da redução de valor e CSV da política recomendada | `out/g08_reducao.md`, `out/g08_decisoes_recomendadas.csv` (gerado por `g08`, não versionado: tem ids de pedido) |

Rodar tudo (da raiz, ~8 min): `for s in g01_diagnostico g02_base g03_perfil g04_financeiro g05_modelo g05b_modelo_em g05c_modelo_final g06_auditoria_cenarios g07_otimizacao g08_reducao; do .venv/Scripts/python analysis/scripts-guilherme/$s.py; done`
(precisa de `tabulate` no `.venv`).

**Convenções.** "PD vida" = inadimplência de vida inteira estimada por Kaplan-Meier no tempo relativo do contrato
(parcela ÷ prazo), com IC 95% de Greenwood. "Parou" = parcela vencida há 61+ dias sem pagamento: nenhuma parcela paga
atrasou mais de 60 dias, e parar é definitivo. "Margem" = resultado esperado por R$ aprovado
(+0,15 em dia, +0,05 atraso, −0,60 não paga). **Observado** = contado na base. **Estimado** = KM ou modelo sobre a base.
**Projetado** = aplicado aos 2.000 novos.

---

## A. Resumo executivo

1. **A carteira tem PD de vida inteira de 15,4% [14,3–16,6]** (6.033 aprovados, R$ 48,3 mi). A taxa ingênua (10,4%)
   subestima, porque 4.523 contratos estão abertos. Política atual: 14,5% [13,2–15,7], margem +0,022/R$.
   Piloto: **21,8% [17,7–25,9], margem −0,035/R$**: deu prejuízo como um todo.
2. **O fator mais forte é saída alta.**
   - Nova parcela ≥ 50% da sobra mensal (entradas − saídas): **100% param** (190 contratos, fora da "conta apertada").
   - Saídas > entradas em algum dos 3 meses antes: 100% (156).
   - Saídas ≥ 80% das entradas: 100% (156).
   - Saídas subindo ≥ 50% nos 3 meses antes: **71% [63–79]** (244).
3. **Reduzir o valor não tira o risco.** Os 347 contratos que a política atual reduziu até a parcela caber em 30% da
   renda têm **PD 61% [55–68]**. Os não reduzidos com o mesmo comprometimento aprovado ficam em ~10%. Mesmo sem conta
   apertada e com parcela < 45% da sobra, os reduzidos ficam em 37% [25–49], contra 9% (`g04`).
   O risco acompanha o **valor pedido**, não só o aprovado.
4. **O score quase não separa risco.**
   - Acima de 600, toda faixa fica entre 13% e 16%.
   - AUC fora do tempo: 0,69 do score, **0,79–0,81** do modelo com a conta corrente, **0,55** da regra atual.
   - Score ≤ 600 é, na prática, cadastro novo no birô: 1.994 dos 2.385 têm ≤ 12 meses de histórico.
5. **Gênero, estado civil, região e idade não acrescentam nada** depois das variáveis financeiras
   (LR χ² = 12,3, 17 g.l., p = 0,78; AUC 0,7896 → 0,7870). Não devem entrar na política.
6. **Os cenários A–H do time se reproduzem, mas o ganho está inflado.**
   - O modelo que escolhe também mede (auto-avaliação).
   - Com avaliadores independentes, G ganha **R$ 501–526 mil** sobre A, não 568 mil.
   - B, G e H não se distinguem entre si.
   - Os filtros extras de D e F são redundantes: 170 dos 171 pedidos já eram negados.
7. **O ganho do G depende de a redução de valor funcionar.** O G reduz 478 pedidos, 98 deles de clientes que pedem
   parcela > 30% da renda (o caso que deu 61% de calote). Se a redução não aliviar o risco, como mostrou o histórico,
   o ganho do G cai para **R$ 227 mil**.
8. **Política recomendada: G + negar (em vez de reduzir) quem pede acima da capacidade.**
   "Acima da capacidade" = parcela pedida > 30% da renda declarada ou ≥ 50% da sobra.
   - Aprova 1.421, R$ 9,48 mi.
   - Ganho sobre a atual de **R$ 454–481 mil** se a redução funcionar e **R$ 515–553 mil** se não funcionar.
   - É a política de melhor pior caso entre as ~40 testadas (`g08`). CSV gerado por `g08` e validado (não versionado: tem ids de pedido):
     `out/g08_decisoes_recomendadas.csv`.

**Principais riscos.**
- Toda PD é condicional à aprovação (viés de seleção). Score ≤ 600, restrição e renda < 2 mil só têm desfecho no
  piloto (6 meses de safra).
- Prazos de 24 e 36 meses ainda não chegaram ao fim; a janela de parada é extrapolada.
- Nenhuma base permite medir o efeito de reduzir o valor para níveis diferentes de 30% da renda.

---

## B. Perfil dos clientes (`out/g03_perfil.md`, seção 1)

- **12.000 clientes, 1 pedido cada** (10.000 históricos de out/24 a set/26; 2.000 novos em out/26).
  **Não existe histórico de recompra:** a seção 4.2 do pedido (compras, intervalos, parcelamentos simultâneos na
  Fortuna) não é reconstruível. Os únicos compromissos anteriores vêm do birô, só como fluxo mensal.
- **Os novos têm o mesmo perfil dos históricos** (qui² p ≥ 0,09 em gênero, região, vínculo, estado civil, idade,
  prazo e score). Exceções pequenas: renda 2–3 mil (+2,6 p.p.; p = 0,028) e pedidos < R$ 3 mil (+2,6 p.p.; p = 0,030).
- **Distribuição:**
  - Gênero: 49,7% F, 49,3% M, 1% não informado.
  - Vínculo: assalariado 55%, autônomo 24%, empresário 10%, aposentado 10%.
  - Idade: mediana 45 anos.
  - Tempo de conta: mediana 47 meses; 15% com menos de 1 ano.
- **Renda declarada:** mediana R$ 4.600, p90 R$ 9.750. A renda identificada na conta é **85% da declarada** (mediana).
- **Profissão:** 46 profissões. Na profissão, o risco vem do vínculo e do comprometimento, não do cargo.
  "Advogado" aparece como assalariado (130) e como autônomo (70).
- **Geografia:** os CEPs são sintéticos (85 prefixos de 3 dígitos, 17 UFs). O ticket varia por região (p < 0,001),
  mas valor/renda não (p = 0,62): a diferença de ticket é de renda.
- **Consumo:** pedido mediano de R$ 6.000, prazo mediano de 24 meses, parcela pedida = 10% da renda estimada (mediana).
  Gênero não muda o ticket (R$ 8.100 × R$ 8.027; p = 0,53).

---

## C. Diagnóstico financeiro (`out/g04_financeiro.md`)

### Reconstrução (12 meses antes do pedido; nenhum mês igual ou posterior ao do pedido, sem vazamento)

| Mediana (históricos) | R$ |
|---|---:|
| Renda declarada | 4.600 |
| Renda identificada na conta | 3.795 |
| Entradas, média / mediana mensal | 4.017 / 3.999 |
| Outras entradas (não salário) | 467 |
| Saídas, média / mediana | 1.302 / 1.254 |
| Sobra mensal (entradas − saídas) | 2.625 |
| Parcelas em outras instituições (birô) | 256 |

- **Autônomos e empresários:** o "salário" é só 10% das entradas. A renda deles foi medida pelas entradas totais.
  Para assalariados e aposentados, pelas entradas de salário.
- **Regularidade e sazonalidade:** todo mês tem salário > 0. Não há sazonalidade relevante: o índice mensal fica entre
  0,99 e 1,01, só julho tem saídas +5%. CV das entradas: mediana 0,09; 0,23–0,25 em autônomo e empresário.
- **Despesas extraordinárias:** pico de saída = 1,17× a mediana no caso típico; p90 = 2×.
- **Limites da base:**
  - A movimentação é agregada por mês. Não dá para separar transferências entre contas, estornos, empréstimos
    recebidos ou reembolsos. "Outras entradas" é o único indício de entrada que não é renda.
  - O birô traz a parcela das outras dívidas, não o saldo devedor: **o estoque de dívida é indisponível**.
  - 1.736 clientes têm menos de 12 meses de movimentação; 292 têm só 1.

### Indicadores (fluxo, estoque e valor contratado não são somados entre si)

| Indicador | Fórmula | Status |
|---|---|---|
| Renda estimada | min(declarada, identificada na conta) | estimado |
| Comprometimento da nova parcela | parcela Price 3% a.m. / renda estimada | estimado |
| Comprometimento total | (nova parcela + outras instituições) / renda estimada | estimado |
| Comprometimento antes do pedido | outras instituições / renda estimada | estimado |
| Endividamento (estoque da dívida nova) | valor / renda estimada (meses de renda) | estimado; outras dívidas indisponíveis |
| Renda disponível após a parcela | sobra mensal − nova parcela | estimado |
| Parcela sobre a sobra | nova parcela / (entradas − saídas) | estimado |

Antes do pedido, o comprometimento mediano é 8% da renda estimada (p90 35%). O comprometimento total com o valor
pedido tem mediana de 22%.

---

## D. Diagnóstico de risco

### D.1 As 10 perguntas da seção 5 (aprovados; PD vida KM [IC 95%]; `out/g04_financeiro.md`)

| # | Pergunta | Resposta com evidência |
|---|---|---|
| 1 | Mais endividado inadimple mais? | Pelo **fluxo anterior**, só a partir de 40% da renda: até 40% fica entre 14% e 16%; ≥ 40% vai a 28% [21–35] (n = 273). Pelo **estoque da dívida nova**: 1–2 meses de renda 12%; 3–4 meses 30%; 4–6 meses 55%. |
| 2 | Faixa de comprometimento em que o risco salta? | O corte mais nítido é **nova parcela ≥ 50% da sobra → 100%**; abaixo de 30% da sobra fica entre 8% e 10%. Sobre a renda, o "degrau dos 30%" vem quase todo dos reduzidos: não reduzidos com parcela de 30–36% da renda estimada ficam em ~10% (n = 40, pouco). Comprometimento total: < 30% 9–11%; 30–40% 19%; 40–50% 21%; 50–60% 29%; 60–80% 44%. |
| 3 | Renda alta com muitas parcelas? | Renda estimada ≥ 8 mil com outras dívidas de 20–40% da renda: 12% (n = 158), sem risco extra. Com ≥ 40%, só 22 casos (não estimado). Abaixo de 8 mil e ≥ 40%: **30,5%** (n = 257). |
| 4 | Renda variável? | CV ≥ 0,3: 22,5% (n = 756) contra ~14%. Autônomo 17,5% [14,9–20,1]; empresário 19,9% [15,9–23,9]; aposentado 10,7%. |
| 5 | Histórico de compras? | **Indisponível** (1 pedido por cliente). Proxies do birô: 6+ consultas em 90 dias 37% [30–44]; < 12 meses de birô 25% [15–34]. |
| 6 | Volume aumentando rápido? | Compras: indisponível. Gastos: **saídas subindo ≥ 50% nos 3 meses antes → 71% [63–79]** (n = 244); subindo 25–50% → 23%. |
| 7 | Saldo negativo? | Saldo mínimo < −R$ 2 mil: 32% [26–38]. Cheque especial em 2 meses do ano: 68% [56–81]; em 3+ meses: 100%. 2+ meses com saídas > entradas: 100%. |
| 8 | Valor da nova parcela? | Pesa pela proporção, não pelo valor: parcela de R$ 1.000–1.500 tem 30%, mas de R$ 1.500–2.500 tem 22%. O que manda é parcela ÷ sobra. |
| 9 | Renda declarada × identificada? | Conta < 60% da declarada: 65% [50–81] (n = 67). Desses, 304 de 351 (em toda a base) têm só 1–2 meses de conta; com renda visível na conta, ficam em 11,6%. Entre 60% e 110%: plano, 14–16%. |
| 10 | Combinação que melhor explica? | No modelo: **parcela ÷ sobra** (queda de AUC de 0,108 ao embaralhar), depois score (0,012), dias de cheque especial (0,010), prazo, tempo de conta, consultas e saldo mínimo. Com regras: saídas altas, parcela ≥ 50% da sobra, valor reduzido, pedido > 30% da renda, restrição, conta < 60% da declarada. |

Outros segmentos com intervalo de confiança:
- Restrição ativa (só no piloto): 40% [25–56] (n = 127).
- Prazo de 6 meses: 26% [21–31]; prazo de 36 meses: 9,7% [7,4–12,0].
- Score 500–599: 28% [18–39] (n = 183).
- Score < 500: 18% [6–30] (n = 94).

### D.2 Score × risco observado (`g04`, `g03`)

| Score | Aprovados | PD vida | IC 95% |
|---|---:|---:|---|
| < 500 | 94 | 18,1% | 6,2–29,9 |
| 500–599 | 183 | 28,4% | 17,9–39,0 |
| 600–649 | 423 | 15,6% | 11,3–19,8 |
| 650–699 | 738 | 14,3% | 11,2–17,5 |
| 700–799 | 2.266 | 15,2% | 13,3–17,2 |
| 800–899 | 1.714 | 15,8% | 13,6–17,9 |
| 900+ | 615 | 13,4% | 10,0–16,8 |

- **Score ≤ 600 com finanças boas, dentro do piloto:** 9,6% [2,8–16,5] (n = 149), contra 6,0% em score > 600 na mesma
  safra e 40,8% em score ≤ 600 sem finanças boas.
- **Score > 700 com comprometimento excessivo:** 46,1% [41,7–50,5] (n = 746), margem −0,21. Nos novos, a atual
  aprova 141 deles.

### D.3 Modelo preditivo (`out/g05*_*.md`)

**Desenho:**
- Rótulo: parou de pagar, com correção de censura. A parada cai de forma uniforme até 2/3 do prazo; os contratos
  abertos entram com rótulo suave por EM.
- Atributos: só os da data do pedido. Os que dependem do valor são recalculados para cada valor candidato.
- Variáveis demográficas fora.
- **Validação fora do tempo:** treino só com o que se sabia em 30/09/2025; teste nos aprovados de out/25–mar/26
  (n = 1.820, 62% do piloto, ou seja, já fora da população da política atual).

| Modelo (teste fora do tempo) | AUC parou até a 4ª | Brier | PD vida prevista | PD vida observada (KM) |
|---|---:|---:|---:|---:|
| Score sozinho | 0,691 | 0,067 | 19,7% | 19,8% [16,7–22,9] |
| Regressão logística + regras | **0,807** | **0,054** | 20,2% | 19,8% |
| Gradient boosting regularizado + regras | 0,796 | 0,055 | 18,5% | 19,8% |
| Regra da política atual (nega = 1) | 0,553 | — | — | — |

**Calibração.** Fora da dobra (5 dobras, 6.033 aprovados), o ensemble logística + boosting tem erro médio de 1,6 p.p.
por decil: decil 1 prevê 4,6% e observa 6,7%; decil 10 prevê 71,9% e observa 72,3%.

**Decisão no ponto de equilíbrio** (nega se PD vida > 17,5%), gradient boosting EM, teste fora do tempo:

| | nega | precisão | recall | F1 | PD dos aprovados | PD dos negados |
|---|---:|---:|---:|---:|---:|---:|
| Modelo | 16,2% | 0,276 | 0,587 | 0,375 | 8,8% | 59,4% |
| Regra atual | 23,5% | 0,108 | 0,333 | 0,163 | 17,2% | 28,5% |

**Duas lições metodológicas, que valem também para o modelo do time:**
1. **O hazard por parcela extrapola mal a vida inteira** quando o treino tem só 12 meses: previu 29% contra 19,8%
   observado. Por isso troquei pelo EM com a janela de 2/3 do prazo.
2. **O otimizador explora artefatos do modelo.** Uma flag de "valor reduzido" fazia P(em dia) saltar 8 p.p. com 0,1%
   de redução, e a política passava a reduzir 98% dos pedidos. Corrigi tirando os atributos que dependem do valor do
   modelo de atraso. Isso mostra que **o efeito da redução de valor não é identificável** nesta base.

---

## E. Comparativo de políticas

### E.1 Auditoria dos cenários A–H (`out/g06_auditoria.md`)

Aprovados e volume se reproduzem exatamente; o resultado, com diferença de até R$ 1 mil. Sem ids duplicados, e volume
coerente com o nº de pedidos. Resultado de vida inteira em R$ mil; entre parênteses, o ganho sobre A **no mesmo
avaliador**.

| | Prompt | Reproduzido | KM por célula | tool_risco | Conservador p/ redução (pior) |
|---|---|---|---|---|---|
| A (1.145; 8,86 mi) | 292 | 292 | 143 | 193 | 32–96 |
| B (1.550; 10,16 mi) | 817 (+526) | 817 (+526) | 663 (+520) | 692 (+498) | (+216) |
| C (1.209; 7,97 mi) | 645 (+354) | 645 (+354) | 527 (+384) | 546 (+353) | (+174) |
| D (1.208) | 645 (+354) | 645 (+354) | 526 (+383) | 546 (+353) | — |
| E (1.192) | 679 (+388) | 679 (+388) | 537 (+394) | 552 (+359) | — |
| F (1.191) | 679 (+388) | 679 (+388) | 536 (+393) | 552 (+359) | — |
| G (1.527; 10,22 mi) | 859 (+568) | 859 (+568) | 669 (+526) | 694 (+501) | (+227) |
| H (1.435; 9,59 mi) | 800 (+508) | 800 (+508) | 629 (+486) | 652 (+459) | (+219) |

**O que a auditoria encontrou:**
- **Premissas diferentes entre cenários.**
  - B, C e D são escolhidos pelo modelo "antigo" (3 classes, rótulo ingênuo) e medidos pelo corrigido.
  - E a H são escolhidos e medidos pelo corrigido: auto-avaliação. Para os aprovados de G ele prevê 5,9% de calote;
    os avaliadores independentes dão 8,1–8,5%.
  - Todos usam 23% fixo de pagadores com atraso. Nos grupos de risco, o atraso passa de 50%.
- **Cada modelo prefere a própria seleção.** G − B vale +42 mil pelo corrigido e −52 mil pelo antigo.
  As diferenças entre B, G e H estão dentro do viés do avaliador.
- **D ≈ C e F ≈ E:** os filtros "saídas ≥ 80%" e "renda real < 60%" pegam 171 novos, e 170 já eram negados
  (122 por restrição, 21 por 2+ meses negativos, 18 por score, 9 por risco).
- **35–40% do ganho vem de 61 pedidos:** os que A reduz para 30% da renda (calote previsto de 52–55%).
- **Tabela 19,4% / 7,7% / 8,0%.**
  - Vem do estimador de `src/cenarios.py` (90+ dias ponderado por parcelas vencidas), que subestima.
  - Os 278 são 100% do piloto. Dos 4.833, 208 não têm parcela vencida.
  - Recalculada (KM, 61 dias): **25,7% [17,1–34,2] / 9,0% [3,2–14,7] / 8,4% [7,4–9,4]**.
  - A queda vem de três filtros: parcela ≤ 20% da renda (−12 paradas), restrição (−7) e no máximo 1 mês negativo (−8).
  - Os mesmos filtros levam score > 600 de 15,1% para 8,4%: **o score baixo não "melhora"; os filtros tiram o mesmo
    tipo de risco dos dois grupos.**
  - Diferença ≤ 600 − > 600 depois dos filtros: +0,5 p.p. [−4,4; +6,7]. Compatível com "igual", mas não prova igualdade
    (13 paradas em 212).
- **Backtest honesto** (treino até 30/09/25; teste nos aprovados de out/25–mar/26, valor limitado ao histórico):
  - C ganha +125 mil [31; 239] sobre A.
  - **G ganha +61 mil [−94; +189], sem diferença estatística**: o modelo de 2025 previa 3,1% para os aprovados de G,
    e o observado foi 16,4%.

### E.2 Novos cenários e fronteira (`out/g07_otimizacao.md`, `out/g08_reducao.md`)

Testei uma grade de ~40 políticas: PD máxima de 8% a 25%; com ou sem redução de valor; com ou sem regras de corte;
score mínimo 0 ou 600. Mais variações do G. Cada uma foi medida por 3 avaliadores e em 2 hipóteses sobre a redução de
valor:
- **padrão:** reduzir o valor baixa o risco, como os modelos supõem;
- **conservadora:** reduzir só diminui a exposição, e a PD é a do valor pedido, como o histórico mostrou.

Ganho sobre A em R$ mil, no mesmo avaliador:

| Política | Aprov. | Volume | Reduz. | Ganho padrão | Ganho conservador | **Pior caso** |
|---|---:|---:|---:|---:|---:|---:|
| **G + negar reduções de quem pede acima da capacidade** | 1.421 | 9,48 mi | 372 | 454–481 | 515–553 | **454** |
| G + negar só reduções de pedidos > 30% da renda | 1.429 | 9,54 mi | 380 | 459–485 | 501–539 | 459 |
| Modelo próprio, PD ≤ 16%, sem reduzir valor | 1.441 | 9,72 mi | 0 | 428–471 | 539–568 | 428 |
| Modelo próprio, PD ≤ 20%, com redução | 1.507 | 9,73 mi | 1.223 | 436–483 | 519–541 | 436 |
| G (time) | 1.527 | 10,22 mi | 478 | 501–526 | 227–239 | 227 |
| H (time) | 1.435 | 9,59 mi | 456 | 459–486 | 219–230 | 219 |
| B (time) | 1.550 | 10,16 mi | 575 | 498–520 | 216–225 | 216 |
| G, reduzidos recebem o valor pedido | 1.527 | 11,98 mi | 0 | −425 a −362 | −314 a −264 | −425 |

**Fronteira de eficiência** (modelo + regras, com redução; ganho KM / tool_risco):

| PD máx. | Aprov. | Volume | Ganho |
|---|---:|---:|---|
| 8% | 979 | 6,2 mi | +264 / +271 |
| 10% | 1.173 | 7,6 mi | +341 / +361 |
| 12% | 1.272 | 8,2 mi | +376 / +397 |
| 14% | 1.314 | 8,5 mi | +392 / +413 |
| 16–25% | 1.327 | 8,6 mi | +396 / +417 |

Acima de ~16% a fronteira fica plana: quase nenhum pedido tem PD entre 16% e 25% (a distribuição é bimodal).
O ponto de equilíbrio de 17,5% não é sensível.

**Saídas altas nos 2.000 novos:** 263 pedidos com algum sinal (saídas ≥ 80%, déficit nos 3 meses, 2+ meses de
déficit, saídas subindo ≥ 50% ou parcela pedida ≥ 50% da sobra).

| Política | Aprova, dos 263 |
|---|---:|
| Atual (A) | 98 |
| G | 116 (100 deles com parcela pedida ≥ 50% da sobra, salvos por redução) |
| Recomendada | 16 (só saídas subindo, e com o valor pedido inteiro) |
| Modelo próprio sem redução | 1 |

---

## F. Recomendações

**1. Política para os 2.000 novos:** G do time + uma regra. Se a parcela **pedida** passa de 30% da renda declarada
ou de 50% da sobra mensal, **nega**; não reduz. Resultado:
- 1.421 aprovados e R$ 9,48 mi (contra 1.145 e R$ 8,86 mi da atual);
- ganho de R$ 454–553 mil;
- PD do volume de 8,1–8,4% (KM por célula e tool_risco) contra 14,4–15,4% da atual.

CSV: `analysis/scripts-guilherme/out/g08_decisoes_recomendadas.csv` (gerado por `g08_reducao.py`, não versionado por conter ids de pedido; validado com
`src/validar_csv.py`). Para virar a entrega oficial, a regra precisa entrar no `src/politica.py` do time.

**2. Critérios de corte** (negar; evidência de PD ≥ 60% com n ≥ 75):
- nova parcela ≥ 50% da sobra (entradas − saídas), ou sobra ≤ 0;
- saídas > entradas em algum dos 3 meses antes, ou em 2+ meses do ano; saídas ≥ 80% das entradas;
- cheque especial em 2+ meses do ano;
- pedido acima da capacidade (parcela pedida > 30% da renda declarada): **negar, não reduzir**.

**3. Limites de comprometimento:**
- nova parcela < 30% da sobra (PD 8–10%);
- comprometimento total (nova + outras) < 30% da renda estimada (PD 9–11%);
- de 30% a 50%: aprovar só com PD do modelo < 17,5%.

**4. Revisão manual** (margem ainda positiva, mas risco acima da média):
- saídas subindo 10–50% nos 3 meses antes;
- pico de saída ≥ 2× a mediana;
- 4–5 consultas em 90 dias;
- conta com ≤ 3 meses de movimentação: a renda declarada não aparece na conta;
- empresário com parcela > 20% da renda.

**5. Segmentos:**
- **Para testar aprovação:** score ≤ 600 com finanças limpas. São 235 nos novos, que a atual nega todos; PD 9,6%
  [2,8–16,5] no piloto. O limite superior do IC chega perto do equilíbrio: teste controlado, com teto de valor.
- **Para aumentar limite:** bom histórico com baixa exposição, 6,1% [4,3–7,8] (n = 1.173); aposentado com finanças
  limpas, 5,6% (n = 363).
- **Para limite menor ou negar:**
  - score > 700 com comprometimento excessivo: 46% (a atual aprova 141 nos novos);
  - restrição ativa: 40% [25–56], com metade dos pagadores atrasando;
  - prazo de 6 meses: 26%.

**6. Variáveis proibidas na política:** gênero, estado civil, CEP/região e idade. Não trazem ganho preditivo
(p = 0,78). Trazem risco legal: LGPD art. 6º IX (não discriminação) e art. 20 (revisão de decisão automatizada).
O CEP funciona como proxy.

**7. Coleta de dados:**
- extrato por transação, para separar transferências, estornos e empréstimos;
- saldo devedor das outras dívidas, e não só a parcela;
- histórico de recompra;
- motivo do pedido;
- registrar o valor pedido e o aprovado em toda redução;
- sobretudo, **variar a redução de valor de forma aleatória num grupo pequeno**. É a única forma de medir se reduzir
  baixa o risco.

---

## G. Plano de implementação

**Usar já** (dados existentes, sem modelo):
- parcela ÷ sobra;
- saídas ÷ entradas e déficit nos 3 meses;
- meses com cheque especial;
- parcela pedida ÷ renda declarada;
- restrição.

**Ajustes na base e no código do time:**
- uma definição só de calote: 61 dias, KM;
- probabilidade de atraso por pedido no lugar dos 23% fixos;
- calibrar o modelo corrigido contra KM antes de usar o corte de 17,5%;
- tirar D e F da comparação.

**Modelos a desenvolver:**
- PD de vida inteira por EM com censura (`g05c`, AUC 0,81 fora do tempo);
- modelo de atraso;
- quando houver dados, o efeito causal da redução de valor.

**Monitoramento:**
- safra mensal: parada até a 3ª e a 6ª parcela, comparada com o previsto por decil;
- PD vida por KM a cada trimestre;
- alerta quando a parada de uma safra passar o previsto + 2 desvios;
- estabilidade (PSI) de parcela ÷ sobra, score e vínculo.

**Teste antes de mudar a política oficial:**
- *champion-challenger*: 80% pela política oficial e 20% pela nova, em sorteio;
- dentro do desafiante, braços aleatórios para "reduzir × negar" e para "score ≤ 600 limpo aprova × nega";
- 6 meses de safra antes de decidir, com corte prévio de parada até a 4ª parcela (o observável mais cedo, AUC 0,8).

---

## Limitações (o que este trabalho não sustenta)

- **Viés de seleção:** só aprovados têm desfecho. Score ≤ 600, restrição e renda < 2 mil vêm só do piloto
  (out/25–mar/26, 1.126 contratos).
- **Censura:** a janela de parada (2/3 do prazo) foi vista em 6, 12 e 18 meses. Para 24 e 36 meses, é extrapolada.
- **Avaliadores:** os três (modelo, KM por célula e tool_risco) foram construídos sobre a mesma base histórica. O
  desfecho real dos 2.000 novos vem das regras da organização e pode diferir. Por isso a escolha é pelo pior caso, e
  não pelo melhor.
- **Rentabilidade (seção 8):** o resultado segue a regra do desafio (+15% / +5% / −60%). Faltam custo de captação,
  custo operacional, recuperação pós-calote, impostos e a receita real de juros (Price a 3% a.m.).
  Com o que há:
  - **por R$ concedido:** atual 0,016–0,022; G 0,066–0,068; recomendada 0,066–0,068 no avaliador padrão e
    **0,062–0,064 no conservador** (G cai para 0,027–0,032);
  - **por cliente aprovado:** atual R$ 125–169; recomendada R$ 439–455.
