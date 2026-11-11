# Roteiro do pitch: 5 minutos, conduzido pelo painel

> Para quem apresenta (Guilherme). É uma proposta de Enio Rocha, 11/11/2026, 14h55. Mudem à vontade.
> Regra do manual (`analysis/resumo-abertura.md:15,49-50`): são 5 minutos com a solução funcionando, mais 2 de perguntas. A banca quer ver onde a IA entra, os principais padrões, a política e o que mudou depois do checkpoint, e como o analista valida. A banca pode pedir a decisão de pedidos ao vivo.
> Ideia central: cada cartão do painel vale **uma frase de conceito e um número**. Não ler a tela, dizer o porquê.

## O que o Miguel pediu (chamada, 14h47)
> "Apresentar as propostas que a gente fez e o impacto no negócio do cliente: comparar como funciona hoje, como a nossa proposta atende, o que usamos para chegar nesse resultado, se escala ou não. São cinco minutos, tem que ser bem curto."

Por isso, o roteiro abaixo responde quatro perguntas, nesta ordem: **hoje × proposta**, **impacto em R$**, **como chegamos lá** e **escala?** (bloco das 4:15).

## Para quem é: o head de crédito e o analista
Tudo é contado do ponto de vista dele. A frase de abertura sugerida:
> "Construímos a mesa de trabalho do analista de crédito. Ele recebe o pedido, a IA sugere a decisão com o porquê, e ele decide."

O caminho do analista, para citar em uma frase cada:
1. **Entrada:** o pedido chega (cadastro e valor pedido). O sistema puxa sozinho o birô (score, restrição, consultas, outras parcelas) e a movimentação da conta (entradas, saídas, cheque especial). O analista não digita nada disso.
2. **Sugestão:** a IA sugere aprovar, reduzir ou negar, com o valor, a faixa de risco (verde, amarelo, laranja) e os pontos a favor e contra no topo do pedido (página Revisão).
3. **Decisão:** o analista confirma ou troca e registra o motivo. A versão final usa a decisão dele onde houve revisão.
4. **Teste antes de mudar a regra:** no Simulador, ele mexe num pedido e vê a sugestão mudar; no Histórico, vê quanto a regra teria rendido no passado.

## O ouro: a página Histórico (a prova de venda)
**Conceito:** a proposta aplicada aos 10.000 pedidos que a Fortuna já decidiu, comparada com o que de fato aconteceu.
- **Nos 10.000 pedidos passados, a proposta renderia +R$ 1,27 milhão** observado (+R$ 1,55 mi estimado); só nos maduros (mais de 1 ano), cerca de +R$ 994 mil. Fonte: `site/src/data/historico.json`, campos `ganhoObservado` e `ganhoEstimado`; mensagem do commit 4a204f6.
- **A IA separa bom e mau pagador; o score do birô quase não separa:** AUC de 0,74 do modelo contra 0,50 do score (0,50 é o mesmo que tirar no cara ou coroa). Fonte: `historico.json`, campos `aucModelo` e `aucScore`.
- **O piloto confirma a escolha:** dos 427 clientes que a Fortuna aprovou fora da regra no piloto, a proposta aprovaria 257, que deram **5,1% de calote**, e negaria 170, que deram **27,7%**. Ela escolhe certo justamente onde a regra atual não deixaria passar. Fonte: `historico.json`, bloco `piloto`.
- **Cada trimestre é decidido por um modelo que não viu aquele trimestre** (treino sem ele). Isso evita olhar a resposta antes.

Frase de venda:
> "Não é promessa: pegamos os 10 mil pedidos que vocês já decidiram e vimos o que teria acontecido. A proposta teria rendido 1,27 milhão a mais, e onde ela discorda da regra atual, acerta: os clientes fora da regra que ela aprovaria deram 5% de calote; os que ela negaria, 28%."

## A fala da melhora, passo a passo, mostrando a página Histórico (sem slides)
Usar os **contratos maduros** (mais de 1 ano, desfecho conhecido): é o número mais honesto. Fonte de todos os números: `site/src/data/historico.json`, base `maduros` (5.001 pedidos, out/2024 a set/2025).

**Antes × depois (o que de fato aconteceu):**
> "Nesses 5 mil pedidos, a Fortuna aprovou 2.844 e teve 13,6% de calote, com resultado de R$ 251 mil. Nos mesmos pedidos, a nossa proposta teria 8,0% de calote e resultado de R$ 1,27 milhão. Isso é cinco vezes mais."

**De onde vem a melhora (cartão "efeito de cada ajuste"), um passo por frase:**
- "A barreira da **parcela acima de 28% da renda real** tira 223 pedidos que deram 51% de calote: **+R$ 742 mil**."
- "A barreira da **conta apertada** tira 67 pedidos que deram 91% de calote: **+R$ 302 mil**."
- "O **teto de risco de 17,5%** tira mais 44 pedidos: +R$ 18 mil."
- "**Emprestar menos que o pedido** custa R$ 45 mil. A gente mostra o que custa também."
- "E há 999 pedidos que a Fortuna negou e a proposta aprovaria. Esses **não têm desfecho**, então o ganho deles (+R$ 534 mil) é **estimado** e aparece separado, em outra cor. Não misturamos estimado com observado."

**Quem a proposta deixaria de aprovar (a matriz):**
> "Dos pedidos que a Fortuna aprovou, a proposta negaria 334. Desses, 56% deram calote. É dinheiro que não se perde."

**A frase de ética (dizer junto, não esconder):**
> "Tudo isso é sobre pedidos que já aconteceram, com o modelo treinado sem ver o período que ele decide. O ganho dos 2.000 novos é estimativa, porque o desfecho deles depende de regras que não conhecemos. Por isso mostramos sempre o observado separado do estimado."

**Por que melhora (o motivo, em uma frase):**
> "Porque olhamos a conta do cliente e não só a nota do birô: o score separa bom e mau pagador quase como uma moeda (AUC 0,50), e o nosso modelo separa com AUC 0,74."

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
> "Cada pedido sai com a sugestão da IA, o valor, a faixa de risco (verde, amarelo, laranja) e o motivo em uma linha. O analista pode buscar qualquer pedido pelo id e perguntar ao agente por que ele decidiu assim. O birô cai de propósito; tratamos com nova tentativa e cache, e o resultado é reproduzível."
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
