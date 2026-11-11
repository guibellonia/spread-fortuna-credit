"""Etapa 2 · Diagnóstico da base: volumes, nulos, duplicidades, integridade, período e consistências.

Só leitura (SELECT). Saída no terminal; os números entram em analysis/analise-guilherme.md.
Rodar: .venv/Scripts/python analysis/scripts-guilherme/g01_diagnostico.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import query  # noqa: E402

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)

TABELAS = ["clientes", "pedidos", "movimentacao_mensal", "parcelas", "bureau"]


def secao(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


def perfil_tabela(t):
    df = query(f"select * from hackathon.{t}")
    secao(f"{t}: {len(df):,} linhas · {df.shape[1]} colunas")
    nulos = (df.isna().mean() * 100).round(2)
    print("nulos (%):", nulos[nulos > 0].to_dict() or "nenhum")
    print("linhas duplicadas (todas as colunas):", int(df.duplicated().sum()))
    for c in ["id_cliente", "id_pedido"]:
        if c in df:
            print(f"{c} únicos: {df[c].nunique():,}")
    for c in df.columns:
        if "data" in c or c == "mes_referencia":
            s = pd.to_datetime(df[c])
            print(f"  {c}: {s.min().date() if s.notna().any() else None} → {s.max().date() if s.notna().any() else None}")
    num = df.select_dtypes(exclude="object")
    if len(num.columns):
        try:
            print(num.astype(float).describe(percentiles=[.01, .5, .99]).T.round(2).to_string())
        except Exception:
            pass
    for c in df.select_dtypes(include="object").columns:
        if df[c].nunique() <= 30:
            print(f"  {c}:", df[c].value_counts(dropna=False).to_dict())
        else:
            print(f"  {c}: {df[c].nunique()} valores distintos")
    return df


def main():
    d = {t: perfil_tabela(t) for t in TABELAS}

    secao("Integridade referencial e relacionamentos")
    print(query("""
        select
          (select count(*) from hackathon.pedidos p where not exists (select 1 from hackathon.clientes c where c.id_cliente=p.id_cliente)) pedidos_sem_cliente,
          (select count(*) from hackathon.clientes c where not exists (select 1 from hackathon.pedidos p where p.id_cliente=c.id_cliente)) clientes_sem_pedido,
          (select count(*) from (select id_cliente from hackathon.pedidos group by 1 having count(*)>1) x) clientes_com_2mais_pedidos,
          (select count(*) from hackathon.clientes c where not exists (select 1 from hackathon.movimentacao_mensal m where m.id_cliente=c.id_cliente)) clientes_sem_mov,
          (select count(*) from hackathon.pedidos p where p.tipo_base='historico' and not exists (select 1 from hackathon.bureau b where b.id_pedido=p.id_pedido)) hist_sem_bureau,
          (select count(*) from hackathon.bureau b join hackathon.pedidos p using(id_pedido) where p.tipo_base<>'historico') bureau_de_novos,
          (select count(*) from hackathon.pedidos p where p.decisao='aprovado' and not exists (select 1 from hackathon.parcelas x where x.id_pedido=p.id_pedido)) aprovados_sem_parcelas,
          (select count(distinct x.id_pedido) from hackathon.parcelas x join hackathon.pedidos p using(id_pedido) where p.decisao<>'aprovado' or p.decisao is null) parcelas_de_nao_aprovados
    """).T.to_string())

    secao("Pedidos: base × decisão × política × situação")
    print(query("""select tipo_base, decisao, politica_aplicada, situacao_final, count(*) n,
                          round(avg(valor_solicitado)) solic_medio, round(avg(valor_aprovado)) aprov_medio,
                          min(data_pedido) de, max(data_pedido) ate
                   from hackathon.pedidos group by 1,2,3,4 order by 1,2,3,4""").to_string())
    print(query("""select to_char(date_trunc('quarter', data_pedido),'YYYY-MM') tri, politica_aplicada, decisao, count(*)
                   from hackathon.pedidos where tipo_base='historico' group by 1,2,3 order by 1,2,3""").pivot_table(
        index="tri", columns=["politica_aplicada", "decisao"], values="count", fill_value=0).to_string())

    secao("Consistências de valores")
    print(query("""select
        count(*) filter (where valor_aprovado > valor_solicitado) aprov_maior_solic,
        count(*) filter (where valor_aprovado > 30000) aprov_acima_30k,
        count(*) filter (where decisao='aprovado' and valor_aprovado < valor_solicitado) aprov_reduzido,
        count(*) filter (where decisao='aprovado') aprovados,
        count(*) filter (where decisao='negado' and coalesce(valor_aprovado,0) > 0) negado_com_valor,
        count(*) filter (where valor_solicitado <= 0) solic_nao_positivo
        from hackathon.pedidos""").T.to_string())
    print("prazos:", query("select prazo_meses, count(*) from hackathon.pedidos group by 1 order by 1").set_index("prazo_meses")["count"].to_dict())

    secao("Parcelas: aderência a Price 3% a.m., quantidade = prazo, pagamento × atraso")
    print(query("""
        with p as (select id_pedido, prazo_meses, valor_aprovado,
                          round(valor_aprovado*0.03/(1-power(1.03,-prazo_meses)),2) pmt from hackathon.pedidos where decisao='aprovado'),
             x as (select id_pedido, count(*) n, max(valor_parcela) vmax, min(valor_parcela) vmin from hackathon.parcelas group by 1)
        select count(*) contratos,
               count(*) filter (where x.n <> p.prazo_meses) n_parcelas_dif_prazo,
               count(*) filter (where abs(x.vmax - p.pmt) > 0.05 or abs(x.vmin - p.pmt) > 0.05) parcela_dif_price
        from p join x using(id_pedido)""").T.to_string())
    print(query("""select
        count(*) parcelas,
        count(*) filter (where data_vencimento > '2026-09-30') vencem_apos_corte,
        count(*) filter (where data_pagamento > '2026-09-30') pagas_apos_corte,
        count(*) filter (where data_pagamento is null and data_vencimento <= '2026-09-30') vencidas_sem_pagto,
        count(*) filter (where data_pagamento is not null and dias_atraso is null) paga_sem_atraso_info,
        count(*) filter (where data_pagamento is not null and dias_atraso <> (data_pagamento - data_vencimento)) atraso_incoerente,
        count(*) filter (where data_pagamento is null and dias_atraso is not null) sem_pagto_com_atraso,
        count(*) filter (where data_pagamento < data_vencimento) pagas_antecipadas,
        max(dias_atraso) filter (where data_pagamento is not null) max_atraso_pago,
        max(dias_atraso) filter (where data_pagamento is null) max_atraso_aberto
        from hackathon.parcelas""").T.to_string())
    print("situacao_final × status das parcelas vencidas (contagem de contratos):")
    print(query("""
        with s as (select p.id_pedido, p.situacao_final,
                    count(*) filter (where x.data_vencimento<='2026-09-30') venc,
                    count(*) filter (where x.data_pagamento is null and x.data_vencimento<='2026-09-30') abertas,
                    max(x.dias_atraso) atraso_max,
                    count(*) filter (where x.dias_atraso>0) com_atraso
                   from hackathon.pedidos p join hackathon.parcelas x using(id_pedido) group by 1,2)
        select situacao_final, count(*) n, round(avg(venc),1) venc_media, sum((abertas>0)::int) com_abertas,
               min(atraso_max) min_atraso_max, max(atraso_max) max_atraso_max, sum((com_atraso>0)::int) algum_atraso
        from s group by 1 order by 1""").to_string())

    secao("Movimentação: meses por cliente e posição em relação ao pedido (vazamento?)")
    print(query("""
        select n_meses, count(*) clientes from (select id_cliente, count(*) n_meses from hackathon.movimentacao_mensal group by 1) x group by 1 order by 1
    """).to_string())
    print(query("""
        select min(diff) min_meses_antes, max(diff) max_meses_antes,
               count(*) filter (where m.mes_referencia >= date_trunc('month', p.data_pedido)) meses_no_ou_apos_mes_pedido
        from (select m.id_cliente, m.mes_referencia,
                     (extract(year from age(date_trunc('month',p.data_pedido), m.mes_referencia))*12
                      + extract(month from age(date_trunc('month',p.data_pedido), m.mes_referencia)))::int diff
              from hackathon.movimentacao_mensal m join hackathon.pedidos p using(id_cliente)) x
        join hackathon.movimentacao_mensal m using(id_cliente, mes_referencia)
        join hackathon.pedidos p using(id_cliente)
    """).T.to_string())
    print(query("""select
        count(*) filter (where entradas_salario > total_entradas + 0.01) salario_maior_entradas,
        count(*) filter (where saldo_minimo > saldo_medio + 0.01) saldo_min_maior_medio,
        count(*) filter (where total_entradas < 0 or total_saidas < 0) negativos,
        count(*) filter (where dias_cheque_especial > 0 and saldo_minimo >= 0) cheque_sem_saldo_neg,
        count(*) filter (where dias_cheque_especial = 0 and saldo_minimo < 0) saldo_neg_sem_cheque,
        count(*) filter (where entradas_salario = 0) meses_sem_salario,
        count(*) filter (where total_entradas = 0) meses_sem_entrada
        from hackathon.movimentacao_mensal""").T.to_string())

    secao("Clientes: consistências")
    print(query("""select
        count(*) filter (where renda_declarada <= 0) renda_nao_positiva,
        count(*) filter (where data_abertura_conta > (select max(data_pedido) from hackathon.pedidos)) conta_futura,
        min(data_nascimento), max(data_nascimento), min(data_abertura_conta), max(data_abertura_conta),
        count(distinct cep) ceps, count(distinct left(cep,1)) regioes, count(distinct left(cep,3)) prefixos3,
        count(distinct profissao) profissoes
        from hackathon.clientes""").T.to_string())
    print(query("""select p.tipo_base, count(*) filter (where c.data_abertura_conta > p.data_pedido) conta_aberta_apos_pedido,
                          round(avg((p.data_pedido - c.data_nascimento)/365.25)::numeric,1) idade_media,
                          min((p.data_pedido - c.data_nascimento)/365.25)::int idade_min, max((p.data_pedido - c.data_nascimento)/365.25)::int idade_max
                   from hackathon.pedidos p join hackathon.clientes c using(id_cliente) group by 1""").to_string())
    print(query("select tipo_vinculo, profissao, count(*) from hackathon.clientes group by 1,2 order by 1,3 desc").to_string())


if __name__ == "__main__":
    main()
