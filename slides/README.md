# Slides do pitch (8 slides, 5 minutos)

- **Autor:** Enio Rocha (com Claude Code)
- **Data:** 11/11/2026
- **Uso:** abrir `index.html` no navegador; setas, espaço, Home e End navegam. Capturas 1366×720 em `capturas/`.
- **Regerar:** `python3 slides/gerar_slides.py` (sem dependências; os números estão no arquivo, cada um com a fonte no rodapé do slide).
- **Aviso:** dados fictícios do hackathon; ganho é estimativa de modelo.

## Fontes por slide

| Slide | Fonte |
|---|---|
| 1 O problema | deck das 10h30 (reduzidos: 177 pedidos, 56%, −R$ 670.271; faixas de score 600+) |
| 2 A régua | motor v2 (`projecao.py`, `ponto-ideal.json`); faixas de score em `motor2/saida/piso/celulas_hist_todos_x_limpos.csv` |
| 3 Os padrões | `motor2/saida/consultas/`; padrões de conta apertada (91%, 67 maduros) e parcela sobre renda real (~50%) |
| 4 A política | `src/politica.py` (híbrida do time) |
| 5 O resultado | números declarados pelo time (1.412 vs 1.145; R$ 385 a 500 mil; R$ 398 mil; +R$ 1,29 mi no Histórico) |
| 6 O ponto honesto | `motor2/saida/piso/seletiva.json`, `resultado_piso.json`; `analysis/scripts-guilherme/out/g06_auditoria.md:42-46` |
| 7 Ética e controle | `motor2/saida/sem_idade/resultado.json` (−R$ 2.255) |
| 8 Riscos | `motor2/saida/fora_da_curva/RESULTADO.md`; auditoria do time |

Os caminhos `motor2/` e `analise/` são do repositório de trabalho do Enio (hackathon-gow-fortuna), não deste repositório.
