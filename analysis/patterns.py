"""Padrões de inadimplência por grupo, corrigidos pela censura da data de corte.

Inadimplência projetada (pd_proj): a parada de pagamento acontece de forma ~uniforme até 2/3 do prazo
e nunca depois. Um contrato observado por `w` dessa janela teria visto, em média, `p * w` paradas.
Logo p = paradas / soma(w). Contratos maduros pesam 1, contratos recém-abertos pesam pouco.

Saída: analysis/out/patterns.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "out"


def pmt(valor, prazo, i=0.03):
    return valor * i / (1 - (1 + i) ** (-prazo))


def load_approved() -> pd.DataFrame:
    d = pd.read_pickle(OUT / "dataset.pkl")
    a = d[d.decisao == "aprovado"].copy()
    a["parou"] = a.parou.astype(bool)
    a["atrasou"] = a.atrasou.astype(bool)
    a["L"] = np.ceil(a.prazo_meses * 2 / 3)
    a["w"] = np.minimum(a.n_decididas, a.L) / a.L
    a["parcela_aprov"] = pmt(a.valor_aprovado, a.prazo_meses)
    a["comp_decl_aprov"] = a.parcela_aprov / a.renda_declarada
    a["comp_real"] = (a.parcela_aprov + a.parcelas_outras_instituicoes) / a.renda_real
    a["outras_renda"] = a.parcelas_outras_instituicoes / a.renda_real
    return a


def add_buckets(a: pd.DataFrame) -> dict[str, pd.Series]:
    cut = lambda s, b, l: pd.cut(s, b, labels=l, right=False)
    return {
        "Score do bureau": cut(a.score, [0, 500, 600, 700, 800, 1001], ["<500", "500-599", "600-699", "700-799", "800+"]),
        "Restrições ativas": a.restricoes_ativas.clip(upper=2).map({0: "0", 1: "1", 2: "2+"}),
        "Renda declarada": cut(a.renda_declarada, [0, 2000, 3000, 5000, 10000, 1e9], ["<2k", "2-3k", "3-5k", "5-10k", "10k+"]),
        "Renda real / declarada": cut(a.renda_ratio, [0, 0.6, 0.8, 0.95, 9], ["<60%", "60-80%", "80-95%", "95%+"]),
        "Parcela / renda declarada": cut(a.comp_decl_aprov, [0, 0.1, 0.2, 0.3, 9], ["<10%", "10-20%", "20-30%", "30%+"]),
        "Comprometimento real (parcela+outras)/renda real": cut(a.comp_real, [0, 0.2, 0.3, 0.4, 0.5, 99], ["<20%", "20-30%", "30-40%", "40-50%", "50%+"]),
        "Dívidas em outras instituições / renda real": cut(a.outras_renda, [0, 1e-9, 0.1, 0.2, 99], ["0", "<10%", "10-20%", "20%+"]),
        "Dias de cheque especial (média/mês)": cut(a.cheq_dias_media, [0, 1e-9, 1, 3, 99], ["0", "até 1", "1-3", "3+"]),
        "Meses com cheque especial (12m)": cut(a.cheq_meses, [0, 1, 3, 6, 13], ["0", "1-2", "3-5", "6+"]),
        "Saldo mínimo no período": cut(a.saldo_min, [-1e9, -2000, 0, 2000, 1e12], ["< -2k", "-2k a 0", "0-2k", "2k+"]),
        "Entradas últimos 3m vs anteriores": cut(a.ent_tend, [0, 0.7, 0.9, 1.1, 99], ["caiu 30%+", "caiu 10-30%", "estável", "subiu 10%+"]),
        "Variação das entradas (CV)": cut(a.ent_cv, [0, 0.1, 0.2, 0.4, 99], ["<10%", "10-20%", "20-40%", "40%+"]),
        "Saídas / entradas": cut(a.sai_ent, [0, 0.5, 0.8, 1.0, 99], ["<50%", "50-80%", "80-100%", "100%+"]),
        "Tempo de conta": cut(a.meses_conta, [0, 6, 12, 24, 999], ["<6m", "6-12m", "12-24m", "24m+"]),
        "Consultas ao CPF em 90 dias": a.consultas_90_dias.clip(upper=4).map({0: "0", 1: "1", 2: "2", 3: "3", 4: "4+"}),
        "Meses de histórico no bureau": cut(a.meses_historico_bureau, [0, 12, 24, 60, 9999], ["<12", "12-24", "24-60", "60+"]),
        "Tipo de vínculo": a.tipo_vinculo,
        "Prazo (meses)": a.prazo_meses.astype(str),
        "Valor aprovado": cut(a.valor_aprovado, [0, 3000, 8000, 15000, 30001], ["<3k", "3-8k", "8-15k", "15-30k"]),
        "Idade": cut(a.idade, [0, 25, 35, 50, 65, 200], ["<25", "25-34", "35-49", "50-64", "65+"]),
        "Gênero (só referência)": a.genero,
        "Estado civil (só referência)": a.estado_civil,
        "Região do CEP (1º dígito, só referência)": a.regiao_cep,
        "Política aplicada": a.politica_aplicada,
    }


def summarize(a: pd.DataFrame) -> pd.DataFrame:
    base = a.parou.sum() / a.w.sum()
    rows = []
    for var, b in add_buckets(a).items():
        g = a.assign(b=b).groupby("b", observed=True)
        for lvl, s in g:
            rows.append({
                "variavel": var, "grupo": str(lvl), "clientes": len(s),
                "inad_proj": s.parou.sum() / s.w.sum(), "paradas": int(s.parou.sum()),
                "atraso_pagadores": s[~s.parou & (s.n_decididas >= 4)].atrasou.mean(),
            })
    t = pd.DataFrame(rows)
    t["vs_media"] = t.inad_proj / base
    t.attrs["base"] = base
    return t


def main():
    a = load_approved()
    t = summarize(a)
    t.to_csv(OUT / "patterns.csv", index=False, float_format="%.4f")
    print(f"Base: {len(a)} aprovados, inadimplência projetada média {t.attrs['base']:.1%}\n")
    for var, s in t.groupby("variavel", sort=False):
        print(f"## {var}")
        print(s[["grupo", "clientes", "paradas", "inad_proj", "vs_media", "atraso_pagadores"]]
              .to_string(index=False, formatters={"inad_proj": "{:.1%}".format, "vs_media": "{:.2f}x".format,
                                                  "atraso_pagadores": "{:.0%}".format}))
        print()


if __name__ == "__main__":
    main()
