# ONDA 2 — Fortuna Crédito · time Spread · 11/11/2026

Refazer: `cd analise && ../.venv/bin/python base.py && ../.venv/bin/python onda2_arvores.py && ../.venv/bin/python onda2_politica.py && ../.venv/bin/python onda2_frases.py`
Alvo: igual à onda 1 (não paga = parcela com 90+ dias até 30/09/2026), medido nos **2.844 aprovados maduros** (pedido ≤ 30/09/2025, todos política atual). Média: **13,6%** não paga · 20,0% atraso · 66,4% em dia.
Conferências: **por tempo** = acho/meço em out/24–mar/25 (n=1.425) e confiro em abr–set/25 (n=1.419); **piloto × atual** = janela out/25–mar/26 com alvo de janela igual `cal3` (90+ dias já na 1ª–3ª parcela; nos maduros calote final ≈ cal3 × 2,92).

## SÍNTESE (topo)

### Padrões, do mais forte ao mais fraco

| # | Frase no formato do manual | Grupo × média | Antigos → novos maduros | Piloto/janela (cal3 grupo × resto) | Afeta hist / novos | Confiança |
|---|---|---|---|---|---|---|
| 1 | Clientes com **saídas maiores que as entradas em algum dos 3 meses antes do pedido E cheque especial nos 2 meses antes** têm inadimplência de **91%**, contra 14% da média. Afeta **485** clientes. | 91,0% × 13,6% (n=67) | 96,9% (32) → 85,7% (35) | 31,5% × 5,1% (54) | 485 / **97** | **regra plantada provável**. Forma mês a mês: no 3º mês antes do pedido as saídas chegam a ~7× as entradas (mediana), o saldo zera, e nos 2 meses seguintes 84–91% ficam no cheque especial; nos outros clientes saídas/entradas = 0,32 em todos os meses. Os 9% que não dão calote atrasam (100% com algum atraso). |
| 2 | Clientes com **parcela aprovada acima de 28% da renda real** (a menor entre renda declarada e entradas médias da conta nos 12 meses) têm inadimplência de **50%**, contra 14% da média. Afeta **820** clientes. | 50,2% × 13,6% (n=221, sem #1) | 54,1% (109) → 46,4% (112) | 22,8% × 4,3% (158) | 820 / **159** (pedido) | **regra plantada provável** (efeito do VALOR). Curva sem estresse: ≤28% → 4–17% (≈8%); 28–30% → 27%; 30–32% → 50%; 35–40% → 75%; >40% → 100% (n=6). Entradas da conta explicam melhor que renda declarada (log-verossimilhança −881,7 × −895,0). |
| 3 | Clientes que tiveram o **pedido reduzido pela política ao teto de 30% da renda declarada** têm inadimplência de **55%**, contra 14% da média. Afeta **281** clientes. | 54,7% × 13,6% (n=172) | 58,3% → 51,1% | 19,6% × 5,5% (51) | 281 (hist) | **consequência do #2**: a regra atual reduz a parcela para 30% da renda declarada, que fica acima de 28% da renda real — reduz pouco. O piloto reduz a 35% (57 casos). |
| 4 | Clientes com **cheque especial nos 2 meses antes do pedido, sem a saída grande** têm inadimplência de **30%**, contra 14% da média. Afeta **144** clientes. | 30,4% × 13,6% (n=23) | 22,2% (9) → 35,7% (14) | 17,6% × 5,8% (17) | 144 / **29** | tendência real, grupo pequeno (acima do ponto de equilíbrio de ~20%: negar) |
| 5 | Clientes com **parcela + dívidas em outras instituições acima de 42% das entradas médias** têm inadimplência de **17,5%**, contra 14% da média (7,2% no resto dos limpos). Afeta **517** clientes. | 17,5% (n=257, já limpos) | 21,4% → 12,8% | 6,1% × 2,8% dos limpos (147) | 517 / ⚪ (birô) | tendência real ~2×, mas **perto do equilíbrio**: ganho do grupo +R$25 mil (−26 mil antigos, +52 mil novos) → não negar; candidato a reduzir valor (⚪ não simulado) |
| 6 | Clientes com **entradas da conta oscilando (coeficiente de variação mensal > 0,35)** têm inadimplência de **17%**, contra 14% da média (7,2% no resto dos limpos). Afeta **1.159** clientes. | 16,7% (n=269) | 21,8% → 12,4% | 5,7% × 2,8% dos limpos | 1.159 / **238** | tendência real (autônomos/empresários: CV mediano 0,19/0,25 contra 0,07); ganho do grupo +R$5 mil → neutro |
| 7 | Clientes com **histórico no bureau de até 30 meses** têm inadimplência de **13%**, contra 14% da média (7,6% no resto dos limpos). Afeta **2.490**. | 12,7% (n=316) | 15,4% → 9,5% | 3,4% × 6,5% (não confirma) | 2.490 / ⚪ | **pode ser ruído** (não se confirma na janela do piloto) |
| 8 | Clientes com **mais de 70 anos** têm inadimplência de **1,6%**, contra 14% da média. Afeta **346**. | 1,6% (n=122) | 0,0% → 3,1% | 1,8% × 6,0% (57) | 346 / **69** | tendência real (protetor) — **idade é atributo sensível** |
| 9 | Clientes **aposentados** têm inadimplência de **4,4%**, contra 14% da média. Afeta **868**. | 4,4% (n=294) | 4,2% → 4,6% | 1,4% × 6,3% (147) | 868 / **162** | tendência real (protetor), estável nas 3 partes |
| 10 | Clientes com **score entre 450 e 600** (só o piloto aprovou) têm inadimplência estimada de **~12%** (cal3 4,1% × 2,92), contra ~9% dos score > 600 (cal3 3,0%). Afeta **2.382** clientes do histórico. | ⚪ calote final; cal3 4,1% × 3,0% (n=243) | — | piloto | 2.382 / ⚪ | **anti-padrão importante**: score abaixo de 600 **não** separa calote como a política atual supõe (piloto, score ≤500 limpo: cal3 1,2%, n=82) |

**Sensíveis / estranhos (item 7) — sem efeito que se sustente:** gênero 9,7%/7,5% (fem) × 10,0%/5,5% (masc) em antigos/novos; estado civil sem diferença estável (viúvo 2,9%/0%, n=34/37, pequeno); 1º dígito do CEP troca de ordem entre as metades (ex.: "1": 7,4% → 17,0%; "8": 12,0% → 3,1%) → ruído; profissão idem (Eletricista 28% → 0%; Técnico em informática 14,8% → 4,6%) → ruído; dia do mês 6,2–9,5% sem padrão; ano de abertura da conta sem padrão (2016: 27%, n=11). Idade > 70 (protetor) é o único sensível com efeito estável.

### Onde a política atual erra (item 6)
- **(a) Aprova e não paga:** dos 388 calotes maduros, **17,5% têm o estresse de conta (#1/#4)** e **29,9% têm parcela > 28% da renda real (#2)**; **46,1% têm um dos dois**. Os 2.533 aprovados sem nenhum dos dois têm 8,3% de calote — os outros 53,9% dos calotes ficam espalhados (não achei regra forte para eles; os #5–#7 só dobram 7% para 13–17%).
- **(b) Nega e pagaria:** no piloto, os aprovados que a regra atual **negaria** e estão "limpos" (sem #1 e parcela ≤ 28% da renda real), n=349: cal3 4,0% → **calote final estimado 11,7%**, contra 7,6% dos aprovados da atual na mesma janela. Por motivo: score ≤ 600 (n=222) ~11,8%; restrição = 1 (n=87) ~13,4%; renda ≤ 2.000 (n=40) ~7,3%. Todos **abaixo de 20%** → dariam lucro. Já os do piloto com estresse ou parcela alta (n=125): ~91% estimado.

### Proposta de política (Filtro → Risco → Valor)
1. **Filtro (negar):** estresse de conta = saídas > entradas em algum dos 3 meses antes do pedido **ou** cheque especial em algum dos 2 meses antes. Restrições ativas ≥ 2: negar (⚪ sem dado — nunca foram aprovadas). Renda declarada < R$1.500: negar (⚪ piloto não aprovou abaixo de 1.550).
2. **Risco:** **não usar score > 600 como corte**; aceitar score ≥ 450 e até 1 restrição (evidência: piloto, item 6b). Abaixo de 450: ⚪ sem dado → negar.
3. **Valor:** renda real = menor entre renda declarada e entradas médias dos 12 meses. Aprovar o pedido inteiro se parcela ≤ 28% da renda real; se passar, **reduzir até parcela = 25% da renda real** (ou negar, se o time preferir o lado seguro).

**Resultado financeiro simulado no histórico maduro** (2.844 aprovados pela atual; só se pode negar/reduzir quem foi aprovado — quem a atual negou não tem desfecho; em andamento: só maduros; `em_atraso` contado como atraso = +5%):

| Política | Aprovados | Volume | Ganho | Calote | Δ vs atual |
|---|---|---|---|---|---|
| Atual (real) | 2.844 | R$22,74 mi | **R$251 mil** | 13,6% | — |
| − estresse de conta | 2.754 | R$22,05 mi | R$583 mil | 11,6% | +R$332 mil |
| − parcela > 28% renda real | 2.618 | R$19,62 mi | R$1,021 mi | 10,4% | +R$770 mil |
| **− estresse − parcela > 28% renda real (negar)** | 2.533 | R$19,03 mi | **R$1,299 mi** | 8,3% | **+R$1,048 mi** |
| idem, mas **reduzir** a 25% em vez de negar (221 casos) | 2.754 | — | R$1,425 mi | — | +R$1,174 mi (⚪ hipótese: risco do reduzido = faixa 20–28%, calote 10,3%) |

Varredura do teto (negando acima): 20% → +R$933 mil · 24% → +R$1,020 mi · 26% → +R$1,028 mi · **28% → +R$1,048 mi** · 30% → +R$1,022 mi · 32% → +R$847 mil. Confere nas duas metades: antigos −R$93 mil → +R$510 mil (Δ +R$603 mil); novos +R$344 mil → +R$788 mil (Δ +R$444 mil).
O ganho de **aprovar score 450–600 e restrição = 1** (item 6b) **não entra** nessa conta (sem desfecho maduro): ⚪ estimado positivo (~+3% do valor por real emprestado com 12% de calote e 30% de atraso).

**Nos 2.000 novos:** estresse de conta **126** (97 com saída grande + cheque; 29 só cheque); parcela pedida > 28% da renda real (fora do estresse) **159** (108 acima de 40%); limpos com parcela ≤ 28%: **1.715**. Arquivo por pedido: `analise/novos_flags.csv`. Score/restrições dos novos vêm da API: ⚪ aqui.

## Detalhe

### 4. Árvores rasas (treino out/24–mar/25, conferência abr–set/25) — `onda2_arvores.py`
Profundidade 2, folha ≥ 50: 1º corte **parcela aprovada/entradas ≤ 0,285**; depois saldo mínimo 3m ≤ R$2.866 (62% → 53% nos novos; é o grupo #1: 82 dos 114 maduros dessa folha têm estresse, e 62 desses 82 não pagam; os 32 sem estresse: 3 calotes) e saídas/entradas ≤ 0,315. Folhas: 10%→6,6% (1.265/1.252) · 62%→53% · 40%→41% · 76%→61%. Profundidade 3–4 só acrescenta coeficiente de variação das entradas e comprometimento com outras dívidas (22%→13%, 29%→12%: não se sustenta). Busca de pares (`onda2_segmentos.csv`): todos os pares de alto risco com sinergia são variações do #1 (saldo baixo + saídas/entradas alta + cheque); pares de baixo risco: idade > 69 + aposentado (1,5% → 9,1%), parcela < 5% das entradas (2,7% → 2,9%).

### 5. Efeito do valor — `onda2_politica.py`
- Entre clientes sem estresse, a taxa fica plana (~8%) até parcela = 28% da renda real e salta depois (tabela no item 2). O ponto ótimo do teto é 28% (varredura acima).
- **Os 347 reduzidos:** atual reduz a parcela a exatamente **30% da renda declarada** (275 de 275 com parcela calculável; desvio 0,0); piloto a **35%** (57). Eles não pagam em 54,7% (sem estresse) — reduzir ao teto antigo não protege, porque a renda real costuma ser menor que a declarada. Na faixa 28–30% das entradas: 40% (25); 30–35%: 47% (95); > 35%: 79% (48).
- O tamanho do pedido também carrega sinal além da parcela aprovada (modelo com parcela pedida + aprovada melhora log-verossimilhança de −881,7 para −872,1): quem pede muito acima do que pode é mais arriscado mesmo reduzido. Por isso "reduzir a 25%" é hipótese ⚪, "negar acima de 28%" é o que está medido.

### O que não medi (⚪)
- Restrições ≥ 2, score < 450, renda < R$1.500: nenhuma aprovação no histórico → sem desfecho. Onde buscar: não há na base; decisão de risco do time.
- Desfecho de quem é reduzido a ≤ 25% da renda real: nunca aconteceu na base.
- Classe "atraso" (vale +5%): não achei regra própria; fica ~15–25% em quase todo segmento.
- Contagem dos novos para padrões que usam birô (#5, #7, #10): depende da API (`cache-biro/`).
