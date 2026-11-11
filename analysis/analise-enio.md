# Análise do Enio · o que complementa e onde diverge

Complementa `analise-banco.md` (Juliano). Não repete o que já está lá: traz só o que medi em separado, o que confirma e onde diverge.
Cada número tem script em `scripts-enio/` que o refaz.

## O que bate com a versão do time
- Política atual nos 2.000 novos: **1.145 aprovados, R$ 8.856.449,87**. Reproduz 100% das 8.737 decisões do histórico.
- A regra dos 30% **reduz o valor**, não nega.
- **Score não separa** bom de mau pagador.
- A árvore do Juliano também corta em **28% de parcela sobre a renda**, o mesmo degrau que achei por outro caminho.
- O grupo dele "sobra mensal até R$ 565" (75%) e o meu "saídas maiores que as entradas" (91%) apontam para os mesmos clientes de conta apertada.

## Como medimos
- "Não paga" = alguma parcela com 90 dias ou mais de atraso (bate 582 de 582 com `inadimplente`).
- Base madura: **2.844 aprovados com pedido até 30/09/2025** (12 meses ou mais de contrato).
  Em dia 66,4% · atraso 20,0% · não paga **13,6%**.
- Cada padrão foi conferido em duas metades da base, por tempo.

## Dois padrões fortes
1. **Conta apertada:** saídas maiores que as entradas em algum dos 3 meses antes do pedido.
   **91% não pagam** (67 contratos maduros; 97% e 86% nas metades). Sem esse sinal: 11,6%.
   Nos novos: **97 pedidos**. Grupo menor, só cheque especial nos 2 meses antes: 30% (23 maduros; 29 novos).
2. **Parcela pesada sobre a renda real:** renda real = a menor entre a renda declarada e as entradas médias da conta.
   Até 28% a inadimplência fica plana em ~8%. Acima de 28%: **50%** (30–32%: 50%; 35–40%: 75%).
   Nos novos: **159 pedidos** pedem acima de 28%.
   Consequência: os reduzidos pela atual para 30% da renda declarada não pagam em 55% dos casos.

## Onde discordamos da política do time
| Ponto | Política do time | O que medimos |
|---|---|---|
| Conta apertada | 2+ meses de saldo negativo em 12: pega 38 novos | saídas > entradas em 3 meses: 91% de calote, 97 novos (126 com o grupo do cheque especial) |
| Teto da parcela | 20% da renda declarada, reduz 575 aprovações | o degrau está em 28% da renda real; entre 20% e 28% o calote não sobe, e cortar valor ali perde 15% por real cortado |
| Reduzir valor | o modelo escolhe de 100% a 10% | na base, só existem reduzidos a exatamente 30% da renda; abaixo disso é extrapolação |
| Restrição | nega toda restrição (377) | 1 restrição no piloto: ~13% estimado, abaixo do ponto de equilíbrio de 20%; contratos ainda novos |
| Maturidade | contratos com 6+ meses | 12+ meses; as safras de 2026 caem a 0% só por falta de tempo |

## Três variantes prontas (todas passam no validador do manual)
| Política | Aprovados | Valor aprovado | Histórico maduro |
|---|---|---|---|
| Atual | 1.145 | R$ 8,86 mi | R$ 251 mil · calote 13,6% |
| A · nega conta apertada e parcela > 28% da renda real | 1.563 | R$ 10,84 mi | R$ 1,30 mi · calote 8,3% |
| B · igual à A, mas reduz o valor até caber em 27% da renda real | 1.702 | R$ 12,13 mi | R$ 738 mil se o desfecho não mudar · R$ 1,47 mi se mudar (hipótese) |
| C · reserva: mantém score > 600 e zero restrição | 1.111 | R$ 8,40 mi | igual à B no histórico |

A e B também aceitam score a partir de 450 e até 1 restrição. Esse grupo (528 a 591 pedidos novos) não tem desfecho maduro na base: é aposta medida só no piloto.

## O que proponho ao time
1. Trocar o filtro de saldo negativo por "saídas > entradas em algum dos 3 meses antes".
2. Medir o teto da parcela pela **renda real, em 28%**, no lugar de 20% da declarada.
3. Decidir juntos: negar acima de 28% (seguro) ou reduzir até 27% (ganha mais se o manual estiver certo sobre o valor).
4. Rodar o validador em todo CSV antes de mandar.

## Birô
2.000 de 2.000 clientes consultados e guardados em disco. 113 erros 503 em 2.113 tentativas (5,3%), todos resolvidos com nova tentativa.

## Não medido
- Se reduzir o valor muda mesmo o desfecho (o manual diz que sim; a base não tem caso).
- Como os contratos ainda abertos viram desfecho na nota.
- O ganho real nos 2.000 novos: só a organização tem.
