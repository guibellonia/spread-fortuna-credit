# ONDA 1 — Fortuna Crédito · time Spread · 11/11/2026

Refazer tudo: `cd analise && ../.venv/bin/python base.py && ../.venv/bin/python onda1.py && ../.venv/bin/python onda1_frases.py`
(base.py monta 1 linha por pedido com features só de antes do pedido + alvos tirados de `parcelas`; cache `_base_*.pkl`.)

## SÍNTESE (topo)

**Alvo usado:** `nao_paga` = alguma parcela vencida com **90+ dias de atraso** até 30/09/2026 (bate 582/582 com `situacao_final='inadimplente'`). Medido só na **base madura = aprovados com pedido até 30/09/2025** (≥12 parcelas vencidas), **n = 2.844** (todos política atual; o piloto só começa em out/2025).
Na base madura: **em dia 66,4% (1.888) · atraso <90d 20,0% (568) · não paga 13,6% (388)**.

**Por que esse alvo e esse corte:** o calote aparece cedo — a 1ª parcela que chega a 90 dias é, em mediana, a 2ª (prazo 6), 4ª (12), 5ª (18), 6ª (24 e 36); máximo 20ª (prazo 36). Safras de out/24 a jul/25 ficam em 12–18% de calote; de jan/26 em diante caem para 7% → 0% só porque ainda não deu tempo (censura). Com ≥12 meses de observação quase todo calote já apareceu (resta subestimar um pouco prazo 24/36).

**Padrões, do mais forte ao mais fraco** (taxa = não paga entre aprovados maduros; média = 13,6%; "afeta" = clientes da base histórica inteira, 10.000, e dos 2.000 novos):

