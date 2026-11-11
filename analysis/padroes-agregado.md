# Padrões com inadimplência projetada · agregado

Todos os 6.033 aprovados do histórico, com a correção de censura explicada em `censura-agregado.md`.
**Média: 15,9%.** Ponto de equilíbrio para aprovar: **~17,5%**.

- **Inadimplência projetada** = paradas ÷ soma da fração já observada de cada contrato. Em grupos pequenos e muito
  ruins ela pode passar de 100%: leia como "praticamente todos param".
- **Pagadores com atraso** = entre os que não pararam e têm 4+ parcelas decididas, quantos pagaram alguma com
  atraso (valem +5%, não +15%).
- **Comprometimento e parcela usam o valor aprovado**, não o pedido.
- **Renda real** = média de `entradas_salario` para assalariados e aposentados, e de `total_entradas` para
  autônomos e empresários. Nestes, o "salário" é só ~10% das entradas.
- **Gênero, estado civil, CEP e idade são só referência.** Não devem entrar na política.
- **Cada grupo foi olhado sozinho, sem limpar os outros.** Por exemplo, parte do efeito de "consultas 4+" vem da
  conta apertada (ver onda 1 do Enio).

Refazer: `cd analysis && ../.venv/Scripts/python build_dataset.py && ../.venv/Scripts/python patterns.py`
(conexão pelo `.env` da raiz; modelo em `.env.example`).

## Destaques

| Padrão (formato do manual) | Projetada | Clientes |
|---|---|---|
| Clientes com saídas ≥ 80% das entradas no ano antes do pedido têm inadimplência de ~100%, contra 15,9% da média. | ~100% | 156 |
| Clientes com 3 a 5 meses de cheque especial nos 12 antes do pedido têm inadimplência de ~100%, contra 15,9%. | ~100% | 76 |
| Clientes cuja renda na conta é menos de 60% da declarada têm inadimplência de 92%, contra 15,9%. | 92,0% | 55 |
| Clientes com parcela acima de 30% da renda declarada têm inadimplência de 65%, contra 15,9%. | 64,7% | 363 |
| Clientes com 3+ dias por mês de cheque especial, em média, têm inadimplência de 64%, contra 15,9%. | 64,3% | 199 |
| Clientes com 1 restrição ativa no bureau têm inadimplência de 39%, contra 15,9%. | 39,4% | 127 |
| Clientes com parcela + outras dívidas acima de 50% da renda real têm inadimplência de 37%, contra 15,9%. | 36,9% | 493 |
| Clientes com saldo mínimo abaixo de −R$ 2 mil têm inadimplência de 34%, contra 15,9%. | 33,5% | 397 |
| Clientes com 4+ consultas ao CPF em 90 dias têm inadimplência de 30%, contra 15,9%. | 29,6% | 591 |
| Clientes com score entre 500 e 599 têm inadimplência de 27%, contra 15,9%. | 26,6% | 183 |
| Clientes com prazo de 6 meses têm inadimplência de 26%, contra 15,9%. | 25,6% | 308 |
| Clientes com valor aprovado entre R$ 15 e 30 mil têm inadimplência de 25%, contra 15,9%. | 24,5% | 668 |
| Clientes com entradas muito oscilantes (CV ≥ 40%) têm inadimplência de 24%, contra 15,9%. | 24,3% | 542 |
| Clientes com menos de 12 meses de histórico no bureau têm inadimplência de 24%, contra 15,9%. | 24,3% | 237 |
| Empresários têm inadimplência de 21%, contra 15,9%. | 21,3% | 622 |
| Clientes com comprometimento real abaixo de 30% têm inadimplência de 11%, contra 15,9%. | 10,7–11,1% | 3.935 |
| Aposentados têm inadimplência de 11%, contra 15,9%. | 11,2% | 612 |
| Clientes com prazo de 36 meses têm inadimplência de 12,5%, contra 15,9% (e não 7%: o 7% era censura). | 12,5% | 1.529 |

## Tabelas completas

### Score do bureau

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <500 | 94 | 11 | 20,6% | 1,30x | 30% |
| 500-599 | 183 | 30 | 26,6% | 1,67x | 29% |
| 600-699 | 1.161 | 120 | 15,5% | 0,98x | 26% |
| 700-799 | 2.266 | 223 | 15,0% | 0,95x | 24% |
| 800+ | 2.329 | 242 | 16,0% | 1,00x | 23% |

