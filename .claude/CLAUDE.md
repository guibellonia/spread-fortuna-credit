# Diretrizes do repositório (Claude Code e time)

## Git: sempre `pull` antes de `push`, e conferir conflitos

O time todo sobe para a `main` ao longo do dia. Antes de qualquer `git push`:

1. **Confira o que vai subir:** `git status` e `git diff --staged`.
   - Adicione arquivos pelo nome (`git add <caminho>`), não com `git add -A`, para não subir rascunho de outra pessoa.
   - Nunca suba `.env`, token do bureau, `*.dump` nem `data/cache/`.
2. **Traga o remoto:** faça o commit do seu trabalho (ou `git stash`) e rode
   `git fetch origin` e depois `git pull --rebase origin main`.
   O histórico é linear (sem commits de merge); o `--rebase` mantém assim.
3. **Verifique conflitos antes de seguir:**
   - `git status` não pode listar arquivo em conflito (`both modified`).
   - `git diff --check` e uma busca por `<<<<<<<`, `=======` e `>>>>>>>` nos arquivos tocados não podem achar nada.
   - Havendo conflito, resolva mantendo as mudanças das duas partes. Se não estiver claro qual versão vale, pare e
     pergunte a quem fez a outra mudança (`git log -p origin/main -- <arquivo>` mostra quem e o quê).
   - Nunca resolva descartando o trabalho dos outros: nada de `--ours`/`--theirs` no arquivo inteiro sem ler,
     `git checkout -- .` ou `git reset --hard`.
   - Depois de resolver: `git add <arquivo>` e `git rebase --continue`. Para desistir: `git rebase --abort`.
4. **Revalide o que o pull tocou:** se vieram mudanças em algo que você também mexeu, rode de novo o que valida
   aquilo antes de subir (ex.: `cd site && npm run build` para o painel; o validador do CSV para as decisões).
5. **Só então** `git push origin main`. Se o push for recusado (non-fast-forward), volte ao passo 2.
   **Nunca** use `git push --force` na `main`.
