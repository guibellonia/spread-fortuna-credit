# Spread · Desafio Fortuna Crédito

Hackathon GOW 2026, 11/11/2026. `spread_final.csv` até 15h30 (checkpoint 14h15), pitch às 15h45.
Regras do desafio: `analysis/resumo-abertura.md`. Mapa das pastas: `README.md`.
Regras de Git (pull antes do push, conflitos): `.claude/CLAUDE.md`, importado abaixo.

@.claude/CLAUDE.md

## Regras gerais

- Responda em português do Brasil, de forma direta.
- Análise ou opinião vai num arquivo do autor; não reescreva o de outra pessoa. O `README.md` é do time.
- Segredos só no `.env` (fora do Git): token do bureau, senha do banco, `SUPABASE_DB_URL`, chaves de LLM.
- O repositório é de conta pessoal (`guibellonia`): colaborador só tem escrita, não existe papel de admin, e só o
  dono cadastra segredos do Actions. Hoje o único segredo é `FORTUNA_DSN` (papel `fortuna_leitura`, só leitura),
  usado pelo job de integração do `ci.yml`. Chaves do Hermes ficam no `~/.hermes/.env` de quem roda.
- Todo número com a fonte (o script ou a consulta que o produz) nas análises e nos READMEs; no site, não.

## Toda automação nova vai para o repositório

Script, workflow do GitHub Actions, job agendado, hook, tool de agente ou migração de banco:

1. fica numa pasta do repositório, não só na máquina de alguém;
2. tem no README da pasta o comando para rodar e as variáveis de `.env` que usa;
3. lê segredo só do ambiente;
4. sobe na hora: commit e push seguindo `.claude/CLAUDE.md`.

## O que o manual pede (PDFs em `material_8h/`, resumo em `analysis/resumo-abertura.md`)

- `spread_final.csv` gerado por código (`src/gerar_decisoes.py`), validado (`src/validar_csv.py`), checkpoint no
  Teams às 14h15 e entrega até 15h30. CSV editado à mão desclassifica. Valor entre R$ 500 e o menor entre o
  solicitado e R$ 30 mil.
- Painel com duas partes obrigatórias: padrões no formato "Clientes com X têm inadimplência de N%, contra M% da
  média. Afeta K clientes." e a política em passos ordenados, incluindo como define o valor.
- A IA sugere e o analista decide; a banca pode pedir a decisão de pedidos ao vivo.
- Não compartilhar código, consultas ou arquivos com outros times.

## Política proposta

- A proposta é a híbrida de `src/politica.py`: barreiras (restrição, conta apertada, parcela acima de 28% da renda
  real) e o modelo que escolhe o valor de maior ganho esperado com risco até 17,5%. `src/politica_mescla.py --comparar`
  mostra que ela rende mais que as regras e que a variante que só aperta, nos três avaliadores e fora da amostra.
- `src/politica_mescla.py` grava `saida/decisoes_mescla.csv`: a proposta (idêntica ao `saida/spread_final.csv`), as
  decisões da atual e das regras, e a faixa de risco do Daniel. É a fonte do painel e da revisão.
- Ordem para atualizar tudo: `gerar_decisoes.py` → `politica_mescla.py` → `supabase/publicar_decisoes.py` →
  `supabase/publicar_motor.py --publicar` → `site/scripts/snapshot.py` → commit e push.

## Painel (`site/`)