### Restrições ativas

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| 0 | 5.906 | 597 | 15,4% | 0,97x | 24% |
| 1 | 127 | 29 | 39,4% | 2,48x | 52% |

### Renda declarada

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <2k | 66 | 10 | 24,6% | 1,55x | 25% |
| 2-3k | 1.045 | 130 | 19,0% | 1,20x | 26% |
| 3-5k | 2.148 | 228 | 16,0% | 1,00x | 24% |
| 5-10k | 2.201 | 199 | 14,1% | 0,89x | 23% |
| 10k+ | 573 | 59 | 15,7% | 0,99x | 24% |

### Renda real / declarada

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <60% | 55 | 27 | 92,0% | 5,79x | 63% |
| 60-80% | 1.551 | 169 | 16,6% | 1,05x | 24% |
| 80-95% | 3.335 | 321 | 14,8% | 0,93x | 24% |
| 95%+ | 1.092 | 109 | 15,1% | 0,95x | 23% |

### Parcela / renda declarada

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <10% | 3.770 | 271 | 11,9% | 0,75x | 23% |
| 10-20% | 1.574 | 136 | 11,9% | 0,75x | 25% |
| 20-30% | 326 | 52 | 19,4% | 1,22x | 23% |
| 30%+ | 363 | 167 | 64,7% | 4,07x | 43% |

### Comprometimento real (parcela+outras)/renda real

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <20% | 2.831 | 197 | 11,1% | 0,70x | 23% |
| 20-30% | 1.104 | 80 | 10,7% | 0,68x | 22% |
| 30-40% | 1.001 | 124 | 18,3% | 1,15x | 23% |
| 40-50% | 604 | 97 | 24,3% | 1,53x | 26% |
| 50%+ | 493 | 128 | 36,9% | 2,32x | 44% |

### Dívidas em outras instituições / renda real

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| 0 | 2.444 | 235 | 14,6% | 0,92x | 24% |
| <10% | 837 | 84 | 15,4% | 0,97x | 23% |
| 10-20% | 1.032 | 111 | 16,3% | 1,03x | 21% |
| 20%+ | 1.720 | 196 | 17,6% | 1,11x | 28% |

### Dias de cheque especial (média/mês)

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| 0 | 4.263 | 377 | 13,6% | 0,86x | 24% |
| até 1 | 626 | 62 | 15,0% | 0,94x | 21% |
| 1-3 | 945 | 103 | 16,6% | 1,04x | 24% |
| 3+ | 199 | 84 | 64,3% | 4,05x | 40% |

### Meses com cheque especial (12m)

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| 0 | 4.263 | 377 | 13,6% | 0,86x | 24% |
| 1-2 | 1.694 | 199 | 17,8% | 1,12x | 23% |
| 3-5 | 76 | 50 | 103,0% | 6,49x | 76% |

### Saldo mínimo no período

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| < -2k | 397 | 84 | 33,5% | 2,11x | 29% |
| -2k a 0 | 1.373 | 165 | 18,0% | 1,14x | 23% |
| 0-2k | 975 | 102 | 16,1% | 1,01x | 24% |
| 2k+ | 3.288 | 275 | 12,8% | 0,81x | 25% |

### Entradas últimos 3m vs anteriores

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| caiu 30%+ | 117 | 10 | 14,3% | 0,90x | 36% |
| caiu 10-30% | 465 | 66 | 21,5% | 1,35x | 24% |
| estável | 4.584 | 437 | 14,6% | 0,92x | 24% |
| subiu 10%+ | 637 | 75 | 17,8% | 1,12x | 23% |

### Variação das entradas (CV)

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <10% | 3.587 | 339 | 14,5% | 0,91x | 24% |
| 10-20% | 1.382 | 129 | 14,2% | 0,90x | 22% |
| 20-40% | 432 | 51 | 17,8% | 1,12x | 26% |
| 40%+ | 542 | 86 | 24,3% | 1,53x | 29% |

### Saídas / entradas

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <50% | 5.877 | 524 | 13,6% | 0,86x | 24% |
| 80-100% | 54 | 38 | 112,0% | 7,05x | 77% |
| 100%+ | 102 | 64 | 105,8% | 6,66x | 81% |

