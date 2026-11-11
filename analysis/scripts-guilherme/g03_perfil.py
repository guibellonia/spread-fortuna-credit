"""Seções 3 e 9 · Perfil socioeconômico, cruzamentos com inadimplência, teste das variáveis demográficas
e segmentação (clusters + segmentos de oportunidade).

Entrada: out/base.pkl e out/periodos.pkl (g02_base.py). Só leitura.
Saída:   out/g03_perfil.md
Rodar:   cd analysis/scripts-guilherme && ../../.venv/Scripts/python g03_perfil.py

Inadimplência = PD de vida inteira por Kaplan-Meier no tempo relativo do contrato, com IC 95% (g_util.py).
Margem = ganho esperado por R$ aprovado pela regra do desafio (+15% em dia, +5% atraso, -60% não paga).
Todas as taxas de inadimplência são CONDICIONAIS À APROVAÇÃO (só aprovados têm desfecho).
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score, silhouette_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from g_util import carregar, fmt, resumo_grupo, tabela

warnings.filterwarnings("ignore")
AQUI = Path(__file__).resolve().parent
OUT = AQUI / "out" / "g03_perfil.md"
MD: list[str] = []


def w(s=""):
    MD.append(s)


def pct(v):
    return "" if pd.isna(v) else f"{100 * v:.1f}%"


def md(df: pd.DataFrame, floatfmt=".2f") -> str:
    return df.to_markdown(floatfmt=floatfmt)


# ---------------------------------------------------------------- faixas
def faixas(d: pd.DataFrame, cont_prof: pd.Series) -> pd.DataFrame:
    """cont_prof: contagem de clientes por profissão na base inteira (12.000), para agrupar igual em todo recorte."""
    d = d.copy()
    d["faixa_renda"] = pd.cut(d.renda_declarada, [0, 2000, 3000, 5000, 10000, np.inf],
                              labels=["<2k", "2-3k", "3-5k", "5-10k", "10k+"], right=False)
    d["faixa_idade"] = pd.cut(d.idade, [0, 25, 35, 45, 55, 65, 200],
                              labels=["<25", "25-34", "35-44", "45-54", "55-64", "65+"], right=False)
    d["tempo_conta"] = pd.cut(d.meses_conta, [-1, 12, 36, 60, 1e6], labels=["<1a", "1-3a", "3-5a", "5a+"])
    d["renda_conta_decl"] = pd.cut(d.renda_ratio, [-1, 0.6, 0.8, 0.95, 1.05, 10],
                                   labels=["<60%", "60-80%", "80-95%", "95-105%", ">105%"])
    d["faixa_valor"] = pd.cut(d.valor_solicitado, [0, 3000, 6000, 10000, 15000, 1e9],
                              labels=["<3k", "3-6k", "6-10k", "10-15k", "15k+"], right=False)
    d["faixa_score"] = pd.cut(d.score, [0, 500, 600, 700, 800, 2000],
                              labels=["<500", "500-600", "601-700", "701-800", "800+"], right=True)
    d["faixa_comp"] = pd.cut(d.comp_real_aprov.fillna(d.comp_real_solic), [-1, 0.1, 0.2, 0.28, 0.4, 100],
                             labels=["<10%", "10-20%", "20-28%", "28-40%", "40%+"])
    d["profissao_g"] = np.where(d.profissao.map(cont_prof) >= 100, d.profissao, "outras (" + d.tipo_vinculo + ")")
    return d


def politica_atual_novos(n: pd.DataFrame) -> pd.DataFrame:
    passa = (n.score > 600) & (n.renda_declarada > 2000) & (n.restricoes_ativas == 0)
    teto = 0.30 * n.renda_declarada * (1 - 1.03 ** (-n.prazo_meses.astype(float))) / 0.03
    valor = np.where(passa, np.minimum(np.minimum(n.valor_solicitado, 30000), np.floor(teto * 100) / 100), 0.0)
    return pd.DataFrame({"atual_aprova": valor > 0, "atual_valor": valor,
                         "atual_reduz": (valor > 0) & (valor < n.valor_solicitado - 0.01)}, index=n.index)


# ---------------------------------------------------------------- 1. perfil descritivo
def perfil_descritivo(hist, novos):
    w("## 1. Perfil descritivo: 10.000 históricos × 2.000 novos")
    w()
    w("Distribuição (% das linhas). `Δ p.p.` = novos − históricos. Teste qui-quadrado de homogeneidade por variável.")
    w()
    for var in ["genero", "regiao", "tipo_vinculo", "estado_civil", "faixa_idade", "faixa_renda",
                "renda_conta_decl", "tempo_conta", "faixa_valor", "prazo_meses", "faixa_score"]:
        a = hist[var].value_counts(normalize=True, dropna=False)
        b = novos[var].value_counts(normalize=True, dropna=False)
        t = pd.concat({"históricos": a, "novos": b}, axis=1).fillna(0)
        t["Δ p.p."] = 100 * (t["novos"] - t["históricos"])
        ct = pd.concat({"h": hist[var].value_counts(), "n": novos[var].value_counts()}, axis=1).fillna(0)
        p = stats.chi2_contingency(ct.values)[1]
        t[["históricos", "novos"]] = (100 * t[["históricos", "novos"]]).round(1)
        w(f"**{var}** (qui² p = {p:.3f})")
        w()
        w(md(t, ".1f"))
        w()
    num = ["renda_declarada", "renda_mov", "renda_ratio", "idade", "meses_conta", "valor_solicitado",
           "prazo_meses", "comp_real_solic", "comp_total_solic", "sai_ent", "score"]
    t = pd.DataFrame({"históricos (mediana)": hist[num].median(), "novos (mediana)": novos[num].median(),
                      "históricos (média)": hist[num].mean(), "novos (média)": novos[num].mean()})
    w("**Variáveis numéricas**")
    w()
    w(md(t))
    w()
    prof = pd.concat({"históricos": hist.profissao.value_counts(), "novos": novos.profissao.value_counts()}, axis=1)
    w(f"Profissões: {hist.profissao.nunique()} distintas; as 10 mais comuns nos históricos:")
    w()
    w(md(prof.head(10), ".0f"))
    w()


# ---------------------------------------------------------------- 2. cruzamentos com inadimplência
def aprov_rate(hist, var):
    g = hist.groupby(var, observed=True)
    at = hist[hist.politica_aplicada == "atual"].groupby(var, observed=True)
    return pd.DataFrame({"pedidos": g.size(), "taxa_aprov": g.apply(lambda x: (x.decisao == "aprovado").mean()),
                         "taxa_aprov_atual": at.apply(lambda x: (x.decisao == "aprovado").mean())})


def risco_por(ap, hist, var, titulo, min_n=30):
    t = tabela(ap, var, min_n=min_n)
    r = aprov_rate(hist, var)
    t = t.join(r, how="left")
    t["taxa_aprov"] = t["taxa_aprov"].map(pct)
    t["taxa_aprov_atual"] = t["taxa_aprov_atual"].map(pct)
    cols = ["pedidos", "taxa_aprov", "taxa_aprov_atual", "contratos", "pararam", "ingenua", "pd_vida", "ic_inf",
            "ic_sup", "p_atraso", "margem_R$", "volume", "aviso"]
    t = t[[c for c in cols if c in t.columns]]
    w(f"**{titulo}**")
    w()
    w(fmt(t))
    w()
    return t


def cruzamentos(ap, hist):
    w("## 2. Inadimplência por segmento (aprovados do histórico, PD de vida inteira por KM)")
    w()
    w("`taxa_aprov` = aprovados / pedidos no segmento (atual + piloto); `taxa_aprov_atual` = só pedidos avaliados pela "
      "política atual. `ingenua` = parou / contratos (subestima). `pd_vida` corrige a censura. "
      "`margem_R$` = ganho esperado por R$ aprovado. Média da carteira: ver linha 'todos'.")
    w()
    todos = pd.DataFrame([resumo_grupo(ap)], index=["todos"])
    w(fmt(todos[["contratos", "pararam", "ingenua", "pd_vida", "ic_inf", "ic_sup", "p_atraso", "margem_R$", "volume"]]))
    w()
    res = {}
    for var, tit in [("faixa_renda", "3.1 Faixa de renda declarada"),
                     ("profissao_g", "3.2 Profissão (profissões com < 100 clientes na base agrupadas por vínculo)"),
                     ("tipo_vinculo", "3.3 Tipo de vínculo"),
                     ("estado_civil", "3.4 Estado civil"),
                     ("regiao", "3.5a Região postal (1º dígito do CEP)"),
                     ("uf", "3.5b UF (pelo CEP; n<30 não estimado)"),
                     ("genero", "Gênero"),
                     ("faixa_idade", "Faixa etária"),
                     ("tempo_conta", "Tempo de conta (relacionamento)"),
                     ("renda_conta_decl", "Renda pela conta / renda declarada"),
                     ("faixa_score", "Score do birô")]:
        res[var] = risco_por(ap, hist, var, tit)
    return res


def capacidade(ap, hist):
    w("## 3. Renda × profissão × capacidade de pagamento; perfil × ticket; perfil × comprometimento")
    w()
    w("**3.6 Vínculo × faixa de renda: capacidade de pagamento (todos os 10.000 pedidos) e PD (aprovados, n≥50)**")
    w()
    g = hist.groupby(["tipo_vinculo", "faixa_renda"], observed=True)
    cap = pd.DataFrame({
        "pedidos": g.size(),
        "renda_conta/decl (med)": g.renda_ratio.median(),
        "sobra mensal R$ (med)": g.sobra_media.median(),
        "saídas/entradas (med)": g.sai_ent.median(),
        "parcela pedida/renda est. (med)": g.comp_real_solic.median(),
        "(parcela+outras)/renda est. (med)": g.comp_total_solic.median(),
        "taxa_aprov": g.apply(lambda x: (x.decisao == "aprovado").mean()),
    })
    pdv = {}
    for k, gg in ap.groupby(["tipo_vinculo", "faixa_renda"], observed=True):
        if len(gg) >= 50:
            r = resumo_grupo(gg)
            pdv[k] = {"aprovados": len(gg), "pd_vida": pct(r["pd_vida"]),
                      "IC95": f"{pct(r['ic_inf'])} – {pct(r['ic_sup'])}", "margem_R$": f"{r['margem_R$']:+.3f}"}
    cap.index = [f"{a} · {b}" for a, b in cap.index]
    pdv = pd.DataFrame({f"{a} · {b}": v for (a, b), v in pdv.items()}).T
    cap = cap.join(pdv)
    cap["taxa_aprov"] = cap["taxa_aprov"].map(pct)
    w(md(cap))
    w()

    w("**3.7 Gênero × comportamento de compra (10.000 pedidos históricos)**")
    w()
    g = hist.groupby("genero")
    t = pd.DataFrame({"pedidos": g.size(), "valor pedido médio": g.valor_solicitado.mean(),
                      "valor pedido mediano": g.valor_solicitado.median(), "prazo médio": g.prazo_meses.mean(),
                      "renda declarada med": g.renda_declarada.median(),
                      "valor pedido / renda (med)": g.apply(lambda x: (x.valor_solicitado / x.renda_declarada).median()),
                      "parcela/renda est. (med)": g.comp_real_solic.median(),
                      "taxa_aprov": g.apply(lambda x: (x.decisao == "aprovado").mean()).map(pct),
                      "valor aprovado médio": g.apply(lambda x: x.loc[x.decisao == "aprovado", "valor_aprovado"].mean())})
    w(md(t))
    w()
    # teste: valor pedido difere por gênero controlando renda?
    h2 = hist[hist.genero != "nao_informado"]
    kw = stats.mannwhitneyu(h2.loc[h2.genero == "feminino", "valor_solicitado"],
                            h2.loc[h2.genero == "masculino", "valor_solicitado"])
    w(f"Mann-Whitney valor pedido feminino × masculino: p = {kw.pvalue:.3f}.")
    w()

    w("**3.8 Localização × volume (históricos)**")
    w()
    g = hist.groupby("regiao")
    t = pd.DataFrame({"pedidos": g.size(), "% pedidos": 100 * g.size() / len(hist),
                      "volume pedido (R$ mi)": g.valor_solicitado.sum() / 1e6,
                      "ticket pedido médio": g.valor_solicitado.mean(),
                      "aprovados": g.apply(lambda x: (x.decisao == "aprovado").sum()),
                      "volume aprovado (R$ mi)": g.apply(lambda x: x.valor_aprovado.sum()) / 1e6,
                      "ticket aprovado médio": g.apply(lambda x: x.loc[x.decisao == "aprovado", "valor_aprovado"].mean()),
                      "renda declarada med": g.renda_declarada.median()}).sort_values("pedidos", ascending=False)
    w(md(t))
    w()
    kw = stats.kruskal(*[x.valor_solicitado.values for _, x in hist.groupby("regiao")])
    kw2 = stats.kruskal(*[(x.valor_solicitado / x.renda_declarada).values for _, x in hist.groupby("regiao")])
    w(f"Kruskal-Wallis ticket pedido entre regiões: p = {kw.pvalue:.3f}; valor pedido/renda entre regiões: p = {kw2.pvalue:.3f}.")
    w()

    w("**3.9 / 3.10 Perfil × ticket médio × comprometimento (históricos)**")
    w()
    for var in ["tipo_vinculo", "faixa_renda", "estado_civil", "faixa_idade", "genero"]:
        g = hist.groupby(var, observed=True)
        t = pd.DataFrame({"pedidos": g.size(), "ticket pedido médio": g.valor_solicitado.mean(),
                          "prazo médio": g.prazo_meses.mean(),
                          "valor/renda (med)": g.apply(lambda x: (x.valor_solicitado / x.renda_declarada).median()),
                          "parcela pedida/renda est. (med)": g.comp_real_solic.median(),
                          "% parcela pedida > 28% renda est.": 100 * g.apply(lambda x: (x.comp_real_solic > 0.28).mean()),
                          "outras parcelas/renda est. (med)": g.comp_antes.median(),
                          "(parcela+outras)/renda est. (med)": g.comp_total_solic.median(),
                          "% (parcela+outras) > 50%": 100 * g.apply(lambda x: (x.comp_total_solic > 0.5).mean()),
                          "saídas/entradas (med)": g.sai_ent.median()})
        w(f"_{var}_")
        w()
        w(md(t))
        w()


# ---------------------------------------------------------------- 3. interações
def interacoes(ap, hist):
    w("## 4. Interações entre variáveis")
    w()
    w("**Faixa de renda × vínculo × região**: com 5 × 4 × 10 = 200 células e 6.033 aprovados, quase nenhuma célula "
      "tem n ≥ 50. Abaixo as interações 2 a 2 com n ≥ 50 (PD vida; vazio = n < 50).")
    w()
    for a, b in [("faixa_renda", "tipo_vinculo"), ("regiao", "tipo_vinculo"), ("faixa_renda", "regiao"),
                 ("faixa_comp", "tipo_vinculo"), ("faixa_comp", "faixa_renda"), ("genero", "faixa_comp"),
                 ("estado_civil", "faixa_comp")]:
        rows = {}
        for (x, y), gg in ap.groupby([a, b], observed=True):
            if len(gg) >= 50:
                r = resumo_grupo(gg)
                rows.setdefault(x, {})[y] = f"{pct(r['pd_vida'])} (n={len(gg)})"
        w(f"_{a} × {b}_")
        w()
        w(pd.DataFrame(rows).T.fillna("").to_markdown())
        w()
    # árvore rasa só com variáveis de perfil (sem finanças da conta) para ver se o perfil sozinho separa risco
    w("**Árvore rasa só com perfil (renda declarada, vínculo, região, gênero, estado civil, idade, tempo de conta)** "
      "— alvo: parou, peso = fração observada da janela (censura), profundidade 3, folha ≥ 150. "
      "PD de cada folha recalculada por KM.")
    w()
    X = pd.get_dummies(ap[["tipo_vinculo", "regiao", "genero", "estado_civil"]], dtype=float)
    X["renda_declarada"] = ap.renda_declarada
    X["idade"] = ap.idade
    X["meses_conta"] = ap.meses_conta
    jan = np.ceil(ap.prazo_meses * 2 / 3)
    peso = np.where(ap.parou, 1.0, np.minimum(ap.n_decididas, jan) / jan)
    ok = ap.k_obs.fillna(0) > 0
    arv = DecisionTreeClassifier(max_depth=3, min_samples_leaf=150, random_state=0)
    arv.fit(X[ok], ap.parou[ok].astype(int), sample_weight=peso[ok])
    folha = pd.Series(arv.apply(X), index=ap.index)
    regras = regras_folhas(arv, list(X.columns))
    t = tabela(ap.assign(folha=folha.map(regras)), "folha")
    w(fmt(t[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup", "margem_R$", "aviso"]]))
    w()


def regras_folhas(arv, nomes):
    """Descreve cada folha da árvore pelo caminho de regras (substitui export_text, que só mostra a classe)."""
    tr = arv.tree_
    out = {}

    def rec(no, caminho):
        if tr.children_left[no] == -1:
            out[no] = " e ".join(caminho) or "todos"
            return
        f, th = nomes[tr.feature[no]], tr.threshold[no]
        if f.startswith(("tipo_vinculo_", "regiao_", "genero_", "estado_civil_")):
            rec(tr.children_left[no], caminho + [f"não {f}"])
            rec(tr.children_right[no], caminho + [f])
        else:
            rec(tr.children_left[no], caminho + [f"{f} ≤ {th:,.0f}"])
            rec(tr.children_right[no], caminho + [f"{f} > {th:,.0f}"])
    rec(0, [])
    return out


# ---------------------------------------------------------------- 4. teste formal das variáveis demográficas
def preparar_periodos(ap):
    per = pd.read_pickle(AQUI / "out" / "periodos.pkl")
    per = per.merge(ap.drop(columns=["prazo_meses", "data_pedido"]), on="id_pedido", how="inner")
    per["t"] = per.numero_parcela / per.prazo_meses
    per = per[per.t <= 0.7].copy()  # depois de 2/3 do prazo ninguém para: hazard 0, sem informação
    return per


def matriz(per):
    f = pd.DataFrame(index=per.index)
    f["t"] = per.t
    f["t2"] = per.t ** 2
    f["log_k"] = np.log(per.numero_parcela)
    f["comp_real"] = per.comp_real_aprov.clip(0, 1.5)
    f["comp_real_gt28"] = (per.comp_real_aprov > 0.28).astype(float)
    f["comp_total"] = per.comp_total_aprov.clip(0, 3)
    f["comp_total_gt50"] = (per.comp_total_aprov > 0.5).astype(float)
    f["log_renda"] = np.log(per.renda_declarada)
    f["renda_ratio"] = per.renda_ratio.clip(0, 1.5)
    f["renda_ratio_lt60"] = (per.renda_ratio < 0.6).astype(float)
    f["sai_ent"] = per.sai_ent.clip(0, 1.5)
    f["sai_ent_ge80"] = (per.sai_ent >= 0.8).astype(float)
    f["deficit_3m"] = per.deficit_3m
    f["cheq_meses"] = per.cheq_meses
    f["cheq_meses_ge3"] = (per.cheq_meses >= 3).astype(float)
    f["cheq_dias_media"] = per.cheq_dias_media.clip(0, 15)
    f["saldo_min_renda"] = (per.saldo_min / per.renda_declarada).clip(-3, 3)
    f["ent_cv"] = per.ent_cv.fillna(0).clip(0, 1.5)
    f["score"] = per.score / 100
    f["score_le600"] = (per.score <= 600).astype(float)
    f["restricoes"] = per.restricoes_ativas
    f["consultas"] = per.consultas_90_dias
    f["hist_bureau"] = per.meses_historico_bureau / 12
    f["hist_lt12"] = (per.meses_historico_bureau < 12).astype(float)
    f["meses_conta"] = (per.meses_conta / 12).clip(0, 15)
    f["mov_incompleta"] = (per.mov_meses < 12).astype(float)
    for p in [6, 12, 18, 24]:
        f[f"prazo_{p}"] = (per.prazo_meses == p).astype(float)
    for v in ["autonomo", "empresario", "aposentado"]:
        f[f"vinc_{v}"] = (per.tipo_vinculo == v).astype(float)
    demo = {
        "gênero": pd.get_dummies(per.genero, prefix="gen", dtype=float).drop(columns="gen_feminino"),
        "estado civil": pd.get_dummies(per.estado_civil, prefix="ec", dtype=float).drop(columns="ec_casado"),
        "região (CEP)": pd.get_dummies(per.regiao, prefix="reg", dtype=float).drop(columns="reg_SP capital/RM"),
        "idade": pd.DataFrame({"idade": per.idade / 10, "idade2": (per.idade / 10) ** 2}),
    }
    return f, demo


def ll(model, X, y):
    p = model.predict_proba(X)[:, 1]
    return -log_loss(y, p, normalize=False)


def teste_demografico(ap):
    w("## 5. Gênero, estado civil, região e idade carregam sinal DEPOIS das variáveis financeiras?")
    w()
    per = preparar_periodos(ap)
    y = per.evento_parada.values
    F, demo = matriz(per)
    sc = StandardScaler()
    base_cols = list(F.columns)
    w(f"Modelo de hazard em tempo discreto (regressão logística por parcela; {len(per):,} parcelas-período de "
      f"{per.id_pedido.nunique():,} contratos, {int(y.sum())} paradas). Controles financeiros: {len(base_cols)} termos "
      "(comprometimento com valor aprovado e degraus 28%/50%, renda, renda conta/declarada, saídas/entradas, déficit, "
      "cheque especial, saldo mínimo, volatilidade, score, restrições, consultas, histórico no birô, tempo de conta, "
      "prazo, vínculo, tempo do contrato). Teste da razão de verossimilhança (LR) para cada bloco; AUC e log-loss "
      "fora da dobra (5 dobras agrupadas por contrato).")
    w()

    def ajustar(X):
        Xs = sc.fit_transform(X)
        m = LogisticRegression(C=1e4, max_iter=5000).fit(Xs, y)
        return m, Xs

    m0, X0 = ajustar(F)
    ll0 = ll(m0, X0, y)
    gkf = GroupKFold(n_splits=5)
    grupos = per.id_pedido.values

    def oof(X, modelo="lr"):
        X = np.asarray(X, float)
        p = np.zeros(len(y))
        for tr, te in gkf.split(X, y, grupos):
            if modelo == "lr":
                s = StandardScaler().fit(X[tr])
                m = LogisticRegression(C=1e4, max_iter=5000).fit(s.transform(X[tr]), y[tr])
                p[te] = m.predict_proba(s.transform(X[te]))[:, 1]
            else:
                m = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, max_leaf_nodes=15,
                                                   min_samples_leaf=80, l2_regularization=1.0, random_state=0)
                m.fit(X[tr], y[tr])
                p[te] = m.predict_proba(X[te])[:, 1]
        return roc_auc_score(y, p), log_loss(y, p)

    auc0, lo0 = oof(F)
    linhas = [{"bloco": "só financeiro (base)", "parâmetros extras": 0, "LR χ²": "", "p-valor": "",
               "AUC fora da dobra": f"{auc0:.4f}", "log-loss fora da dobra": f"{lo0:.5f}"}]
    todos = []
    for nome, D in demo.items():
        X1 = pd.concat([F, D], axis=1)
        m1, Xs1 = ajustar(X1)
        lr = 2 * (ll(m1, Xs1, y) - ll0)
        dfree = D.shape[1]
        p = stats.chi2.sf(max(lr, 0), dfree)
        auc1, lo1 = oof(X1)
        linhas.append({"bloco": f"+ {nome}", "parâmetros extras": dfree, "LR χ²": f"{lr:.1f}", "p-valor": f"{p:.3f}",
                       "AUC fora da dobra": f"{auc1:.4f}", "log-loss fora da dobra": f"{lo1:.5f}"})
        todos.append(D)
    Xall = pd.concat([F] + todos, axis=1)
    m1, Xs1 = ajustar(Xall)
    lr = 2 * (ll(m1, Xs1, y) - ll0)
    dfree = Xall.shape[1] - F.shape[1]
    auc1, lo1 = oof(Xall)
    linhas.append({"bloco": "+ todos os demográficos", "parâmetros extras": dfree, "LR χ²": f"{lr:.1f}",
                   "p-valor": f"{stats.chi2.sf(max(lr, 0), dfree):.3f}",
                   "AUC fora da dobra": f"{auc1:.4f}", "log-loss fora da dobra": f"{lo1:.5f}"})
    w(pd.DataFrame(linhas).to_markdown(index=False))
    w()
    # coeficientes demográficos no modelo completo (escala padronizada → razão de chances por 1 dp)
    coefs = pd.Series(m1.coef_[0], index=Xall.columns)
    dem_cols = [c for c in Xall.columns if c not in F.columns]
    w("Coeficientes dos termos demográficos no modelo completo (log-odds por 1 desvio-padrão; referência: feminino, "
      "casado, SP capital/RM):")
    w()
    w(coefs[dem_cols].round(3).to_frame("coef").T.to_markdown())
    w()
    # mesma pergunta com modelo não linear
    aucg0, log0 = oof(F, "gbm")
    aucg1, log1 = oof(Xall, "gbm")
    w(f"Mesmo teste com gradient boosting (captura não linearidades): AUC fora da dobra {aucg0:.4f} → {aucg1:.4f}; "
      f"log-loss {log0:.5f} → {log1:.5f}.")
    w()
    # estratificação: dentro do perfil financeiro limpo
    limpo = ap[(ap.sai_ent < 0.8) & (ap.cheq_meses < 3) & (ap.comp_real_aprov <= 0.28) & (ap.renda_ratio >= 0.6)
               & (ap.restricoes_ativas == 0)]
    w(f"**Estratificação:** dentro do perfil financeiro limpo (saídas/entradas < 80%, < 3 meses de cheque especial, "
      f"parcela ≤ 28% da renda estimada, renda conta/declarada ≥ 60%, sem restrição; n = {len(limpo):,} aprovados), "
      "a PD de vida por grupo demográfico:")
    w()
    for var in ["genero", "estado_civil", "regiao", "faixa_idade"]:
        t = tabela(limpo, var, min_n=50)
        w(f"_{var}_")
        w()
        w(fmt(t[[c for c in ["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup", "margem_R$", "aviso", "obs"]
                 if c in t.columns]]))
        w()
    return linhas, aucg0, aucg1


# ---------------------------------------------------------------- 5. clusters e segmentos
CLUST_VARS = {
    "log_renda_est": lambda d: np.log(d.renda_est.clip(lower=300)),
    "renda_ratio": lambda d: d.renda_ratio.clip(0, 1.5),
    "parcela_pedida/renda": lambda d: d.comp_real_solic.clip(0, 1),
    "outras_parc/renda": lambda d: d.comp_antes.clip(0, 1.5),
    "saidas/entradas": lambda d: d.sai_ent.clip(0, 1.2),
    "cv_entradas": lambda d: d.ent_cv.fillna(0).clip(0, 1),
    "dias_cheque_mes": lambda d: d.cheq_dias_media.clip(0, 15),
    "meses_deficit": lambda d: d.meses_deficit,
    "score": lambda d: d.score,
    "consultas_90d": lambda d: d.consultas_90_dias,
    "log_hist_bureau": lambda d: np.log1p(d.meses_historico_bureau),
    "restricoes": lambda d: d.restricoes_ativas.clip(0, 3),
}


def clusters(hist, ap, novos):
    w("## 6. Segmentação (k-means em variáveis financeiras e de birô, padronizadas)")
    w()
    Xh = pd.DataFrame({k: f(hist) for k, f in CLUST_VARS.items()}, index=hist.index)
    Xn = pd.DataFrame({k: f(novos) for k, f in CLUST_VARS.items()}, index=novos.index)
    sc = StandardScaler().fit(Xh)
    Zh, Zn = sc.transform(Xh), sc.transform(Xn)
    rng = np.random.RandomState(0)
    amostra = rng.choice(len(Zh), 4000, replace=False)
    sil = {}
    for k in range(3, 9):
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Zh)
        sil[k] = silhouette_score(Zh[amostra], km.labels_[amostra])
    w("Silhueta por k (amostra de 4.000): " + ", ".join(f"k={k}: {s:.3f}" for k, s in sil.items()))
    w()
    k = 6  # escolhido por interpretabilidade (ver texto); silhueta acima
    km = KMeans(n_clusters=k, n_init=20, random_state=0).fit(Zh)
    hist = hist.assign(cluster=km.labels_)
    novos = novos.assign(cluster=km.predict(Zn))
    ap = ap.join(hist["cluster"])
    perfil = Xh.assign(cluster=km.labels_).groupby("cluster").median()
    perfil["log_renda_est"] = np.exp(perfil["log_renda_est"]).round(0)
    perfil = perfil.rename(columns={"log_renda_est": "renda_est (R$)"})
    perfil["log_hist_bureau"] = np.expm1(perfil["log_hist_bureau"]).round(0)
    perfil = perfil.rename(columns={"log_hist_bureau": "hist_bureau (meses)"})
    t = tabela(ap, "cluster", min_n=30)
    pa = politica_atual_novos(novos)
    extra = pd.DataFrame({
        "pedidos hist": hist.groupby("cluster").size(),
        "taxa_aprov": hist.groupby("cluster").apply(lambda x: (x.decisao == "aprovado").mean()).map(pct),
        "novos": novos.groupby("cluster").size(),
        "novos: atual aprova": pa.groupby(novos.cluster).atual_aprova.sum(),
    })
    w(f"k = {k} (escolhido por interpretabilidade; a silhueta é baixa em todos os k — os clientes formam um contínuo, "
      "não grupos naturais bem separados). Medianas por cluster:")
    w()
    w(md(perfil))
    w()
    w(fmt(extra.join(t[["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup", "p_atraso", "margem_R$", "volume",
                        "aviso"]])))
    w()
    return hist, novos


def segmentos(hist, ap, novos):
    w("## 7. Segmentos de oportunidade e de atenção (seção 9)")
    w()
    w("Definidos só com informação da data do pedido (valor PEDIDO para comprometimento, porque é o que se conhece "
      "antes de decidir). PD medida nos aprovados do histórico; contagem nos 2.000 novos com a política atual "
      "(score > 600, renda > 2.000, sem restrição, valor reduzido até a parcela caber em 30% da renda).")
    w()
    pa = politica_atual_novos(novos)

    def financas_boas(d):
        return ((d.sai_ent < 0.6) & (d.meses_deficit == 0) & (d.cheq_meses == 0) & (d.comp_real_solic <= 0.25)
                & (d.renda_ratio >= 0.6) & (d.restricoes_ativas == 0))

    def comp_excessivo(d):
        return (d.comp_real_solic > 0.28) | (d.comp_total_solic > 0.5) | (d.sai_ent >= 0.8) | (d.renda_ratio < 0.6)

    segs = {
        "S1 score ≤ 600 com finanças boas": lambda d: (d.score <= 600) & financas_boas(d),
        "S1b score ≤ 600 sem finanças boas": lambda d: (d.score <= 600) & ~financas_boas(d),
        "S2 score > 700 com comprometimento excessivo": lambda d: (d.score > 700) & comp_excessivo(d),
        "S2b score > 700 sem comprometimento excessivo": lambda d: (d.score > 700) & ~comp_excessivo(d),
        "S3 bom histórico e baixa exposição": lambda d: ((d.score > 600) & (d.restricoes_ativas == 0)
                                                         & (d.consultas_90_dias <= 1)
                                                         & (d.meses_historico_bureau >= 60)
                                                         & (d.comp_total_solic < 0.3) & (d.cheq_meses == 0)
                                                         & (d.sai_ent < 0.6)),
        "S4 aposentado/servidor com finanças boas": lambda d: (d.tipo_vinculo == "aposentado") & financas_boas(d),
        "S5 deterioração: entradas últimos 3m caíram ≥ 10%": lambda d: d.ent_tend < 0.9,
        "S5b deterioração: saídas últimos 3m subiram ≥ 10%": lambda d: d.sai_tend > 1.1,
        "S5c deterioração: cheque especial novo (só nos últimos 3m)": lambda d: ((d.cheq_meses_3m > 0)
                                                                              & (d.cheq_meses == d.cheq_meses_3m)),
        "S5d deterioração: saídas/entradas 3m ≥ 90%": lambda d: d.sai_ent_3m >= 0.9,
        "S6 atípico: renda pela conta > 105% da declarada": lambda d: d.renda_ratio > 1.05,
        "S6b atípico: entradas não salariais > 50% (assalariado)": lambda d: ((d.tipo_vinculo == "assalariado")
                                                                           & (d.sal_share < 0.5)),
        "S6c atípico: pico de saídas ≥ 2× a mediana": lambda d: d.sai_pico >= 2,
        "S7 conta < 12 meses de movimentação": lambda d: d.mov_meses < 12,
        "S8 1+ restrição ativa": lambda d: d.restricoes_ativas >= 1,
    }
    linhas = []
    for nome, f in segs.items():
        mh, ma, mn = f(hist).fillna(False), f(ap).fillna(False), f(novos).fillna(False)
        r = resumo_grupo(ap[ma]) if ma.sum() >= 30 else None
        linhas.append({
            "segmento": nome, "pedidos hist": int(mh.sum()), "taxa_aprov": pct(hist.loc[mh, "decisao"].eq("aprovado").mean()),
            "aprovados": int(ma.sum()),
            "pd_vida": pct(r["pd_vida"]) if r else "n<30",
            "IC95": f"{pct(r['ic_inf'])} – {pct(r['ic_sup'])}" if r else "",
            "margem_R$": f"{r['margem_R$']:+.3f}" if r else "",
            "aviso": r["aviso"] if r else "",
            "novos": int(mn.sum()), "novos: atual aprova": int(pa.loc[mn, "atual_aprova"].sum()),
            "novos: atual nega": int((~pa.loc[mn, "atual_aprova"]).sum()),
            "novos: atual reduz valor": int(pa.loc[mn, "atual_reduz"].sum()),
        })
    t = pd.DataFrame(linhas).set_index("segmento")
    w(t.to_markdown())
    w()
    w("S6b não tem nenhum caso: em todo assalariado as entradas de salário são a maior parte das entradas "
      "(a base não traz o padrão 'assalariado vivendo de outras entradas').")
    w()
    # sinais de deterioração/atípicos LÍQUIDOS dos filtros já conhecidos (para não contar o mesmo cliente duas vezes)
    limpo = ((ap.sai_ent < 0.8) & (ap.sai_ent_3m < 0.9) & (ap.cheq_meses < 3) & (ap.comp_real_aprov <= 0.28)
             & (ap.renda_ratio >= 0.6) & (ap.restricoes_ativas == 0))
    lim = ap[limpo]
    w(f"**Sinais líquidos:** dentro dos aprovados que já passam pelos filtros conhecidos (saídas/entradas 12m < 80% e "
      f"3m < 90%, < 3 meses de cheque especial, parcela aprovada ≤ 28% da renda estimada, renda conta/declarada ≥ 60%, "
      f"sem restrição; n = {len(lim):,}, PD {pct(resumo_grupo(lim)['pd_vida'])}), quanto cada sinal ainda acrescenta:")
    w()
    rows = {}
    for nome in ["S5 deterioração: entradas últimos 3m caíram ≥ 10%", "S5b deterioração: saídas últimos 3m subiram ≥ 10%",
                 "S5c deterioração: cheque especial novo (só nos últimos 3m)", "S6c atípico: pico de saídas ≥ 2× a mediana",
                 "S7 conta < 12 meses de movimentação"]:
        m = segs[nome](lim).fillna(False)
        for rot, mm in [("com o sinal", m), ("sem o sinal", ~m)]:
            if mm.sum() >= 30:
                r = resumo_grupo(lim[mm])
                rows[f"{nome} · {rot}"] = {"contratos": int(mm.sum()), "pararam": r["pararam"], "pd_vida": pct(r["pd_vida"]),
                                           "IC95": f"{pct(r['ic_inf'])} – {pct(r['ic_sup'])}",
                                           "margem_R$": f"{r['margem_R$']:+.3f}"}
            else:
                rows[f"{nome} · {rot}"] = {"contratos": int(mm.sum()), "pd_vida": "n<30"}
    w(pd.DataFrame(rows).T.fillna("").to_markdown())
    w()
    # renda conta/declarada < 60% é quase só de conta nova
    h = hist.assign(mm=np.select([hist.mov_meses <= 2, hist.mov_meses < 12], ["1-2 meses", "3-11 meses"], "12 meses"),
                    rr=np.where(hist.renda_ratio < 0.6, "renda conta < 60% decl.", "≥ 60%"))
    a = h.loc[ap.index]
    w("**Renda pela conta < 60% da declarada × meses de movimentação** (pedidos históricos; PD nos aprovados, n ≥ 20):")
    w()
    ct = pd.crosstab(h.mm, h.rr)
    pdt = {}
    for (x, y), gg in a.groupby(["mm", "rr"]):
        pdt[(x, y)] = f"{pct(resumo_grupo(gg)['pd_vida'])} (n={len(gg)})" if len(gg) >= 20 else f"n={len(gg)}"
    pdt = pd.Series(pdt).unstack()
    w(ct.astype(str).add(" pedidos · PD ").add(pdt.reindex_like(ct).fillna("")).to_markdown())
    w()
    w("**Score × meses de histórico no birô** (10.000 pedidos históricos): o score baixo é, na prática, cadastro novo no birô.")
    w()
    w(pd.crosstab(pd.cut(hist.meses_historico_bureau, [-1, 6, 12, 24, 60, 1e9],
                         labels=["0-6", "7-12", "13-24", "25-60", "60+"]),
                  hist.faixa_score).to_markdown())
    w()
    base = resumo_grupo(ap)
    w(f"Referência: todos os aprovados, n = {len(ap):,}, PD vida {pct(base['pd_vida'])} "
      f"[{pct(base['ic_inf'])} – {pct(base['ic_sup'])}], margem {base['margem_R$']:+.3f} por R$.")
    w()
    # S1 por política: score ≤ 600 só foi aprovado no piloto -> comparar com o piloto de score > 600
    w("**Controle de safra para S1:** score ≤ 600 só foi aprovado no piloto (out/25–mar/26). Comparação justa é com o "
      "piloto de score > 600 nas mesmas condições de finanças:")
    w()
    pil = ap[ap.politica_aplicada == "piloto"]
    rows = {}
    for nome, m in [("piloto, score ≤ 600, finanças boas", (pil.score <= 600) & financas_boas(pil)),
                    ("piloto, score > 600, finanças boas", (pil.score > 600) & financas_boas(pil)),
                    ("piloto, score ≤ 600, sem restrição", (pil.score <= 600) & (pil.restricoes_ativas == 0)),
                    ("piloto, score > 600, sem restrição", (pil.score > 600) & (pil.restricoes_ativas == 0)),
                    ("piloto, score ≤ 600, todos", pil.score <= 600),
                    ("piloto, score > 600, todos", pil.score > 600)]:
        rows[nome] = resumo_grupo(pil[m]) if m.sum() >= 30 else {"contratos": int(m.sum())}
    tt = pd.DataFrame(rows).T
    w(fmt(tt[[c for c in ["contratos", "pararam", "pd_vida", "ic_inf", "ic_sup", "p_atraso", "margem_R$", "aviso"]
              if c in tt.columns]]))
    w()
    return t


# ---------------------------------------------------------------- main
def main():
    d, hist, ap, novos = carregar()
    cont = d.profissao.value_counts()
    hist, ap, novos = faixas(hist, cont), faixas(ap, cont), faixas(novos, cont)
    w("# Perfil socioeconômico, cruzamentos e segmentação · Guilherme")
    w()
    w("Gerado por `analysis/scripts-guilherme/g03_perfil.py` a partir de `out/base.pkl` (g02_base.py). "
      "PD = inadimplência de vida inteira por Kaplan-Meier no tempo relativo do contrato, IC 95% de Greenwood. "
      "Todas as taxas de inadimplência são condicionais à aprovação (viés de seleção: só aprovados têm desfecho; "
      "score ≤ 600 e restrição só existem no piloto de out/25–mar/26).")
    w()
    w("<!-- ACHADOS -->")
    w()
    perfil_descritivo(hist, novos)
    cruzamentos(ap, hist)
    capacidade(ap, hist)
    interacoes(ap, hist)
    teste_demografico(ap)
    hist, novos = clusters(hist, ap, novos)
    segmentos(hist, ap, novos)
    txt = "\n".join(MD)
    achados = AQUI / "out" / "g03_achados.md"
    if achados.exists():
        txt = txt.replace("<!-- ACHADOS -->", achados.read_text(encoding="utf-8"))
    OUT.write_text(txt, encoding="utf-8")
    print("gravado", OUT, len(txt), "caracteres")


if __name__ == "__main__":
    main()
