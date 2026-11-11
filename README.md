# Spread · Desafio Fortuna Crédito

Hackathon GOW 2026 · 11/11/2026 · entrega do `spread_final.csv` até **15h30** (checkpoint 14h15) · pitch às 15h45.

**Site do time:** https://guibellonia.github.io/spread-fortuna-credit/ (abas com tudo o que está neste repositório)

## O desafio, em 5 linhas

- A Fortuna Crédito quer uma política de aprovação e de valor melhor que a atual, com a IA achando os padrões e o analista decidindo.
- Por pedido aprovado: pagou em dia **+15%** do valor · com atraso **+5%** · não pagou **−60%** · negado **0**.
- Nota: 40 ganho sobre a política atual nos 2.000 pedidos novos · 25 padrões · 15 pitch · 10 painel · 10 qualidade técnica.
- O CSV sai do código (`id_pedido,decisao,valor_aprovado`); editado à mão desclassifica.
- Regras completas: [analysis/resumo-abertura.md](analysis/resumo-abertura.md).

## Onde está cada coisa

| Pasta | O que tem |
|---|---|
| `analysis/` | análises da base (uma por autor), padrões, censura, pendências, resumo e transcrição da abertura |
| `prompts/` | prompts de contexto do time, com autor e versão |
| `api-baseline/` | baseline da API do bureau |
| `docker/` e `docker-compose.yml` | banco local |
| `index.html` | o site do time (GitHub Pages) |

## Como contribuir

Todo mundo pode e deve contribuir. Para não pisar no trabalho do outro:

1. **Antes de começar:** `git pull`. Leia o que já existe na pasta do assunto.
2. **Um arquivo por contribuição,** com o seu nome quando for opinião ou análise sua (ex.: `analysis/analise-<nome>.md`, `prompts/<nome>_<assunto>_v1.md`).
3. **Não reescreva o arquivo de outra pessoa.** Discorde num arquivo seu, citando o dela, ou converse no chat do time.
4. **Todo número com a fonte:** o script ou a consulta que o produz. Hipótese marcada como hipótese.
5. **Versão nova = arquivo novo** (`_v2`), para comparar.
6. **Nunca suba o token do bureau** nem senha de banco. Use variável de ambiente.
7. **Commit pequeno e com mensagem clara.** Depois `git pull --rebase` e `git push`.

O site atualiza sozinho a cada push na `main`. Para um documento novo aparecer como aba, avise quem está cuidando do `index.html`.

## Decisões do time

| Quando | Decisão |
|---|---|
| 08h50 | Python; repositório único; prompts versionados |
| 09h00 | cada um roda a própria análise; depois juntamos num prompt único |
| 09h00 | duas frentes: back-end (inteligência e automação) e front-end (painel) |
