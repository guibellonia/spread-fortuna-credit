# Censura, inadimplência projetada e ponto de equilíbrio · agregado

Complementa `analise-banco.md` (Juliano) e `analise-enio.md` (Enio). Traz o que muda nas contas quando se usa
**todos os 6.033 aprovados** em vez de só os contratos maduros. Scripts: `analysis/build_dataset.py` e
`analysis/patterns.py` (tabela completa em `analysis/out/patterns.csv` e em `padroes-agregado.md`).

## 1. Três fatos da base que resolvem a censura

Medidos nas 135.792 parcelas da tabela `parcelas`:

1. **Parar de pagar é definitivo.** Dos 582 inadimplentes, nenhum pagou parcela alguma depois da primeira que
   deixou de pagar.
2. **Parcela paga nunca atrasou mais de 60 dias.** O atraso das parcelas pagas vai de 0 a 60 (95% até 28 dias).
   Logo, parcela vencida há **61 dias ou mais** sem pagamento já é calote, sem esperar os 90.
3. **A parada acontece de forma espalhada até ~2/3 do prazo, e nunca depois.**

| Prazo | Parcela máxima em que alguém parou | Fração do prazo |
|---|---|---|
| 6 | 4ª | 0,67 |
| 12 | 8ª | 0,67 |
| 18 | 10ª a 12ª | 0,56–0,67 |
| 24 | 15ª (ainda censurado) | — |
| 36 | 20ª (ainda censurado) | — |

Nos contratos de 6 e 12 meses já encerrados, a parada se distribui quase igual entre a 1ª e a última parcela
dessa janela (12 meses: 4, 18, 13, 14, 14, 13, 15 e 2 casos da 1ª à 8ª).

## 2. Inadimplência projetada

Se a parada cai em qualquer parcela da janela (até 2/3 do prazo) com a mesma chance, um contrato observado em uma
fração `w` da janela teria mostrado, em média, `p × w` paradas. Então:

```
inadimplência projetada = paradas observadas / soma de w
w = min(parcelas já decididas, janela) / janela      janela = 2/3 do prazo, arredondado para cima
```

Contrato maduro pesa 1; contrato aberto há 2 meses pesa pouco. Nenhum contrato é descartado.

| Recorte | Ingênua (parou / total) | Projetada |
|---|---|---|
| Todos os aprovados (6.033) | 10,4% | **15,9%** |
| Política atual (4.907) | — | **14,7%** |
| Piloto (1.126) | — | **21,6%** |
| Prazo 6 | 22,7% | 25,6% |
| Prazo 12 | 14,3% | 17,4% |
| Prazo 18 | 9,8% | 13,5% |
| Prazo 24 | 9,8% | 16,1% |
| Prazo 36 | 5,8% | **12,5%** |

**Consequências para o que o time já escreveu:**
- O corte em 12 meses (Enio, média 13,6%) ainda **subestima prazos longos**. Num contrato de 36 meses, o calote
  pode aparecer até a ~24ª parcela.
- "Prazo de 36 meses = 7%" (Juliano) é quase todo efeito da censura: corrigido, fica em 12,5%, pouco abaixo da
  média.
- O multiplicador único "cal3 × 2,92" usado para estimar o piloto não vale para todos os prazos. As parcelas 1 a 3
  cobrem 3/4 da janela no prazo 6 (fator ~1,3) e 3/24 no prazo 36 (fator ~8). Com prazos misturados, um fator único
  erra para cima ou para baixo conforme o grupo.
- **Hipótese em aberto:** a janela de 2/3 foi vista nos prazos 6, 12 e 18. Nos prazos 24 e 36 ela é extrapolada,
  porque nenhum contrato desses chegou ao fim.

## 3. Ponto de equilíbrio é ~17,5%, não 20%

Por real aprovado: `+0,15 × em dia + 0,05 × com atraso − 0,60 × não paga`.

Os 20% citados nos documentos supõem que todo bom pagador paga em dia. Mas **~23% dos que pagam atrasam alguma
parcela** (22,6% dos contratos encerrados sem calote; 22 a 28% nos abertos com 4+ parcelas). Com `r` = fração de
pagadores com atraso:

```
aprovar compensa se  inadimplência < (0,15 − 0,10·r) / (0,75 − 0,10·r)
r = 0      → 20,0%
r = 0,23   → 17,5%
r = 1      →  7,7%
```

Leituras:
- A política atual roda a **14,7%** projetado: dá lucro, mas está perto do limite.
- O piloto, no geral, roda a **21,6%**: deu prejuízo como um todo. O ganho dele só existe nos subgrupos limpos.
- Grupos entre 15% e 20% (por exemplo, "parcela + outras dívidas > 42% das entradas", 17,5%) estão **no empate**,
  não abaixo dele.
- O atraso também piora nos grupos de risco: 1 restrição tem 52% de pagadores com atraso; saídas ≥ entradas, 77
  a 81%. Isso baixa ainda mais o ponto de equilíbrio deles.

## 4. Divergência a resolver antes de afrouxar score e restrição

O Enio estima calote de ~12 a 13% para score entre 450 e 600 e para 1 restrição, já sem os grupos de conta
apertada e parcela alta, usando o cal3 × 2,92. Pela inadimplência projetada, **sem limpar** esses grupos:

| Grupo (aprovados) | Clientes | Paradas | Projetada | Pagadores com atraso |
|---|---|---|---|---|
| Score < 500 | 94 | 11 | 20,6% | 30% |
| Score 500–599 | 183 | 30 | 26,6% | 29% |
| Score 600–699 | 1.161 | 120 | 15,5% | 26% |
| Score 700+ | 4.595 | 465 | 15,5% | 24% |
| 0 restrição | 5.906 | 597 | 15,4% | 24% |
| **1 restrição** | **127** | **29** | **39,4%** | **52%** |

As duas contas medem coisas diferentes (com e sem limpeza), mas a distância é grande demais para ser só isso,
principalmente em 1 restrição. Aprovar quem a atual nega é a única direção que pode deixar o ganho negativo
(`para-discussao.md`). **Proposta:** medir score 450–600 e 1 restrição já limpos, com a inadimplência projetada,
antes de colocar na política. Se ficarem acima de ~17,5%, manter score > 600 e zero restrição.

## 5. O que confirma o que o time já tem

| Padrão do time | Aqui (projetada) |
|---|---|
| Conta apertada (saídas ≥ 80% das entradas) | 106 a 112% (todos param; acima de 100% é ruído do estimador em grupo pequeno) |
| 3 a 5 meses com cheque especial em 12 | ~100% (76 clientes) |
| Parcela > 30% da renda declarada | 64,7% (363) |
| Comprometimento real > 50% | 36,9% (493) |
| Renda real < 60% da declarada | 92,0% (55) |
| Aposentado | 11,2% (612), protetor |
| Prazo 6 | 25,6% (308) |
| Score sem degrau acima de 600 | 600–699, 700–799 e 800+ ficam todos entre 15% e 16% |
