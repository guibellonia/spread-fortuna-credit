# Roteiro do pitch: 5 minutos, conduzido pelo painel

> Para quem apresenta (Guilherme). É uma proposta de Enio Rocha, 11/11/2026, 14h55. Mudem à vontade.
> Regra do manual (`analysis/resumo-abertura.md:15,49-50`): são 5 minutos com a solução funcionando, mais 2 de perguntas. A banca quer ver onde a IA entra, os principais padrões, a política e o que mudou depois do checkpoint, e como o analista valida. A banca pode pedir a decisão de pedidos ao vivo.
> Ideia central: cada cartão do painel vale **uma frase de conceito e um número**. Não ler a tela, dizer o porquê.

## O que o Miguel pediu (chamada, 14h47)
> "Apresentar as propostas que a gente fez e o impacto no negócio do cliente: comparar como funciona hoje, como a nossa proposta atende, o que usamos para chegar nesse resultado, se escala ou não. São cinco minutos, tem que ser bem curto."

Por isso, o roteiro abaixo responde quatro perguntas, nesta ordem: **hoje × proposta**, **impacto em R$**, **como chegamos lá** e **escala?** (bloco das 4:15).

## 0:00–0:30 · Visão geral (topo)
**Conceito:** a régua do jogo.
> "Aprovar rende 15%, 5% com atraso, e um calote perde 60%. Um calote come o lucro de quatro bons pagadores. Pela conta, só vale aprovar abaixo de ~17,5% de chance de não pagar. Esse é o nosso teto."

## 0:30–1:00 · Inadimplência por safra
**Conceito:** o calote real é maior do que parece.
> "Metade dos contratos ainda está pagando. Quem conta só os que terminaram vê um calote menor. Nós corrigimos os contratos em aberto antes de qualquer conta, e o risco real sobe para perto de 16–17%."

## 1:00–2:00 · Padrões encontrados (parte 1 do manual)
**Conceito:** olhamos a conta, não só o cadastro.
> "Os padrões que mais derrubam calote vêm da movimentação: quem tirou mais do que entrou em algum dos 3 meses antes do pedido tem 91% de calote. Quem compromete mais de 28% do que de fato entra na conta (a renda real, não a declarada) tem cerca de 50%. O score acima de 600 quase não separa bom de mau pagador."
> Se perguntarem: "muitas consultas ao CPF é sinal real, mas já está dentro desses dois padrões; negar por consulta perderia dinheiro, então medimos e não viramos regra."

## 2:00–2:45 · Política proposta (parte 2 do manual) e Funil de decisão
**Conceito:** regra simples na frente, modelo atrás.
> "Restrição nega. Conta apertada nega. Parcela acima de 28% da renda real nega. O resto, o modelo escolhe o valor de maior ganho, sempre abaixo do teto de 17,5%. Negamos em vez de reduzir: os pedidos que a política atual reduz dão mais de 55% de calote, então reduzir não tira o risco."
> **O que mudou depois do checkpoint:** [preencher com a decisão final do time, por exemplo "tiramos a idade do modelo" ou "passamos a liberar só a faixa de score que o histórico prova"].

## 2:45–3:30 · Qual política rende mais · Volume aprovado · Lucro e prejuízo esperados da IA
**Conceito:** ganho com faixa, não com número cravado.
> "Comparamos a política atual, as regras e a proposta com três avaliadores e fora da amostra. Os números estão nos cartões. E aplicada aos 10 mil pedidos passados, na página Histórico, a proposta teria rendido mais."
> Dizer junto: "o desfecho dos 2.000 novos vem de regras que não conhecemos. Por isso mostramos faixa e o teste fora do tempo, não uma promessa."

## 3:30–4:15 · Ética e honestidade
**Conceito:** o que tiramos e o que admitimos.
> "Idade, gênero, estado civil e CEP não entram no modelo. Medimos o custo de tirar a idade e ficou dentro do ruído. E testamos o próprio modelo treinado só com o passado: nas faixas de score de 500 a 600 o histórico mostra calote perto do limite. Dizemos isso, e não escondemos."

## 4:15–5:00 · Revisão do analista e o chat do agente
**Conceito:** a IA sugere e o analista decide.
> "Cada pedido sai com a decisão, o valor, a faixa de risco (verde, amarelo, laranja) e o motivo em uma linha. O analista pode buscar qualquer pedido pelo id e perguntar ao agente por que ele decidiu assim. O birô cai de propósito; tratamos com nova tentativa e cache, e o resultado é reproduzível."
> **Escala?** "Sim. Tudo roda por código, num comando, e é reproduzível. O birô tem cache e nova tentativa. As regras são parâmetros que o analista ajusta sem programar. O modelo retreina com cada nova safra. O que não escala sozinho é a calibração: ela precisa ser conferida a cada safra contra o calote real."
> Fechar convidando: "escolham um pedido e a gente mostra."

## Reserva para as perguntas (2 min)
- **Onde a IA entra?** Na descoberta dos padrões (exploração e agrupamento), na estimativa de risco por pedido e na explicação ao analista. Quem decide aprovar é a régua, não a IA.
- **Por que confiar?** Cada número tem fonte no repositório. O ganho foi testado fora do tempo, e a calibração do modelo foi auditada pelo próprio time (`analysis/scripts-guilherme/out/g06_auditoria.md`).
- **Dado estranho?** Procuramos pontos fora da curva: zero valores impossíveis, mas quatro grupos com degrau tão brusco que parecem regras do próprio gerador. Fora deles, o calote é estável, perto de 10%.

## Fontes dos números citados
- 17,5%: equilíbrio da regra +15/+5/−60 com ~23% de atraso entre pagadores (`analysis/censura-agregado.md`).
- 91% e ~50%: `analysis/analise-enio.md`.
- Reduzidos com mais de 55%: `analysis/analise-enio.md`; o Guilherme mede 61,2% por Kaplan-Meier (`g06_auditoria.md`).
- Score que não separa acima de 600: `analysis/analise-guilherme.md`.
- Custo de tirar a idade e faixas de score 500–600: medição do motor v2 do Enio (fora do repositório; números com o Enio).
