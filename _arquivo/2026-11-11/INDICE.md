# Arquivo de 11/11/2026

Arquivos que nada importa nem cita como dependência, tirados do caminho. Nada foi apagado: o histórico do git guarda
tudo, e cada arquivo aqui mantém o caminho de origem dentro desta pasta (ex.: `validacao/score_direto.py` está em
`_arquivo/2026-11-11/validacao/score_direto.py`). Para voltar, `git mv` de volta.

Esta pasta NÃO é publicada no site (o `static.yml` publica só uma lista fechada). Prazo para apagar de vez:
14 dias depois do resultado do hackathon. [FALTA: data do resultado; onde buscar: Manual do Participante]

| Arquivo (origem) | O que é | Autor (git log) | Por que saiu | Data |
|---|---|---|---|---|
| `analysis/PENDENCIAS.md` | lista de pendências do início do dia | chatbot-ia-gow | obsoleto; coberto por `analysis/pendencias-agregado.md` | 11/11/2026 |
| `analysis/contexto-gpt.md` | prompt de contexto para o ChatGPT | Juliano Ferreira | coberto por `prompts/` e `hermes/contexto.md` | 11/11/2026 |
| `analysis/contexto-claude.md` | prompt de contexto para o Claude | Juliano Ferreira | idem | 11/11/2026 |
| `analysis/transcricao-abertura.md` | transcrição automática da abertura | Enio Rocha | o cabeçalho diz que tem erros; vale `analysis/resumo-abertura.md` | 11/11/2026 |
| `validacao/politicas.log` | saída de `politicas.py` com NaN (`pd_max`, `pd_media_pond`) | Juliano Ferreira | saída velha e inconsistente | 11/11/2026 |
| `validacao/experimento_hiper.log` | saída de `experimento_hiper.py` | Juliano Ferreira | sem leitor | 11/11/2026 |
| `validacao/busca_politicas.csv` | saída de `politicas.py` (linha 97) | Juliano Ferreira | só é escrito, nada lê | 11/11/2026 |
| `validacao/score_direto.log` | saída de `score_direto.py` | Juliano Ferreira | sem leitor | 11/11/2026 |
| `validacao/validar_modelo.log` | saída de `validar_modelo.py` | Juliano Ferreira | sem leitor | 11/11/2026 |
| `validacao/experimento_hiper.py` | experimento de hiperparâmetros | Juliano Ferreira | nenhum import, nenhuma citação (importa `score_direto`, que veio junto) | 11/11/2026 |
| `validacao/score_direto.py` | score direto, base do experimento | Juliano Ferreira | só `experimento_hiper.py` importava | 11/11/2026 |
| `validacao/validar_modelo.py` | validação do modelo | Juliano Ferreira | nenhum import, nenhuma citação | 11/11/2026 |
| `src/painel.py` | painel de experimentação antigo | julianoferreira-cmyk e Juliano Ferreira | nada importa; o painel em `site/` o substituiu | 11/11/2026 |

Os arquivos `validacao/*` são do Juliano (o "agente independente"): a prova do método está nos logs. Se ele quiser
manter algum, é só voltar com `git mv`.

## Ficaram onde estavam (a proposta listava, mas há dependência)

| Arquivo | Por que ficou |
|---|---|
| `validacao/politicas.py` | `validacao/final.py` faz `from politicas import ...`; final.py gera o CSV que `src/conselho.py` lê |
| `validacao/final.log` | `analysis/scripts-guilherme/g06_auditoria_cenarios.py:76` e `out/g06_auditoria.md:12` citam o caminho (arquivos do Guilherme, que o CLAUDE.md manda não reescrever) |
