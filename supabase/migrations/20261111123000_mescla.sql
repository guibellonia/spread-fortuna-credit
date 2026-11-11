-- Mescla das políticas: cada pedido guarda a decisão da proposta (híbrida, src/politica_mescla.py) e a das
-- alternativas (atual e regras do Bilosca), para o analista ver onde divergem; e a faixa de risco do Daniel
-- (analysis/pontuacao-risco.md). Idempotente.

alter table painel.decisoes add column if not exists politica        text;
alter table painel.decisoes add column if not exists regras_decisao  text check (regras_decisao in ('APROVADO', 'NEGADO'));
alter table painel.decisoes add column if not exists regras_valor    numeric(12, 2);
alter table painel.decisoes add column if not exists pontos          smallint;
alter table painel.decisoes add column if not exists faixa           text check (faixa in ('verde', 'amarela', 'laranja', 'barreira'));
alter table painel.decisoes add column if not exists pontos_detalhe  text;

-- valor mínimo do produto (dicionário de dados): R$ 500
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
  if new.acao = 'aprovar' and (new.valor < 500 or new.valor > least(d.valor_solicitado, 30000)) then
    raise exception 'valor precisa ficar entre R$ 500 e o menor entre o solicitado (%) e R$ 30 mil', d.valor_solicitado;
  end if;
  new.analista       := auth.uid();
  new.analista_email := lower(auth.jwt() ->> 'email');
  new.decisao_ia     := d.decisao;
  new.valor_ia       := d.valor_aprovado;
  new.criado_em      := now();
  return new;
end;
$$;

drop view if exists painel.decisoes_revisadas;
create view painel.decisoes_revisadas with (security_invoker = true) as
select d.*,
       r.acao           as revisao_acao,
       r.valor          as revisao_valor,
       r.justificativa  as revisao_justificativa,
       r.analista_email as revisao_por,
       r.criado_em      as revisao_em,
       case r.acao when 'negar' then 'NEGADO' when 'aprovar' then 'APROVADO' else d.decisao end as decisao_final,
       case r.acao when 'negar' then 0 when 'aprovar' then r.valor else d.valor_aprovado end as valor_final,
       coalesce(d.atual_decisao <> d.decisao, false) as diverge_atual,
       (coalesce(d.atual_decisao <> d.decisao, false) or coalesce(d.regras_decisao <> d.decisao, false))
         as diverge_politicas
from painel.decisoes d
left join lateral (
  select * from painel.revisoes x where x.id_pedido = d.id_pedido order by x.criado_em desc, x.id desc limit 1
) r on true;
revoke all on painel.decisoes_revisadas from public, anon;
grant select on painel.decisoes_revisadas to authenticated;