### Tempo de conta

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <6m | 364 | 45 | 18,8% | 1,18x | 26% |
| 6-12m | 402 | 30 | 11,8% | 0,74x | 20% |
| 12-24m | 724 | 78 | 16,4% | 1,03x | 24% |
| 24m+ | 4.543 | 473 | 15,9% | 1,00x | 25% |

### Consultas ao CPF em 90 dias

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| 0 | 2.192 | 225 | 15,5% | 0,98x | 23% |
| 1 | 1.609 | 131 | 12,6% | 0,79x | 23% |
| 2 | 954 | 98 | 15,6% | 0,98x | 27% |
| 3 | 687 | 62 | 13,7% | 0,86x | 24% |
| 4+ | 591 | 110 | 29,6% | 1,86x | 28% |

### Meses de histórico no bureau

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <12 | 237 | 34 | 24,3% | 1,53x | 28% |
| 12-24 | 413 | 53 | 19,0% | 1,20x | 21% |
| 24-60 | 1.246 | 124 | 15,4% | 0,97x | 23% |
| 60+ | 4.137 | 415 | 15,3% | 0,96x | 25% |

### Tipo de vínculo

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| aposentado | 612 | 47 | 11,2% | 0,70x | 23% |
| assalariado | 3.426 | 332 | 15,0% | 0,94x | 24% |
| autonomo | 1.373 | 162 | 17,8% | 1,12x | 24% |
| empresario | 622 | 85 | 21,3% | 1,34x | 27% |

### Prazo (meses)

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| 12 | 1.238 | 177 | 17,3% | 1,09x | 24% |
| 18 | 1.158 | 114 | 13,5% | 0,85x | 22% |
| 24 | 1.800 | 176 | 16,1% | 1,01x | 24% |
| 36 | 1.529 | 89 | 12,5% | 0,79x | 26% |
| 6 | 308 | 70 | 25,6% | 1,61x | 26% |

### Valor aprovado

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <3k | 585 | 50 | 13,2% | 0,83x | 24% |
| 3-8k | 3.271 | 269 | 12,5% | 0,79x | 24% |
| 8-15k | 1.509 | 205 | 20,6% | 1,29x | 24% |
| 15-30k | 668 | 102 | 24,5% | 1,54x | 29% |

### Idade

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| <25 | 607 | 59 | 15,3% | 0,97x | 24% |
| 25-34 | 1.205 | 136 | 17,4% | 1,09x | 25% |
| 35-49 | 1.816 | 193 | 16,1% | 1,02x | 25% |
| 50-64 | 2.046 | 209 | 15,7% | 0,99x | 23% |
| 65+ | 359 | 29 | 11,7% | 0,73x | 24% |

### Gênero (só referência)

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| feminino | 2.995 | 313 | 16,2% | 1,02x | 25% |
| masculino | 2.969 | 302 | 15,4% | 0,97x | 24% |
| nao_informado | 69 | 11 | 26,3% | 1,65x | 22% |

### Estado civil (só referência)

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| casado | 2.161 | 228 | 16,1% | 1,01x | 25% |
| divorciado | 591 | 63 | 16,6% | 1,04x | 26% |
| solteiro | 2.395 | 261 | 16,7% | 1,05x | 23% |
| uniao_estavel | 709 | 65 | 14,1% | 0,89x | 27% |
| viuvo | 177 | 9 | 7,8% | 0,49x | 28% |

### Região do CEP (1º dígito, só referência)

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| 0 | 548 | 55 | 15,0% | 0,95x | 24% |
| 1 | 277 | 43 | 23,6% | 1,48x | 26% |
| 2 | 702 | 80 | 17,5% | 1,10x | 24% |
| 3 | 714 | 77 | 16,2% | 1,02x | 26% |
| 4 | 886 | 82 | 14,4% | 0,91x | 22% |
| 5 | 470 | 42 | 13,6% | 0,86x | 26% |
| 6 | 811 | 85 | 16,1% | 1,01x | 25% |
| 7 | 365 | 40 | 16,5% | 1,04x | 21% |
| 8 | 533 | 52 | 15,2% | 0,96x | 24% |
| 9 | 727 | 70 | 15,0% | 0,94x | 26% |

### Política aplicada

| Grupo | Clientes | Paradas | Inadimplência projetada | vs média | Pagadores com atraso |
|---|---|---|---|---|---|
| atual | 4.907 | 480 | 14,7% | 0,93x | 23% |
| piloto | 1.126 | 146 | 21,6% | 1,36x | 28% |

