# Resumo da abertura (kickoff das 08h) + manual

Resumo do que foi dito na abertura, conferido contra o Manual do Participante. Não é a transcrição: é o que importa para decidir.

## O jogo
- Fortuna Crédito: crédito pessoal até R$ 30 mil, juros de 3% ao mês, parcela pela tabela Price.
- Base: 10.000 pedidos históricos (out/24 a set/26, corte em 30/09/2026) e 2.000 pedidos novos (out/26) para decidir.
- A organização já tem o desfecho dos 2.000 novos, gerado por regras que ela definiu. O desfecho considera o valor aprovado.

## A nota (0 a 100)
| Critério | Peso | Como |
|---|---|---|
| Ganho sobre a política atual | 40 | nosso resultado menos o da atual, nos mesmos 2.000. Maior ganho = nota 10; ganho zero ou negativo = nota zero |
| Padrões descobertos pela IA | 25 | quantos padrões corretos, bem explicados |
| Pitch | 15 | 5 minutos com a solução funcionando + 2 de perguntas |
| Painel de experimentação | 10 | o analista entende sem ler código; a banca avalia conteúdo, não visual |
| Qualidade técnica | 10 | código organizado, falha do birô tratada, reprodutível, README de um comando |

Resultado por pedido aprovado: pagou em dia **+15%** do valor aprovado · com atraso **+5%** · não pagou **−60%** · negado **0**.
Um calote custa o lucro de quatro bons pagadores.

## Prazos
- 14h15: checkpoint (arquivo validado + 10 minutos com mentor).
- **15h30: code freeze, sem tolerância.** Arquivo `spread_final.csv` na pasta do time no Teams.
- 15h45: pitches.
- Validação do formato do CSV: a qualquer hora, quantas vezes quiser, pelo canal.

## O que desclassifica ou zera
- CSV que a solução não gerou (editado à mão).
- Arquivo fora do formato: não pontua.
- Enviado depois das 15h30: não pontua.

## CSV
`id_pedido,decisao,valor_aprovado` · UTF-8 · vírgula · ponto decimal com 2 casas · `APROVADO` ou `NEGADO` em maiúsculas · `0.00` quando negado · valor nunca acima do pedido nem de 30000 · não abrir no Excel.

## Regras
- A IA precisa participar da descoberta dos padrões e da decisão. Só escrever código com IA não conta.
- Só dados do kit (banco e API do birô).
- A IA sugere, o analista de risco decide.
- Pode conversar com outros times, sem compartilhar código, consultas ou arquivos.

## Birô
`GET /v1/bureau/{id_cliente}` com o token do time. Falha com 503 e demora de propósito. A resposta de um cliente não muda. Sem limite de chamadas.

## Pessoas
- Cliente (representa a Fortuna e desempata): Gabi. Sessões de até 15 minutos por time, pela agenda dela no Teams; dúvidas também por mensagem.
- Banca: Cadu, Miguel, Bruno e Gabi.

## O pitch precisa mostrar
Onde a IA entra · os principais padrões · a política e o que mudou depois do checkpoint · como o analista valida o que a IA propõe. A banca pode pedir a decisão de alguns pedidos ao vivo.
