# Banco e API no Supabase

Projeto `spread-fortuna` (organização Spread, região São Paulo):
https://supabase.com/dashboard/project/vjxwagiqgecsscoogxln

- **Banco compartilhado:** o dump do hackathon no schema `hackathon`, para o time todo usar o mesmo banco e para o
  teste de integração do CI (`.github/workflows/ci.yml`).
- **Painel de revisão:** a IA sugere, o analista decide. As decisões do pipeline ficam em `painel.decisoes`; o
  analista confirma, aprova com valor ou nega em
  [/dashboard/revisao/](https://guibellonia.github.io/spread-fortuna-credit/dashboard/revisao/), e cada revisão
  fica registrada (quem, quando, por quê, e qual era a decisão da IA).
- **Bureau ao vivo:** a Edge Function `bureau` consulta a API com o token guardado como segredo dela; o navegador
  nunca vê o token.

## Atualizar as decisões no painel

```
cd src && python gerar_decisoes.py && python politica_mescla.py   # proposta, regras, atual e faixa de risco
cd .. && .venv/Scripts/python supabase/publicar_decisoes.py         # saida/decisoes_mescla.csv -> painel.decisoes
```

Confere os 2.000 pedidos novos e os limites de valor numa transação só. As revisões já feitas continuam valendo.
As migrações rodam uma vez cada (registro em `painel.migracoes`).

Na revisão, o botão "Baixar CSV da IA" gera o arquivo de entrega no formato do manual a partir dessas decisões.
A opção "com as revisões do analista" troca a decisão da IA pela do analista: confirme com a organização antes de
entregar assim.

## Dar acesso a alguém

```
.venv/Scripts/python supabase/configurar_projeto.py --org-id qskawawwcfrqkbwcigzy --usuario nova@pessoa.com
```

Cria o usuário no Auth (senha inicial em `../spread-acessos-painel.txt`, fora do repositório) e inclui o e-mail
em `painel.membros`. O cadastro público está fechado: só entra quem foi incluído assim.

## Conexões (todas no `.env`, fora do Git)

| Variável | Para quê |
|---|---|
| `SUPABASE_DB_URL` | conexão de escrita (Session pooler). `src/` usa como `FORTUNA_DSN` |
| `SUPABASE_LEITOR_SENHA` | senha do papel `fortuna_leitura` (só `SELECT`). Use este papel no segredo `FORTUNA_DSN` do CI |
| `SUPABASE_DB_SENHA` | senha do banco, usada para montar a `SUPABASE_DB_URL` |
| `SUPABASE_ACCESS_TOKEN` | token da API de gerenciamento, com escopo só na organização Spread; expira em 7 dias |

URL do papel de leitura: `postgresql://fortuna_leitura.vjxwagiqgecsscoogxln:<SUPABASE_LEITOR_SENHA>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require`

## Scripts

| Script | O que faz |
|---|---|
| `configurar_projeto.py` | ponta a ponta e idempotente: projeto, conexão, restauração, migrações, membros, schema `painel` na Data API, cadastro público fechado, SSL obrigatório, segredos e publicação da função, usuários, `site/site.config.json` |
| `restaurar_banco.py` | restaura o dump numa transação, fecha `hackathon` para a API e liga o RLS; `--recriar`, `--leitor` |
| `aplicar_migracoes.py` | aplica `migrations/` e cadastra membros (`--membro`) |
| `publicar_decisoes.py` | publica o CSV de decisões em `painel.decisoes` |
| `functions/bureau/` | Edge Function do bureau ao vivo (retry, cache em `painel.bureau_consultas`, CORS só do Pages e do localhost) |

O segredo `FORTUNA_DSN` do GitHub Actions já está cadastrado com a URL do papel de leitura. Em repositório de conta
pessoal só o dono (`guibellonia`) cadastra ou troca segredos. Para o Hermes, use a mesma URL de leitura no
`FORTUNA_DSN` do `~/.hermes/config.yaml`; a senha (`SUPABASE_LEITOR_SENHA`) vai por mensagem privada, nunca no chat do time.

## Segurança

- **Dados crus fora da API:** o schema `hackathon` não é exposto; `anon` e `authenticated` não têm acesso e o RLS está ligado.
- **`painel` só para membros:** só leitura para quem está logado e na lista de membros. A revisão é só acréscimo: não
  dá para alterar nem apagar, e quem/quando/decisão da IA são preenchidos pelo banco, não pelo navegador.
- **A chave `anon` em `site/site.config.json` é pública por desenho;** quem protege os dados é o RLS.
- **TLS obrigatório no banco:** o projeto recusa conexão sem SSL, direta ou pelo pooler (`configurar_projeto.py`
  liga a exigência; ligar reinicia o banco por alguns segundos). Toda URL de conexão usa `?sslmode=require`.
- Segredos nunca em commit, chat ou código. O CI usa o papel de leitura.
- Sem `--recriar`, nada é apagado.
