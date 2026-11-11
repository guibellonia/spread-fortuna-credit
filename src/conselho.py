"""Conselho de modelos: quatro estimativas independentes de P(não paga) de vida inteira para o mesmo pedido e valor.

Membros
  1. gbm_corrigido   : gradient boosting com pesos de censura (cenarios.treinar_corrigido)
  2. sobrevivencia   : modelo de hazard por parcela + recalibração KM (validacao/tool_risco.py, agente independente)
  3. logistico       : validador explicável - regressão logística com pesos de censura em 10 variáveis
  4. tabela          : taxa projetada medida direto nos dados, por faixa de parcela/renda e saúde da conta

Veredito por pedido (ponto de equilíbrio ~17,5% de P(não paga)):
  - "aprova (consenso)"  : todos os membros abaixo do limite
  - "nega (consenso)"    : todos acima
  - "divergência"        : membros discordam -> vai para o analista de risco

Uso como tool:  avaliar_pedidos(ids, valores) -> DataFrame  |  python conselho.py  (compara e grava saida/)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from cenarios import pesos_censura, treinar_corrigido
from features import parcela_price
from modelo import SAIDA, atributos_para_valor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validacao"))
import tool_risco  # noqa: E402

LIMITE = 0.175
VARS_LOG = ["comp_aprov", "comp_real_aprov", "mov_meses_cheque", "r_saidas", "entradas_sobre_renda",
            "restricoes_ativas", "consultas_90_dias", "prazo_meses", "score", "vinc_empresario"]


def _prep(df, valor):
    a = atributos_para_valor(df, valor).copy()
    a["r_saidas"] = (df["mov_saidas_media"] / df["mov_entradas_media"].clip(lower=1)).values
    a["entradas_sobre_renda"] = df["entradas_sobre_renda"].values
    return a


def _faixa(df, valor):
    comp = parcela_price(valor, df["prazo_meses"]) / df["renda_declarada"]
    c = pd.cut(comp, [-1, 0.10, 0.20, 0.30, 99], labels=["<10%", "10-20%", "20-30%", "30%+"]).astype(str)
    apertada = ((df["mov_meses_cheque"] >= 2) | (df["mov_saidas_media"] >= 0.8 * df["mov_entradas_media"])
                | (df["restricoes_ativas"] > 0))
    return c + np.where(apertada, " | conta/bureau ruim", " | ok")


class Conselho:
    def treinar(self, hist, ate=None):
        ap = hist[hist.decisao == "aprovado"].reset_index(drop=True)
        if ate:
            ap = ap[ap.data_pedido <= ate].reset_index(drop=True)
            h = hist[hist.data_pedido <= ate]
        else:
            h = hist
        w, ap = pesos_censura(ap)
        y = (ap.situacao_final == "inadimplente").astype(int)
        ok = w > 0
        self.gbm, _ = treinar_corrigido(h) if not ate else (self._gbm_ate(h), None)
        X = _prep(ap, ap.valor_aprovado)[VARS_LOG].fillna(0)
        self.log = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.5))
        self.log.fit(X[ok], y[ok], logisticregression__sample_weight=w[ok])
        f = _faixa(ap, ap.valor_aprovado)
        t = pd.DataFrame({"f": f, "y": y, "w": w})[ok].groupby("f").agg(d=("y", "sum"), e=("w", "sum"))
        media = y[ok].sum() / w[ok].sum()
        self.tabela = ((t.d + 2 * media) / (t.e + 2)).to_dict()  # suavizada para faixas pequenas
        self.media = media
        caminho = str(SAIDA / ("sobrev_ate.joblib" if ate else "sobrev.joblib"))
        if ate or not Path(caminho).exists():  # o modelo completo é reaproveitado se já foi treinado
            tool_risco.treinar(caminho=caminho, ate_data_pedido=ate)
        self.sobrev = tool_risco.carregar_modelo(caminho)
        return self

    @staticmethod
    def _gbm_ate(h):
        from cenarios import HistGradientBoostingClassifier
        ap = h[h.decisao == "aprovado"].reset_index(drop=True)
        w, ap = pesos_censura(ap)
        y = (ap.situacao_final == "inadimplente").astype(int)
        ok = w > 0
        m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.04, max_leaf_nodes=15,
                                           min_samples_leaf=40, l2_regularization=1.0, random_state=42)
        return m.fit(atributos_para_valor(ap, ap.valor_aprovado)[ok], y[ok], sample_weight=w[ok])

    def opinar(self, df, valor, base_sobrev):
        valor = np.asarray(valor, float)
        out = pd.DataFrame({"id_pedido": df["id_pedido"].values, "valor": valor})
        out["gbm_corrigido"] = self.gbm.predict_proba(atributos_para_valor(df, valor))[:, 1]
        out["logistico"] = self.log.predict_proba(_prep(df, valor)[VARS_LOG].fillna(0))[:, 1]
        out["tabela"] = _faixa(df, valor).map(self.tabela).fillna(self.media).values
        b = base_sobrev.set_index("id_pedido").loc[out.id_pedido].reset_index()
        out["sobrevivencia"] = tool_risco.prever_df(b, valor, self.sobrev)["p_nao_paga"].values
        membros = ["gbm_corrigido", "sobrevivencia", "logistico", "tabela"]
        p = out[membros]
        out["p_mediana"] = p.median(axis=1)
        out["divergencia_pp"] = (p.max(axis=1) - p.min(axis=1)) * 100
        acima = (p > LIMITE).sum(axis=1)
        out["veredito"] = np.select([acima == 0, acima == len(membros)],
                                    ["aprova (consenso)", "nega (consenso)"], "divergência")
        out["votos_contra"] = acima
        return out


def comparar_historico(hist):
    """Fora do tempo: treina até set/2025, testa out/2025 em diante (pesos de censura)."""
    c = Conselho().treinar(hist, ate="2025-09-30")
    te = hist[(hist.decisao == "aprovado") & (hist.data_pedido > "2025-09-30")].reset_index(drop=True)
    w, te = pesos_censura(te)
    y = (te.situacao_final == "inadimplente").astype(int)
    ok = (w > 0).values
    base = tool_risco.carregar_pedidos("historico")
    op = c.opinar(te, te.valor_aprovado, base)
    linhas = []
    for mbr in ["gbm_corrigido", "sobrevivencia", "logistico", "tabela", "p_mediana"]:
        p = op[mbr].values
        auc = roc_auc_score(y[ok], p[ok], sample_weight=w[ok])
        q = pd.qcut(p[ok], 5, labels=False, duplicates="drop")
        cal = pd.DataFrame({"q": q, "p": p[ok], "y": y[ok], "w": w[ok]}).groupby("q").apply(
            lambda g: f"{g.p.mean():.0%}/{g.y.sum() / g.w.sum():.0%}", include_groups=False)
        linhas.append({"membro": mbr, "auc": round(auc, 3),
                       "previsto_medio": round(float(np.average(p[ok], weights=w[ok])), 3),
                       "projetado_real": round(float(y[ok].sum() / w[ok].sum()), 3),
                       "quintis previsto/real": " ".join(cal.values)})
    return pd.DataFrame(linhas)


def main():
    hist = pd.read_pickle(SAIDA / "hist.pkl")
    novos = pd.read_pickle(SAIDA / "novos.pkl").reset_index(drop=True)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 80)

    print("== Comparação fora do tempo (treino até set/25, teste out/25+) ==")
    comp = comparar_historico(hist)
    print(comp.to_string(index=False))
    comp.to_csv(SAIDA / "conselho_validacao.csv", index=False, encoding="utf-8")

    print("\n== Conselho nos 2.000 pedidos novos (valor = proposto pela política do agente; negados = solicitado) ==")
    c = Conselho().treinar(hist)
    prop = pd.read_csv(Path(__file__).resolve().parents[1] / "validacao" / "decisoes_PROPRIA.csv")
    v = novos[["id_pedido", "valor_solicitado"]].merge(prop, on="id_pedido")
    valor = np.where(v.valor_aprovado > 0, v.valor_aprovado, np.minimum(v.valor_solicitado, 30000))
    op = c.opinar(novos, valor, tool_risco.carregar_pedidos("novo"))
    op["decisao_agente"] = v.decisao.values
    op.round(4).to_csv(SAIDA / "conselho_novos.csv", index=False, encoding="utf-8")
    print(op.veredito.value_counts().to_string())
    print("\nP(não paga) média por membro:", op[["gbm_corrigido", "sobrevivencia", "logistico", "tabela"]].mean().round(3).to_dict())
    print("Correlação entre membros:\n", op[["gbm_corrigido", "sobrevivencia", "logistico", "tabela"]].corr().round(2))
    print("\nVeredito x decisão do agente:\n", pd.crosstab(op.veredito, op.decisao_agente))
    print("\nMaiores divergências:\n", op.sort_values("divergencia_pp", ascending=False).head(8)[
        ["id_pedido", "valor", "gbm_corrigido", "sobrevivencia", "logistico", "tabela", "decisao_agente"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
