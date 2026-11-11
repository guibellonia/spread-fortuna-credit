# Para discussão: como não tirar zero e onde está o ganho seguro

Revisão por um conselho de outros modelos de IA (5 papéis) sobre as duas políticas, a do time e a minha. Conclusão: não entregar nenhuma das duas crua.

## O risco que pesa 40 pontos
A nota é o ganho sobre a política atual. **Ganho zero ou negativo = zero.**
- Copiar a atual dá zero.
- Aprovar quem a atual nega (score até 600, restrição) troca 0 por −60% se o calote estiver subestimado. É a única direção que pode negativar sozinha.
- Negar quem a atual aprova e não paga só pode melhorar.

## Fusão conservadora (piso seguro)
Partir da política atual e **só apertar**:
1. Negar o grupo "saídas maiores que as entradas nos 3 meses antes" (91% de calote). Dos 1.145 que a atual aprova nos novos, **34** estão nele.
2. Tratar os que pedem parcela acima de 28% da renda real (50% de calote). Dos 1.145, **76** estão nessa faixa.
3. Não cortar valor de quem está entre 20% e 28%: ali o calote não sobe.

Depois, em cima do piso, decidir o que afrouxar (score, 1 restrição) com teste na base.

## Cinco testes de 15 minutos que decidem
| # | Dúvida | Teste |
|---|---|---|
| 1 | Cheque especial sozinho (30%, só 23 casos) entra no filtro? | taxa nas duas metades; entra só se passar de 20% nas duas |
| 2 | 20% da renda declarada é o mesmo degrau que 28% da renda real? | calote por faixa, nas duas medidas, e quantos reais o teto de 20% corta na zona plana |
| 3 | Reduzir o valor muda o desfecho, ou o risco é da pessoa? | comparar parcela pedida × aprovada; se a pedida prever igual, negar em vez de reduzir |
| 4 | Dá para aprovar quem tem 1 restrição? | resultado financeiro desse grupo, só com contratos de 12+ meses |
| 5 | 6 meses de contrato bastam para treinar? | quantos "bons aos 6 meses" viram calote aos 12 |

## Minha posição
- Os dois filtros (conta apertada e 28% da renda real) entram em qualquer política.
- Afrouxar score e restrição: só com o teste 4 e 5 na mão.
- Reduzir valor em vez de negar: o manual sugere que funciona; a base não tem caso que prove.
