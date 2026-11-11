-- Schema `painel`: o que a Data API do Supabase expõe para o painel de revisão.
-- Os dados crus continuam em `hackathon`, fora da API. Idempotente: pode rodar de novo.
--
-- Acesso: só usuários logados cujo e-mail está em painel.membros (papel `authenticated`).
-- `anon` não vê nada. Revisões são só acréscimo (sem update/delete) e guardam quem, quando e por quê.

create schema if not exists painel;
revoke all on schema painel from public, anon;
grant usage on schema painel to authenticated, service_role;

-- membros do time ------------------------------------------------------------------------------------------
create table if not exists painel.membros (
  email     text primary key check (email = lower(email)),
  nome      text,
  criado_em timestamptz not null default now()
);
alter table painel.membros enable row level security;
revoke all on painel.membros from public, anon, authenticated;

create or replace function painel.eh_membro() returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (select 1 from painel.membros m where m.email = lower(coalesce(auth.jwt() ->> 'email', '')));
$$;
revoke all on function painel.eh_membro() from public, anon;
grant execute on function painel.eh_membro() to authenticated, service_role;

-- decisões da IA (publicadas por supabase/publicar_decisoes.py) --------------------------------------------
create table if not exists painel.decisoes (
  id_pedido        text primary key,
  id_cliente       text not null,
  valor_solicitado numeric(12, 2) not null,
  prazo_meses      smallint not null,
  decisao          text not null check (decisao in ('APROVADO', 'NEGADO')),
  valor_aprovado   numeric(12, 2) not null check (valor_aprovado >= 0),
  motivo           text,
  p_nao_paga       numeric(6, 4),
  ganho_esperado   numeric(12, 2),
  atual_decisao    text check (atual_decisao in ('APROVADO', 'NEGADO')),
  atual_valor      numeric(12, 2),
  fonte            text not null,
  publicado_em     timestamptz not null default now()
);
alter table painel.decisoes enable row level security;
revoke all on painel.decisoes from public, anon;
grant select on painel.decisoes to authenticated;
drop policy if exists membros_leem on painel.decisoes;
create policy membros_leem on painel.decisoes for select to authenticated using (painel.eh_membro());

-- revisões do analista (só acréscimo) -----------------------------------------------------------------------
create table if not exists painel.revisoes (
  id             bigint generated always as identity primary key,
  id_pedido      text not null references painel.decisoes (id_pedido) on delete cascade,
  acao           text not null check (acao in ('confirmar', 'aprovar', 'negar')),
  valor          numeric(12, 2),
  justificativa  text not null check (length(btrim(justificativa)) >= 5),
  decisao_ia     text not null,
  valor_ia       numeric(12, 2) not null,
  analista       uuid not null,
  analista_email text not null,
  criado_em      timestamptz not null default now(),
  check ((acao = 'aprovar') = (valor is not null))
);
create index if not exists revisoes_pedido_idx on painel.revisoes (id_pedido, criado_em desc);

-- quem, quando e a decisão da IA vêm do servidor, não do navegador
create or replace function painel.revisao_carimbo() returns trigger
language plpgsql set search_path = ''
as $$
declare
  d painel.decisoes%rowtype;
begin
  select * into d from painel.decisoes where id_pedido = new.id_pedido;
  if not found then
    raise exception 'pedido % sem decisão publicada', new.id_pedido;
  end if;
  if new.acao = 'aprovar' and (new.valor <= 0 or new.valor > least(d.valor_solicitado, 30000)) then
    raise exception 'valor precisa ser maior que zero e até o solicitado (%) e R$ 30 mil', d.valor_solicitado;
  end if;
  new.analista       := auth.uid();
  new.analista_email := lower(auth.jwt() ->> 'email');
  new.decisao_ia     := d.decisao;
  new.valor_ia       := d.valor_aprovado;
  new.criado_em      := now();
  return new;
end;
$$;
drop trigger if exists revisao_carimbo on painel.revisoes;
create trigger revisao_carimbo before insert on painel.revisoes
  for each row execute function painel.revisao_carimbo();

alter table painel.revisoes enable row level security;
revoke all on painel.revisoes from public, anon, authenticated;
grant select, insert on painel.revisoes to authenticated;
drop policy if exists membros_leem on painel.revisoes;
create policy membros_leem on painel.revisoes for select to authenticated using (painel.eh_membro());
drop policy if exists membros_revisam on painel.revisoes;
create policy membros_revisam on painel.revisoes for insert to authenticated with check (painel.eh_membro());

-- bureau consultado ao vivo (gravado pela Edge Function `bureau` com a service role) -------------------------
create table if not exists painel.bureau_consultas (
  id_cliente    text primary key,
  dados         jsonb not null,
  tentativas    smallint not null,
  ms            integer not null,
  consultado_em timestamptz not null default now()
);
alter table painel.bureau_consultas enable row level security;
revoke all on painel.bureau_consultas from public, anon, authenticated;
grant select on painel.bureau_consultas to authenticated;
grant select, insert, update on painel.bureau_consultas to service_role;
drop policy if exists membros_leem on painel.bureau_consultas;
create policy membros_leem on painel.bureau_consultas for select to authenticated using (painel.eh_membro());

-- visão para o painel: decisão da IA + última revisão + decisão final ---------------------------------------
create or replace view painel.decisoes_revisadas with (security_invoker = true) as
select d.*,
       r.acao           as revisao_acao,
       r.valor          as revisao_valor,
       r.justificativa  as revisao_justificativa,
       r.analista_email as revisao_por,
       r.criado_em      as revisao_em,
       case r.acao when 'negar' then 'NEGADO' when 'aprovar' then 'APROVADO' else d.decisao end as decisao_final,
       case r.acao when 'negar' then 0 when 'aprovar' then r.valor else d.valor_aprovado end as valor_final,
       coalesce(d.atual_decisao <> d.decisao, false) as diverge_atual
from painel.decisoes d
left join lateral (
  select * from painel.revisoes x where x.id_pedido = d.id_pedido order by x.criado_em desc, x.id desc limit 1
) r on true;
revoke all on painel.decisoes_revisadas from public, anon;
grant select on painel.decisoes_revisadas to authenticated;

grant select on painel.decisoes, painel.revisoes to service_role;
