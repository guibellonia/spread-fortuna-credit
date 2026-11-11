"""O que o modelo de risco aprendeu, e se aprendeu algo que não devia.

- importancia_permutacao: quanto a AUC fora do tempo cai ao embaralhar cada variável
- dependencia_parcial: como P(não paga) varia com uma variável, mantendo o resto fixo
- teste_sanidade:
    1. atributos sensíveis usados diretamente pelo modelo (gênero, estado civil, CEP, idade)
    2. sonda de vazamento: um classificador tenta adivinhar o atributo sensível só a partir das
       variáveis do modelo e do risco previsto. AUC ~0,5 = o modelo não carrega essa informação.
    3. disparidade: risco previsto e taxa de aprovação da política por grupo, nos pedidos novos
    4. monotonicidade: o risco deve subir com parcela/renda e com meses de saldo negativo
"""
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import cross_val_predict

from cenarios import HistGradientBoostingClassifier, pesos_censura
from modelo import ATRIBUTOS, atributos_para_valor

SENSIVEIS_NO_MODELO = {"idade": "idade (proteção etária)", "genero": "gênero", "estado_civil": "estado civil",
                       "cep": "CEP", "uf_regiao": "região do CEP"}
CFG = dict(max_iter=300, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0,
           random_state=42)


def _base(hist):
    ap = hist[hist.decisao == "aprovado"].reset_index(drop=True)
    w, ap = pesos_censura(ap)
    ok = (w > 0).values
    ap, w = ap[ok].reset_index(drop=True), w[ok].reset_index(drop=True)
    X = atributos_para_valor(ap, ap.valor_aprovado).reset_index(drop=True)
    y = (ap.situacao_final == "inadimplente").astype(int).reset_index(drop=True)
    return ap, X, y, w


def importancia_permutacao(hist, repeticoes=5):
    ap, X, y, w = _base(hist)
    tr = (ap.data_pedido <= "2025-09-30").values
    m = HistGradientBoostingClassifier(**CFG).fit(X[tr], y[tr], sample_weight=w[tr])
    auc = roc_auc_score(y[~tr], m.predict_proba(X[~tr])[:, 1], sample_weight=w[~tr])
    r = permutation_importance(m, X[~tr], y[~tr], sample_weight=w[~tr], scoring="roc_auc",
                               n_repeats=repeticoes, random_state=0)
    imp = pd.DataFrame({"variavel": X.columns, "queda_auc": r.importances_mean, "desvio": r.importances_std})
    imp = imp.sort_values("queda_auc", ascending=False)
    return {"auc_fora_do_tempo": round(auc, 3),
            "importancia": imp.round(4).to_dict("records"),
            "leitura": "queda_auc = quanto a AUC cai ao embaralhar a variável; perto de zero = o modelo não depende dela"}


def dependencia_parcial(modelo, hist, variavel, pontos=None):
    _, X, _, _ = _base(hist)
    if variavel not in X.columns:
        raise ValueError(f"variável fora do modelo. Use: {list(X.columns)}")
    amostra = X.sample(min(1500, len(X)), random_state=0)
    pontos = pontos or list(np.round(np.quantile(X[variavel], [0.02, .1, .25, .5, .75, .9, .98]), 4))
    curva = []
    for v in pontos:
        a = amostra.copy()
        a[variavel] = v
        curva.append({"valor": float(v), "p_nao_paga_media": round(float(modelo.predict_proba(a)[:, 1].mean()), 4)})
    return {"variavel": variavel, "curva": curva}


def _sonda(atributos: pd.DataFrame, alvo: pd.Series):
    """AUC de um classificador que tenta prever o atributo sensível (1 contra o resto, média ponderada)."""
    alvo = alvo.fillna("na").astype(str)
    aucs, pesos = [], []
    for g in alvo.value_counts().index:
        yb = (alvo == g).astype(int)
        if yb.sum() < 30 or (1 - yb).sum() < 30:
            continue
        p = cross_val_predict(HistGradientBoostingClassifier(max_iter=150, random_state=0), atributos, yb,
                              cv=3, method="predict_proba")[:, 1]
        aucs.append(roc_auc_score(yb, p))
        pesos.append(yb.sum())
    return round(float(np.average(aucs, weights=pesos)), 3) if aucs else None