| # | Frase no formato do manual | Grupo | Média | n maduros | Afeta hist / novos | Confiança |
|---|---|---|---|---|---|---|
| 1 | Clientes com **saídas maiores que as entradas em pelo menos 1 dos 12 meses** antes do pedido têm inadimplência de **91%**, contra 14% da média. Afeta **490** clientes. | 91,0% | 13,6% | 67 | 490 / 97 | **regra plantada provável** (degrau 15%→91%, o resto dos 9% vira atraso: 100% têm algum atraso) |
| 2 | Clientes com **mais de 6 dias de cheque especial nos 3 meses** antes do pedido têm inadimplência de **76%**, contra 14%. Afeta **613**. | 76,5% | 13,6% | 85 | 613 / 118 | plantada provável — **mesmo grupo do #1** (61 de 67 do #1 também estão aqui) |
| 3 | Clientes com **saldo mínimo abaixo de −R$300 nos 3 meses** antes do pedido têm inadimplência de **75%**, contra 14%. Afeta **594**. | 74,7% | 13,6% | 87 | 594 / 115 | plantada provável — sobrepõe #1/#2 (“estresse de conta”) |
| 4 | Clientes com **parcela pedida acima de 30% das entradas médias da conta** têm inadimplência de **55%**, contra 14%. Afeta **811**. | 54,9% | 13,6% | 206 | 811 / 162 | **regra plantada provável** (efeito do VALOR; independente do #1: fora do estresse 54% vs 8,5%) |
| 5 | Clientes com **valor pedido acima de 4× a renda declarada** têm inadimplência de **61%**, contra 14%. Afeta **565**. | 60,6% | 13,6% | 142 | 565 / 116 | mesma família do #4 (comprometimento) |
| 6 | Clientes com **parcela pedida acima de 25% da renda declarada** têm inadimplência de **50%**, contra 14%. Afeta **835**. | 49,8% | 13,6% | 229 | 835 / 160 | mesma família do #4; curva: ≤24% → 6–10%; 24–29% → ~27%; exatamente 30% (os reduzidos ao teto) → 54% |
| 7 | Clientes com **saldo médio abaixo de R$7.500 nos 3 meses** antes do pedido têm inadimplência de **51%**, contra 14%. Afeta **911**. | 50,8% | 13,6% | 118 | 911 / 195 | **carona** do #1–#3: fora do estresse cai para 17% (n=47) vs 11,5% |
| 8 | Clientes com **mais de 6 consultas ao CPF em 90 dias** têm inadimplência de **43%**, contra 14%. Afeta **439**. | 43,4% | 13,6% | 76 | 439 / ⚪ (birô novo via API) | **carona**: fora do estresse cai para 16% (n=49) vs 11,6% — não usar sozinho |
| 9 | Clientes com **parcela pedida + dívidas em outras instituições acima de 45% da renda declarada** têm inadimplência de **38%**, contra 14%. Afeta **1.027**. | 38,2% | 13,6% | 262 | 1.027 / ⚪ | tendência real; no resíduo (sem #1 e #4) ainda 19% vs 7,7% |
| 10 | Clientes com **entradas da conta oscilando muito (coef. de variação mensal > 0,35)** têm inadimplência de **23%**, contra 14%. Afeta **1.344**. | 23,0% | 13,6% | 304 | 1.344 / 269 | tendência real (no resíduo: 16% vs 7%) |
| 11 | Clientes com **prazo de 6 meses** têm inadimplência de **24%**, contra 14%. Afeta **505**. | 23,9% | 13,6% | 159 | 505 / 101 | **pode ser artefato**: prazo curto = parcela maior, e prazo 36 ainda censurado; no resíduo 11% vs 8% |
| 12 | Clientes **aposentados** têm inadimplência de **7%**, contra 14%. Afeta **1.016**. | 6,9% | 13,6% | 320 | 1.016 / 196 | tendência real (protetor) |

Atributos sensíveis medidos (decisão de uso é do time): gênero sem efeito (13,4% × 13,6%); estado civil "viúvo" 2,5% (n=79, pequeno); 1º dígito do CEP "1" 19,7% (n=127) — fraco, provável ruído. Profissão: de 5,6% (Gerente comercial, n=36) a 26,4% (Auxiliar de produção, n=53) — grupos pequenos, não testado fora da amostra ainda.

**Leitura em 3 frases:** (1) existe um segmento de **"estresse de conta"** (saídas > entradas, cheque especial, saldo mínimo negativo nos 3 meses antes do pedido) com ~600 clientes no histórico e **113 nos novos**, que não paga em 77–91% dos casos — a política atual aprova vários (156 aprovados no histórico) porque olha só score/renda/restrições. (2) O **comprometimento da parcela** decide o resto: até ~24% da renda o calote é 6–10%; acima de 25% salta para ~50%; os que a política atual **reduziu ao teto de 30%** da renda caíram justamente na faixa ruim (54%). (3) Fora desses dois blocos sobra uma base de 2.538 aprovados maduros com **8,3%** de calote — abaixo do ponto de equilíbrio (~20%).

**Proposta de política (esboço, a simular na onda 2):** Filtro: negar estresse de conta (#1 ou #2+#3). → Risco: score/restrições como hoje (a medir se dá para afrouxar com o piloto). → Valor: limitar parcela a ~20–24% da renda declarada **e** ≤ ~25% das entradas médias da conta (não reduzir ao teto de 30%). Resultado financeiro simulado: ⚪ NÃO-MEDIDO nesta onda (onda 2).

## Detalhe

### 1. Alvo e maturação
- Classes por parcela batem 100% com `situacao_final`: em_dia = quitado_em_dia + em_dia; atraso = em_atraso + quitado_com_atraso; não paga = inadimplente.
- Calote por safra (aprovados): out/24 15,7% · nov 13,2% · dez 16,6% · jan/25 18,4% · fev 12,7% · mar 15,0% · abr 15,6% · mai 13,0% · jun 12,0% · jul 11,6% · ago 10,1% · set 9,1% · out/25 12,4% · nov 14,3% · dez 12,1% · jan/26 7,0% · fev 7,3% · mar 7,9% · abr 3,8% · mai–set 0%. A queda depois de jul/25 é censura, não melhora.
- Piloto (out/25–mar/26, 1.263 pedidos, 1.126 aprovados): calote bruto 11,4% vs atual 9,3% no total, mas o piloto ainda está imaturo (6–11 meses) — comparação justa fica para a onda 2 com janela igual.
- 347 aprovados reduzidos: a regra é **parcela = 30% da renda declarada** (83,6% batem com teto de 30% arredondado a R$100; 290 atual); os 57 do piloto parecem usar teto de 35% (a confirmar).

### 2. Varredura de uma variável
Tabela completa: `analise/onda1_varredura.csv` (alvo não paga) e `analise/onda1_varredura_qualquer_atraso.csv`; categóricas em `analise/onda1_categ.csv`. Degraus secos (taxa logo abaixo → logo acima do corte, 5% dos dados de cada lado):
- `meses_saida_maior > 0`: 14,8% → 91,0%
- `saida_ent` (saídas/entradas 12m) > 0,97: 18% → 90%
- `cheque_3m > 6`: 17% → 77% · `saldo_min_3m < −315` (≈ −300): 16% → 76% · `cheque_12m > 34` (≈35): 11% → 78%
- `valor_renda > 4`: 17% → 61% · `parc_ent > 0,30`: 13% → 49% · `parc_renda > 0,25–0,27`: 16–22% → 50–56%
- Score (>600 já filtrado): sem degrau dentro dos aprovados (16% ≤650 vs 13% >650). Renda: 20% ≤2.500 vs 13%.

### O que não medi (⚪)
- Birô dos 2.000 novos (vem da API): contagens de #8 e #9 nos novos ficam ⚪ — onde buscar: `cache-biro/` do outro braço.
- Interações, confirmação temporal, piloto × atual, simulação financeira, profissão fora da amostra: onda 2.
