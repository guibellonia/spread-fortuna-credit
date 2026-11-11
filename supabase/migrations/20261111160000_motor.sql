-- Motor da Proposta no navegador (explicação por pedido e simulador): o modelo exportado e as entradas de cada
-- pedido, publicados por supabase/publicar_motor.py. Só para membros, como o resto do schema painel.

alter table painel.decisoes add column if not exists entrada jsonb;

create table if not exists painel.modelo (
  id           text primary key,
  conteudo     jsonb not null,
  fonte        text not null,
  publicado_em timestamptz not null default now()
);
alter table painel.modelo enable row level security;
revoke all on painel.modelo from public, anon, authenticated;
grant select on painel.modelo to authenticated;
drop policy if exists membros_leem on painel.modelo;
create policy membros_leem on painel.modelo for select to authenticated using (painel.eh_membro());