def teste_sanidade(hist, novos, modelo, decisoes):
    ap, X, y, w = _base(hist)
    risco_hist = modelo.predict_proba(X)[:, 1]
    sem_sensivel = X.drop(columns=[c for c in SENSIVEIS_NO_MODELO if c in X.columns])

    # 1. uso direto
    usados = [SENSIVEIS_NO_MODELO[c] for c in ATRIBUTOS if c in SENSIVEIS_NO_MODELO]

    # 2. sonda de vazamento
    ap["faixa_idade"] = pd.cut(ap.idade, [0, 30, 45, 60, 200], labels=["<30", "30-45", "45-60", "60+"])
    sondas = {}
    for attr in ["genero", "estado_civil", "uf_regiao", "faixa_idade"]:
        sondas[attr] = {
            "auc_pelas_variaveis_do_modelo": _sonda(sem_sensivel, ap[attr]),
            "auc_so_pelo_risco_previsto": _sonda(pd.DataFrame({"r": risco_hist}), ap[attr]),
        }

    # 3. disparidade nos pedidos novos
    d = novos[["id_pedido", "genero", "estado_civil", "uf_regiao", "idade", "tipo_vinculo"]].merge(decisoes, on="id_pedido")
    d["faixa_idade"] = pd.cut(d.idade, [0, 30, 45, 60, 200], labels=["<30", "30-45", "45-60", "60+"]).astype(str)
    disp = {}
    for attr in ["genero", "faixa_idade", "estado_civil", "uf_regiao", "tipo_vinculo"]:
        g = d.groupby(attr).agg(pedidos=("aprova", "size"), taxa_aprovacao=("aprova", "mean"),
                                p_nao_paga_media=("p_nao_paga", "mean"))
        g = g[g.pedidos >= 20]
        disp[attr] = {"grupos": g.round(3).reset_index().to_dict("records"),
                      "razao_aprovacao_min_max": round(float(g.taxa_aprovacao.min() / g.taxa_aprovacao.max()), 3)}

    # 4. monotonicidade nas variáveis-chave
    mono = {}
    for v in ["comp_aprov", "mov_meses_cheque", "restricoes_ativas"]:
        c = dependencia_parcial(modelo, hist, v)["curva"]
        ps = [p["p_nao_paga_media"] for p in c]
        mono[v] = {"curva": c, "monotona_crescente": bool(all(b >= a - 0.005 for a, b in zip(ps, ps[1:])))}

    alertas = []
    if usados:
        alertas.append(f"o modelo usa diretamente: {', '.join(usados)}")
    for a, s in sondas.items():
        if s["auc_so_pelo_risco_previsto"] and s["auc_so_pelo_risco_previsto"] > 0.6:
            alertas.append(f"o risco previsto carrega informação de {a} (AUC {s['auc_so_pelo_risco_previsto']})")
    for a, s in disp.items():
        if a != "tipo_vinculo" and s["razao_aprovacao_min_max"] < 0.8:
            alertas.append(f"aprovação desigual por {a}: razão mín/máx {s['razao_aprovacao_min_max']} (regra dos 80%)")
    for v, s in mono.items():
        if not s["monotona_crescente"]:
            alertas.append(f"risco não cresce de forma monótona com {v}")
    return {"atributos_sensiveis_usados_diretamente": usados, "sonda_vazamento": sondas,
            "disparidade_nos_novos": disp, "monotonicidade": mono, "alertas": alertas,
            "leitura": ("sonda: AUC 0,5 = não dá para adivinhar o atributo; 1,0 = adivinha sempre. "
                        "Disparidade: regra dos 80% (taxa do grupo menos aprovado / mais aprovado >= 0,8).")}
