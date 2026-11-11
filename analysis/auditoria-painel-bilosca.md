# Auditoria do painel de revisão contra as definições da `analysis/`

Bilosca, 11/11/2026. Dados auditados: `decisoes_mescla.csv sha256:26380dbe4e0f`, publicado às 14:49 UTC,
lido pelas quatro abas do painel (https://guibellonia.github.io/spread-fortuna-credit/dashboard/revisao/).
Amostra: 200 linhas, **119 pedidos distintos**, 96 aprovados e 23 negados.

Como os números foram apurados: as linhas das abas foram cruzadas com `hackathon.pedidos`, `clientes` e
`movimentacao_mensal` do banco local e com o bureau já em `data/cache/bureau_novos.json`. As barreiras usam
`filtros_cliente()` de `src/politica.py` e a pontuação foi recalculada com `pontuacao()` de
`src/politica_mescla.py`, as mesmas funções que geraram o arquivo publicado.

## Resultado

**Passa.** Nas 96 aprovações não há uma única violação das regras do manual nem das barreiras da análise, e a
pontuação do Daniel bate em 119 de 119 pedidos, incluindo faixa e texto do detalhe.

Sobraram três pontos em aberto, nenhum deles uma quebra de regra. Dois já foram tratados depois desta
auditoria:

- **Idade saiu do modelo** (`src/modelo.py`), e a medição mostrou que isso melhora os dois lados: o ganho
  projetado foi de +R\$ 385 a 500 mil para +R\$ 504.666 e o observado fora da amostra ficou em +R\$ 392.138,
  no mesmo patamar de antes.
- **A barreira dos 28% fica como está**, negando. Medimos a alternativa de cortar o valor em vez de negar e ela
  piora muito o resultado real: o ganho observado cai para +R\$ 183.773, abaixo até das regras do Bilosca.
- **A restrição no bureau continua em aberto.**

## O que está condizente

| Definição | Onde está | Resultado na amostra |
|---|---|---|
| Valor até o solicitado e até R\$ 30 mil, mínimo de R\$ 500, múltiplo de R\$ 100, negado com 0,00 | `resumo-abertura.md`, dicionário de dados | 0 violações em 96 |
| Barreira de conta apertada | `pontuacao-risco.md` §1 | 0 aprovações |
| Barreira de parcela acima de 28% da renda real | `pontuacao-risco.md` §1 | 0 aprovações |
| Parcela até 28% da renda declarada | `PARAMS` em `src/politica.py` | 0 aprovações acima |
| Sem restrição ativa no bureau | `padroes-agregado.md` (39,4% de calote) | 0 aprovações |
| Risco até 17,5%, o ponto de equilíbrio | `padroes-agregado.md`, linha 4 | maior risco aprovado: 16,68% |
| Ganho esperado positivo | matriz +15% / +5% / −60% | 0 aprovações com ganho zero ou negativo |
| Pontuação em três faixas, verde ≤ 0, amarela = 1, laranja ≥ 2 | `pontuacao-risco.md` §4 | 119 de 119 conferem |
| A faixa não decide, só diz quanto confiar | `pontuacao-risco.md` | 47 dos 50 laranjas aprovados, 1 verde negado |

A pontuação e o modelo foram construídos separadamente e concordam na direção, o que é um bom argumento de pitch:

| Faixa | Aprovados | Risco médio do modelo | Mediana |
|---|---|---|---|
| Verde | 28 | 5,6% | 4,5% |
| Amarela | 21 | 6,9% | 6,2% |
| Laranja | 47 | 8,0% | 7,0% |

Três lacunas que existiam na publicação das 14:20 foram fechadas:

1. O motivo da conta apertada aparece com o nome certo, "saídas maiores que entradas nos últimos 3 meses".
   A regra de "2+ meses com saldo negativo", que o `pontuacao-risco.md` §2 mandou aposentar, saiu da tela.
2. O painel mostra pontos, faixa e o detalhe de onde veio cada ponto, que é a explicabilidade prometida ao
   analista, além da decisão das regras do Bilosca lado a lado.
3. A aba laranja virou a fila de revisão que o documento sugeriu. Dos 47 laranjas aprovados, 18 saíram com
   valor reduzido.

## O que não está condizente

### 1. A barreira dos 28% nega em vez de reduzir o valor

São 6 negados por esse motivo, R\$ 116.100 pedidos, dos quais a política atual aprovaria R\$ 82.598. Quatro deles
têm risco do modelo abaixo de 7,3%:

| Pedido | Solicitado | Risco | A atual daria |
|---|---|---|---|
| P-07635 | R\$ 28.100 | 6,4% | R\$ 27.508,63 |
| P-04364 | R\$ 15.300 | 4,7% | R\$ 15.300,00 |
| P-06029 | R\$ 12.200 | 6,2% | R\$ 9.588,42 |
| P-00808 | R\$ 19.500 | 7,2% | R\$ 12.171,85 |

O `padroes-agregado.md`, linha 10, define que parcela e comprometimento se medem **sobre o valor aprovado**,
não sobre o pedido. Medido assim, esses quatro caberiam dentro dos 28% com um valor menor, em vez de sair com
zero.

**Medido e recusado.** Troquei a barreira por um teto de valor, aprovando o máximo que faz a parcela caber em
28% da renda real, e rodei `politica_mescla.py --comparar`. A proposta passaria de 1.412 para 1.537 aprovados
e de R\$ 9,34 mi para R\$ 10,33 mi, e o ganho projetado subiria para +R\$ 582.938. Só que, nos pedidos reais com
desfecho conhecido (out/25 a mar/26), o ganho cai de +R\$ 392.138 para +R\$ 183.773, abaixo das regras do
Bilosca (+R\$ 336.818). A barreira fica. A definição de medir sobre o valor aprovado continua certa para
descrever os padrões, mas não se sustenta como regra de decisão nesse grupo: são clientes cuja conta não
aguenta o pedido, e dar menos não os torna bons pagadores. É exatamente a limitação que o
`pontuacao-risco.md` registra, de que a base não mostra se reduzir o valor reduz o risco.

### 2. Restrição ativa nega mesmo quando o modelo vê risco baixo

12 negados por restrição, R\$ 92.400 pedidos. Sete deles têm risco abaixo de 10%, o menor em 2,27% (P-00990),
e o `padroes-agregado.md` avisa que os 39,4% da tabela de restrição são efeito bruto, porque cada grupo foi
olhado sozinho, sem limpar os outros. O `pontuacao-risco.md` lista só duas barreiras, conta apertada e parcela
pesada, e restrição não é uma delas.

### 3. Idade entra no modelo (corrigido)

`padroes-agregado.md`, linha 13: "Gênero, estado civil, CEP e idade são só referência. Não devem entrar na
política." Três ficaram de fora e `"idade"` tinha ficado na lista `ATRIBUTOS` de `src/modelo.py`.

Removida. O modelo foi retreinado sem ela e a política regerada: 1.412 aprovados de 2.000, R\$ 9.338.100, CSV
validado por `src/validar_csv.py`. O ganho projetado ficou em +R\$ 504.666 pelo GBM corrigido e o observado
fora da amostra em +R\$ 392.138, ou seja, tirar a variável sensível não custou resultado. O verificador de
`src/explicabilidade.py`, que lista os atributos sensíveis usados direto pelo modelo, passa a fechar limpo.

## Justificativas e detalhes

### Sobre a barreira dos 28%

A publicação das 14:20 reduzia o valor nesses casos e a das 14:49 nega. A comparação acabou respondendo qual
das duas vale, com as quatro políticas medidas lado a lado:

| Política | Aprovados | Ganho projetado (GBM) | Ganho observado fora da amostra |
|---|---|---|---|
| Atual | 1.145 | referência | referência |
| Regras do Bilosca | 1.043 | +R\$ 285.782 | +R\$ 336.818 |
| Proposta, barreira que nega | 1.412 | +R\$ 504.666 | **+R\$ 392.138** |
| Proposta, teto que reduz | 1.537 | +R\$ 582.938 | +R\$ 183.773 |

O projetado e o observado discordam, e vale o observado, porque são pedidos reais com desfecho conhecido. O
modelo fica otimista justamente onde não tem evidência, que é o cliente recebendo menos do que pediu.

### Sobre a restrição no bureau

Agora existe justificativa registrada no cabeçalho de `src/politica_mescla.py`: o experimento da Fortuna entre
out/25 e mar/26 mostrou prejuízo ao afrouxar score ou restrição **sem as barreiras ligadas**. O detalhe é que a
política proposta afrouxou score e manteve restrição, enquanto a evidência citada trata os dois juntos. Falta a
medida da variante "afrouxar restrição com as barreiras ligadas". É a pergunta mais provável da banca e dá para
respondê-la com número rodando `python politica_mescla.py --comparar` com essa candidata a mais.

### Sobre a faixa de risco

Duas linhas mostram que a faixa é agregada e o modelo é individual: P-05967 está verde com 47% de chance de não
pagar, negado pelo modelo, e P-13056 está laranja com 44%. É o comportamento previsto pelo documento, onde a
faixa diz quanto confiar e não decide, mas convém ter a resposta pronta se a banca abrir um desses pedidos.

### Detalhe de dados nas linhas de barreira

As linhas barradas trazem `pontos` preenchido (P-00664 com 3, P-02380 com 3) e `pontos_detalhe` dizendo
"barrado antes da pontuação". O analista vê um número que a própria linha diz não existir. Zerar o campo ou
mostrar o detalhe resolve.

### Duas definições de renda real

O `padroes-agregado.md` usa a média de `entradas_salario` para assalariado e aposentado, e de `total_entradas`
para autônomo e empresário. O `pontuacao-risco.md` usa o menor valor entre a renda declarada e a média de
entradas. O código segue o segundo. Como é a variável da barreira principal, vale alinhar o texto.

### Volume na aba não enviesada

Das quatro abas, só a dos 50 primeiros ids não é enviesada por construção. Nela: 36 aprovados, 72% do total,
R\$ 228.200. A política atual aprovaria 24 pedidos e R\$ 191.272; as regras do Bilosca, 23 pedidos e R\$ 179.100.
As faixas ficam em 17 verdes, 13 amarelas, 7 laranjas e 13 barreiras.

## Limites desta auditoria

- 119 pedidos dos 2.000. As abas de laranja e de divergentes são enviesadas por construção, então só os 50
  primeiros ids servem para falar de perfil.
- Os padrões da `analysis/` entraram como dados; não refiz as tabelas de inadimplência.
- Os números de ganho vêm de `python politica_mescla.py --comparar`, rodado duas vezes: uma com a barreira e
  outra com o teto, as duas já sem a idade no modelo. O painel só reflete isso depois de
  `supabase/publicar_decisoes.py` e `site/scripts/snapshot.py`.
