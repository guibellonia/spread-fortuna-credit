# Cruzamento das tabelas e pontuação de risco · Time Spread

Cruzamos as cinco tabelas do banco (`pedidos`, `clientes`, `movimentacao_mensal`, `bureau`, `parcelas`) para achar o
que separa quem paga de quem não paga. O resultado é uma análise de crédito em dois passos: **duas barreiras** que
negam direto e uma **pontuação simples** que o analista de risco consegue ler cliente a cliente.

Cada número deste documento sai das consultas em `sql-cruzamentos/` (ver "Como refazer" no fim).

## Resumo em 30 segundos

- **Dois sinais fortes explicam quase metade do calote:** conta apertada (91% não pagam) e parcela pesada sobre a
  renda real (43% a 77% não pagam). Esses viram barreira.
- **Saldo negativo e cheque especial são, quase sempre, os mesmos clientes da conta apertada.** Sozinhos, fora dela,
  não indicam risco alto. A regra de "2+ meses de saldo negativo" é pior que a de conta apertada.
- **No resto da base não existe sinal forte**, só sinais fracos que se somam. Eles viram uma pontuação de 3 faixas.
- **As três faixas dão lucro.** A faixa diz quanto confiar no cliente, não se ele deve ser negado.
- **O score do bureau não ajuda:** 13% a 14% de calote em qualquer faixa acima de 600.

## Base usada

- **2.844 contratos aprovados com 12 meses ou mais de contrato** (pedido até 30/09/2025). Calote médio: **13,6%**.
- Contratos mais novos ficam de fora porque ainda não tiveram tempo de atrasar e pareceriam bons pagadores.
- **Calote** = `situacao_final = 'inadimplente'`.
- **Renda real** = a menor entre a renda declarada e a média de entradas na conta nos 12 meses antes do pedido.
- Para separar padrão de acaso, cada achado foi conferido em duas metades no tempo: pedidos até mar/25 e de abr a
  set/25.

## Como as tabelas se ligam

| Tabela | O que guarda | Ligação |
|---|---|---|
| `pedidos` | valor, prazo, decisão, política usada e desfecho | `id_pedido`, `id_cliente` |
| `clientes` | renda declarada, profissão, vínculo, tempo de conta | `id_cliente` |
| `movimentacao_mensal` | entradas, salário, saídas, saldo e cheque especial, mês a mês, 12 meses antes do pedido | `id_cliente` |
| `bureau` | score, restrições, dívidas em outras instituições, consultas ao CPF | `id_pedido` (só histórico) |
| `parcelas` | vencimento, pagamento e atraso de cada parcela | `id_pedido` (só aprovados) |

Os 2.000 pedidos novos têm cadastro e movimentação, mas **não têm bureau**: ele precisa ser buscado na API.

## 1. Os dois sinais fortes (barreiras)

### Conta apertada

As saídas da conta chegam perto da renda ou das entradas. Medimos de três jeitos e **os três marcam exatamente os
mesmos 67 clientes**:

- saídas médias ≥ 70% da renda declarada;
- saídas médias ≥ 95% das entradas;
- saídas maiores que as entradas em algum dos 3 meses antes do pedido.

| | Contratos | Calote |
|---|---|---|
| Conta apertada | 67 | **91%** |
| Demais | 2.777 | 11,8% |

### Parcela pesada sobre a renda real

| Parcela ÷ renda real | Contratos | Calote |
|---|---|---|
| Até 15% | 2.146 | 9,6% |
| 15% a 20% | 280 | 13,9% |
| 20% a 28% | 192 | 13,5% |
| **28% a 35%** | 169 | **42,6%** |
| **35% ou mais** | 57 | **77,2%** |

Até 28% o risco é praticamente plano. **Cortar valor de quem está entre 20% e 28% só reduz o ganho.**

### Os dois são independentes

| Conta apertada | Parcela pesada | Contratos | Calote |
|---|---|---|---|
| não | não | 2.554 | **8,4%** |
| não | sim | 223 | 50,7% |
| sim | não | 64 | 90,6% |
| sim | sim | 3 | 100% |

Juntos, explicam **45% de todo o calote** da base.

## 2. Saldo negativo e cheque especial: mesmo grupo?

Em grande parte, sim.

| Conta apertada | Saldo negativo 2+ meses | Cheque especial > 30 dias | Contratos | Calote |
|---|---|---|---|---|
| sim | sim | sim | 45 | 91% |
| sim | sim | não | 13 | 85% |
| sim | não | não | 9 | **100%** |
| não | sim | sim | 15 | **20%** |
| não | sim | não | 4 | 25% |
| não | não | não | 2.758 | 11,7% |

- 58 dos 77 clientes com saldo negativo e 45 dos 60 com cheque especial longo **já estão na conta apertada**.
- Fora dela, os dois sinais ficam em ~21% de calote, em cima do ponto de equilíbrio (abaixo).
- **Comparação com a regra atual do time** ("nega 2+ meses de saldo negativo"): ela deixa passar 9 clientes que não
  pagaram nenhum e nega 19 que em sua maioria pagaram. Trocar por "conta apertada" é melhor nas duas pontas. É a
  mesma conclusão do Enio em `analise-enio.md`.

**Ponto de equilíbrio:** com +15% quando paga e −60% quando não paga, aprovar só compensa se o calote ficar abaixo
de ~20%.

