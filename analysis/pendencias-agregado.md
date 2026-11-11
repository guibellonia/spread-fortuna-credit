# Pendências técnicas e testes · agregado

Complementa `PENDENCIAS.md` (arquivado em `_arquivo/2026-11-11/analysis/`) e `para-discussao.md`. Registrado em 11/11/2026.

## Testes que decidem a política

Usar a inadimplência projetada (`censura-agregado.md`) e o ponto de equilíbrio de ~17,5%.

| # | Pergunta | Como medir | Regra de decisão |
|---|---|---|---|
| 1 | Score 450–600 dá lucro? | projetada no grupo já limpo (sem conta apertada e com parcela ≤ 28% da renda real) | entra só se ficar abaixo de ~17,5%, considerando o atraso do próprio grupo |
| 2 | 1 restrição dá lucro? | idem; sem limpar está em 39,4% (127 clientes) | idem; senão, manter zero restrição |
| 3 | O multiplicador cal3 × 2,92 bate com a projetada? | comparar as duas por prazo nos grupos do piloto | se divergir, usar a projetada |
| 4 | A janela de 2/3 do prazo vale para 24 e 36 meses? | fração da janela em que as paradas observadas caem, por safra | se as paradas se concentrarem no começo, a correção para prazo longo fica menor |
| 5 | Reduzir o valor muda o desfecho? | sem caso na base abaixo de 30% da renda declarada (35% no piloto) | segue como hipótese; negar acima de 28% da renda real é o que está medido |

## Reprodutibilidade (conta 10% na nota técnica)

- **Cada máquina tem o banco numa porta:** Enio 5544 (fixo em `scripts-enio/base.py`), Juliano 5433, Guilherme
  5434. Proposta: toda conexão lê do `.env` (modelo em `.env.example`; `.env` fica fora do Git pelo
  `.gitignore`). `analysis/db.py` já faz assim.
- **Os scripts do Enio citam `analise/` e `../.venv/bin/python`.** No repositório a pasta é `analysis/`, e no
  Windows o Python fica em `.venv/Scripts/python`.
- **O cache do bureau (`cache-biro/`) e o cliente da API não estão no repositório.** O código final precisa ter:
  cliente com retry e espera crescente para 503, timeout, cache em disco por `id_cliente` e registro das falhas.
  O README precisa de um comando que gere `spread_final.csv` do zero.
- **O token do bureau não pode ir para o Git:** só no `.env`.

## Arquivos deste agregado

| Arquivo | O que é |
|---|---|
| `censura-agregado.md` | Três fatos da base, inadimplência projetada, ponto de equilíbrio de 17,5%, divergência sobre score e restrição |
| `padroes-agregado.md` | Padrões com a inadimplência projetada (destaques no formato do manual e tabelas completas) |
| `pendencias-agregado.md` | Este arquivo |
| `db.py`, `build_dataset.py`, `patterns.py` | Scripts que refazem os números (`out/dataset.pkl` fica fora do Git) |
| `out/patterns.csv` | Tabela completa em CSV |