- Next.js 16 (App Router) com export estático, no GitHub Pages em `/dashboard/`
  (https://guibellonia.github.io/spread-fortuna-credit/dashboard/). A página do time (`index.html`) fica na raiz.
- Dados em `site/src/data/dashboard.json`, gerados por `site/scripts/snapshot.py` (banco + API do bureau).
  Atualizar: `.venv/Scripts/python site/scripts/snapshot.py`, commit do JSON e push.
- Políticas do seletor: Atual (reprodução própria, conferida contra o histórico: bate 100%), Regras do time e
  Proposta, as duas últimas lidas de `saida/decisoes_mescla.csv`. Padrões (parte 1) são calculados no histórico
  maduro (12+ meses); a política em passos (parte 2) e o comparativo saem do mesmo snapshot.
- Página Histórico (`/historico/`): a Proposta nos 10.000 pedidos do histórico contra a decisão real e o desfecho,
  com o modelo de cada trimestre treinado sem ele. Dados em `site/src/data/historico.json`, gerados por
  `site/scripts/historico.py` (precisa de `saida/hist.pkl` e do banco; não usa o bureau).
- Bureau: `site/scripts/bureau_client.py` (timeout 10 s, até 6 tentativas com espera crescente e jitter,
  10 em paralelo, 401 interrompe, cache em `data/cache/bureau/`, registro em `data/cache/bureau_chamadas.jsonl`).
- Deploy: `.github/workflows/static.yml` a cada push na `main` (build, checagem de ids, raiz + `/dashboard/`).
- Antes de subir mudança no painel: `cd site && npx tsc --noEmit && npm run build`.

Segurança do painel (não quebrar):

- Repositório e site são públicos: o JSON leva só agregados, nunca id de cliente ou pedido. O snapshot e o
  workflow param se acharem `C-…` ou `P-…`.
- O token do bureau não vai para o site nem para o CI. O navegador só testa o `GET /health`, sem token.
- CSP por página em `site/scripts/csp.mjs` (hash dos scripts inline). Origem externa nova entra em
  `connect-src` via `site/site.config.json`.
- Sem CDN em tempo de execução: fontes via `next/font`, baixadas no build.

Textos do painel são para o cliente, que não é técnico: nada de caminho de arquivo, nome de script, fórmula,
nome de modelo (GBM, AUC, árvores) ou nome de pessoa do time. A fonte de cada número fica nos READMEs, não no site.

Visual do painel: Material Design 3, tema claro, Poppins no texto e Montserrat nos números e destaques.
Sem box-shadow, poucas bordas, hover só com camada de estado (opacidade), nunca translate. Todo gráfico tem
a alternância para tabela.

## Banco

- Local: PostgreSQL 16+, banco `fortuna`, schema `hackathon` (`docker compose up -d`). Conexão pelo `.env`
  (`PG*`); o `src/` usa `FORTUNA_DSN`.
- Supabase (projeto `vjxwagiqgecsscoogxln`, São Paulo): mesmo dump no schema `hackathon`, fechado para a Data
  API (sem acesso para `anon`/`authenticated`, RLS ligado). Nunca exponha `hackathon` na API.
- Schema `painel` (exposto, só para membros logados): `decisoes` (publicadas por `supabase/publicar_decisoes.py`),
  `revisoes` (só acréscimo, carimbadas pelo banco), `bureau_consultas` (cache da Edge Function), `membros`,
  `modelo` (motor da Proposta, de `supabase/publicar_motor.py`).
  Mudança de schema = arquivo novo em `supabase/migrations/` aplicado por `supabase/aplicar_migracoes.py`.
- Edge Function `supabase/functions/bureau`: token do bureau só como segredo da função; CORS só do Pages e do
  localhost. Publicar de novo: `supabase/configurar_projeto.py` (idempotente).
- Nenhum segredo passa pelo chat ou por saída de comando: scripts leem do `.env` e não imprimem valores.
- Detalhe em `supabase/README.md`.

## Revisão (`site/src/app/revisao/`)

Página do painel com login (Supabase Auth, e-mail e senha; cadastro público fechado): fila de pedidos com
filtros, sugestão da IA com o "por que" visual (passos contra os limites e ganho de cada valor), bureau ao vivo e
registro da revisão. O Simulador (`/simulador/`, mesmo login) testa clientes novos, um a um ou em lote por CSV.
Os dois usam `site/src/lib/motor.ts`, a Proposta em TypeScript com o modelo de `painel.modelo`
(`supabase/publicar_motor.py`, que só publica se o motor der as mesmas 2.000 decisões do Python). Usa `supabaseUrl` e a chave anon de
`site/site.config.json` (pública por desenho; o RLS protege). Navegação entre páginas com `<a>` comum: o
prefetch do `next/link` dá 404 no export estático do Next 16.