## 3. O que sobra: sinais fracos

Sem barreira nenhuma ficam **2.537 contratos com 8,4% de calote**. Dentro deles, nenhum sinal sozinho passa de
12,5%. O que se repete nas duas metades:

| Sinal | Calote | Contratos |
|---|---|---|
| Prazo de 6 ou 12 meses | ~11% | 641 |
| Prazo de 36 meses | **4,5%** | 667 |
| Empresário | 12,5% | 248 |
| Aposentado | **4,1%** | 296 |
| Entradas da conta instáveis (os 20% que mais variam) | 12,2% | 501 |
| Parcela nova + dívidas em outras instituições ≥ 35% da renda real | 12,0% | 507 |

**Não serviram:** score, idade, renda, tempo de conta, estado civil, gênero (diferenças pequenas ou que mudam de uma
metade para a outra) e profissão (grupos pequenos; Eletricista, por exemplo, teve 28% numa metade e 0% na outra).

## 4. A pontuação

### Passo 1 · Barreiras (negam direto)

1. **Conta apertada:** saídas ≥ 70% da renda declarada.
2. **Parcela pesada:** parcela acima de 28% da renda real.

### Passo 2 · Pontos (para quem passou pelas barreiras)

| Sinal | Pontos |
|---|---|
| Prazo de 6 ou 12 meses | +1 |
| Prazo de 36 meses | −1 |
| Empresário ou autônomo | +1 |
| Aposentado | −1 |
| Entradas da conta instáveis (variação mês a mês de 16% ou mais) | +1 |
| Parcela nova + dívidas em outras instituições ≥ 35% da renda real | +1 |

### Resultado no histórico

| Pontos | Contratos | Calote | Ganho esperado por R$ 100 |
|---|---|---|---|
| −2 | 58 | 1,7% | R$ 12,00 |
| −1 | 456 | 3,7% | R$ 10,00 |
| 0 | 769 | 6,6% | R$ 8,00 |
| 1 | 649 | 9,9% | R$ 5,60 |
| 2 | 418 | 12,4% | R$ 3,70 |
| 3 | 152 | 13,8% | R$ 2,20 |
| 4 | 35 | 17,1% | R$ 0,40 |

Agrupado em faixas:

| Faixa | Pontos | Contratos | Calote (1ª / 2ª metade) | Ganho esperado por R$ 100 | Pedidos novos |
|---|---|---|---|---|---|
| 🟢 Verde | 0 ou menos | 1.283 | 5,4% (6,5% / 4,3%) | R$ 8,90 | 932 |
| 🟡 Amarela | 1 | 649 | 9,9% (11,6% / 8,0%) | R$ 5,60 | 473 |
| 🟠 Laranja | 2 ou mais | 605 | 13,1% (15,2% / 10,7%) | R$ 3,10 | 337 |
| ⛔ Barreira | — | — | 51% a 91% | negativo | 258 |

O ganho esperado aplica a regra da nota (+15% se pagou em dia, +5% se pagou com atraso, −60% se não pagou) às taxas
observadas em cada linha.

### Como ler

- **Cada ponto a mais aumenta o calote, e a ordem se mantém nas duas metades.**
- **Todas as faixas dão lucro.** A faixa diz quanto confiar no cliente, não se ele deve ser negado.
- **O analista vê de onde veio cada ponto.** Exemplo: "+1 prazo curto, +1 autônomo, −1 aposentado = 1 ponto, faixa
  amarela".
- **Sugestão ainda não testada:** na faixa laranja, aprovar um valor menor ou mandar para revisão do analista, em vez
  de aprovar o valor pedido inteiro.

## Limitações

- **Só conhecemos o desfecho de quem foi aprovado.** Quem a política atual negou nunca teve a chance de pagar ou não.
- **Os pedidos novos ainda não têm um dos pontos.** O sinal de dívidas em outras instituições vem do bureau. Sem ele,
  parte dos clientes contados como verde ou amarela deve subir de faixa quando o bureau for consultado.
- **A base não mostra se reduzir o valor reduz o risco.** Quase ninguém no histórico recebeu menos do que pediu.
- **A segunda metade tem calote menor em quase todos os grupos** (6,7% contra 10%), provavelmente porque esses
  contratos tiveram menos tempo para dar errado. As taxas dela estão um pouco subestimadas.

## Como refazer

Com o banco do `docker-compose.yml` no ar (container `fortuna-db`), da raiz do repositório, em PowerShell. Os
arquivos rodam em pares, porque o segundo usa a tabela temporária criada pelo primeiro:

```powershell
$d = "analysis\sql-cruzamentos"
Get-Content "$d\01-cruzamentos.sql", "$d\02-sobreposicao.sql" -Encoding UTF8 | docker exec -i fortuna-db psql -U postgres -d fortuna -q
Get-Content "$d\03-residuo.sql", "$d\04-pontuacao.sql" -Encoding UTF8 | docker exec -i fortuna-db psql -U postgres -d fortuna -q
```

| Arquivo | O que mostra |
|---|---|
| `01-cruzamentos.sql` | calote por faixa de cada variável na base madura |
| `02-sobreposicao.sql` | sobreposição de conta apertada, saldo negativo e cheque especial |
| `03-residuo.sql` | sinais fracos dentro do grupo sem barreira |
| `04-pontuacao.sql` | pontuação, faixas e contagem nos pedidos novos |
