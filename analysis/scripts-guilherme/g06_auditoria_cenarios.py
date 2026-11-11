"""Etapa 7.1 · Auditoria dos cenários A–H (src/cenarios.py) e da tabela "inadimplência projetada por grupo".

Só leitura no banco. Não grava nada em saida/ do time: o SAIDA de src/modelo.py e src/cenarios.py é redirecionado
para analysis/scripts-guilherme/out/g06_saida/. Birô dos novos: data/cache/bureau/*.json (não chama a API).

Rodar (da raiz do repositório):
  .venv/Scripts/python analysis/scripts-guilherme/g06_auditoria_cenarios.py
Saída: analysis/scripts-guilherme/out/g06_auditoria.md (+ g06_*.csv)

Passos:
  1. reproduz A–H com o código do src (mesmos modelos, mesmos parâmetros)
  2. reavalia os mesmos conjuntos de decisões com avaliadores independentes:
       - KM por célula (sem modelo): PD de vida inteira e P(em dia) dos aprovados históricos com o mesmo perfil
       - modelo de sobrevivência de validacao/tool_risco.py (hazard por parcela + recalibração por KM)
  3. reduzidos pela regra dos 30% (histórico)
  4. sobreposição dos filtros extras de D/F
  5. tabela 19,4% / 7,7% / 8,0%
  6. backtest fora do tempo (censura simulada em 30/09/2025)
"""
import json
import os
import sys
import types
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[1]
OUT = AQUI / "out"
SAIDA_G06 = OUT / "g06_saida"
SAIDA_G06.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- conexão: shim do módulo `db` usado pelo src/ e validacao/
from dotenv import load_dotenv  # noqa: E402
import psycopg  # noqa: E402

load_dotenv(ROOT / ".env")


def _consulta(sql, params=None):
    with psycopg.connect() as conn:  # PG* do .env
        conn.read_only = True
        cur = conn.execute(sql, params)
        cols = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


_db = types.ModuleType("db")
_db.consulta = _consulta
_db.q = _consulta
_db.query = _consulta
sys.modules["db"] = _db

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "validacao"))
sys.path.insert(2, str(AQUI))

import features as F  # noqa: E402
import modelo as M  # noqa: E402
import politica as P  # noqa: E402
import cenarios as C  # noqa: E402
from g_util import km_vida, km_em_dia, proj_w, resumo_grupo  # noqa: E402

M.SAIDA = SAIDA_G06
C.SAIDA = SAIDA_G06

R_ATRASO = C.R_ATRASO

RESUMO = """## Resumo da auditoria (números desta execução; detalhe e fonte nas seções 1–6)

1. **Reprodução:** os 8 cenários batem com o código de `src/cenarios.py` (aprovados e volume exatos; resultado ±R$ 1 mil).
   O `validacao/final.log` (A = R$ 193 mil, B = 1.559) é outra conta: o resultado de A lá é idêntico (193.174,25) ao que o
   avaliador `tool_risco` dá aqui; o B de lá é outra seleção.
2. **Auto-avaliação infla o resultado.** O modelo corrigido escolhe E–H e também os mede. Nos aprovados de G ele prevê
   PD 5,9%; os avaliadores independentes dão 8,1% (`tool_risco`) e 8,5% (KM por célula). Resultado de G: 859 → 669–694 mil
   (−19% a −22%). O **ganho sobre A** cai menos (568 → 501–526 mil, −7% a −12%) porque o resultado de A também estava
   superestimado (292 → 143–193 mil).
3. **Cada modelo prefere a própria seleção.** G − B: +42 mil pelo corrigido, −52 mil pelo modelo antigo, +6 / +3 mil pelos
   neutros. E − C: +34 mil, −40 mil, +10 / +6 mil. As diferenças B×G×H e C×E estão dentro do viés do avaliador.
   O que é robusto em todos os avaliadores: toda proposta ganha da atual (~350–650 mil) e "sem corte de score" (B, G)
   supera "score > 600" (C, E) em ~130–140 mil nos avaliadores neutros.
4. **Onde está o ganho:** a política atual reduz 61 pedidos novos para parcela = 30% da renda. PD prevista nesses 61:
   52% (corrigido) / 55% (KM). No histórico, os 347 reduzidos têm PD de vida 61,2% [IC 54,8–67,5] e margem −0,32 por R$.
   Só esses 61 tiram 192–213 mil do resultado de A: ~35–40% do ganho de qualquer proposta vem de não emprestar a eles.
5. **Premissas não equivalentes:** B, C e D são escolhidos pelo modelo antigo (rótulo ingênuo, treino até mar/26, risco ≤ 20%)
   e avaliados pelo corrigido; E–H são escolhidos e avaliados pelo corrigido. Todos são vida inteira, mas com 23% fixo de
   pagadores com atraso para qualquer pedido (otimista nos grupos de risco, onde chega a ~50%). O corte de 17,5% está na
   escala do modelo corrigido, que é calibrado no estimador w-90d, e esse estimador subestima (item 7).
6. **D ≈ C e F ≈ E:** os filtros extras pegam 171 novos; 170 já eram negados em C e E (122 restrição, 21 por 2+ meses com
   saldo negativo, 18 score, 9 risco). Sobra 1. Os filtros são redundantes com a v2, não inúteis: na política atual cortariam 31.
7. **Tabela 19,4% / 7,7% / 8,0%:** reproduzida com o estimador `pesos_censura` (evento = 90+ dias; peso = parcelas vencidas
   até o corte / janela). 278 = todos os aprovados com score ≤ 600, **100% do piloto** (out/25–mar/26, mediana jan/26);
   4.833 inclui 208 contratos sem parcela vencida (peso 0): n efetivo 4.625. Esse estimador mistura evento de 90 dias com
   parcelas vencidas há menos de 90 dias e **subestima**: com KM e regra de 61 dias, 19,4% → **25,7%** [17,1–34,2];
   7,7% → **9,0%** [3,2–14,7]; 8,0% → **8,4%** [7,4–9,4]. A queda vem de três filtros: parcela ≤ 20% da renda
   (−26 contratos / −12 paradas), restrição (−28 / −7) e ≤ 1 mês negativo (−11 / −8); os filtros extras tiram 1 / 1.
   Os mesmos filtros levam score > 600 de 15,1% para 8,4%: o score baixo não "melhora", os filtros tiram o mesmo tipo de
   risco dos dois grupos. Diferença pós-filtro (≤ 600 − > 600) = +0,5 p.p., IC95 [−4,4; +6,7]; contra > 600 do próprio
   piloto, +1,1 [−4,6; +7,5]. Indistinguível, mas com 212 contratos e 13 paradas o limite superior (~15%) fica perto do
   equilíbrio (~17,5%): é "consistente com não haver diferença", não "provado igual".
8. **Backtest fora do tempo** (treino até 30/09/25; teste = aprovados de out/25–mar/26; valor ≤ o aprovado na época):
   no horizonte observado, C ganha +180 mil [IC 116; 248] e G +217 mil [131; 297] sobre A. Projetando a vida inteira por KM,
   C +125 mil [31; 239] e G +61 mil [−94; +189]: **G não é estatisticamente melhor que A na vida inteira** nesse teste.
   O modelo treinado em 30/09/25 previa PD 3,1% para os aprovados de G; o KM observado é 16,4%. Mal calibrado, o corte de
   risco não morde e G vira "só filtros". 264 aprovações de G no teste não têm desfecho (negados na época): viés de seleção.
   O piloto como foi rodado (todos os aprovados históricos) perde −306 mil [−494; −150] contra A no mesmo teste.

**O que corrigir na conta do time**
- Apresentar o resultado com avaliador independente e em faixa: ganho de G sobre A ≈ **R$ 500–570 mil** (não 568 cravado);
  resultado absoluto ≈ 670–860 mil.
- Calibrar o modelo corrigido contra KM com regra de 61 dias (como `tool_risco` já faz, isotônica) antes de usar o corte de
  17,5%; ou usar `tool_risco` como modelo de decisão. Unificar o rótulo de calote (61 dias) em todas as contas.
- Usar P(atraso) por pedido (ex.: `tool_risco`) em vez de 23% fixo.
- Não vender B, G e H como diferentes entre si: a diferença é menor que o viés do avaliador. Escolher por robustez.
- Trocar a tabela 19,4 / 7,7 / 8,0 por KM 61 dias com IC (25,7 / 9,0 / 8,4) e n efetivo; dizer que ≤ 600 é só piloto.
- Tirar D e F da comparação, ou explicar que os filtros já estão contidos na v2.
- No pitch: o maior item do ganho é não reduzir para 30% quem não cabe (61 pedidos, ~200 mil).
"""

LINHAS_MD: list[str] = []


def md(s=""):
    LINHAS_MD.append(s)
    print(s)


def tab(df: pd.DataFrame, floatfmt="{:,.0f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join([str(df.index.name or "")] + [str(c) for c in cols]) + " |",
           "|" + "---|" * (len(cols) + 1)]
    for i, r in df.iterrows():
        cel = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cel.append("" if pd.isna(v) else floatfmt.format(v))
            else:
                cel.append(str(v))
        out.append("| " + " | ".join([str(i)] + cel) + " |")
    return "\n".join(out)


def pct(v):
    return "" if pd.isna(v) else f"{100 * v:.1f}%"


# ---------------------------------------------------------------- 1. bases do src + reprodução A–H
def bureau_cache() -> pd.DataFrame:
    linhas = [json.loads(f.read_text(encoding="utf-8")) for f in (ROOT / "data/cache/bureau").glob("*.json")]
    b = pd.DataFrame(linhas)
    b["parcelas_outras_instituicoes"] = b["parcelas_outras_instituicoes"].astype(float)
    return b


def bases_src():
    cache = SAIDA_G06 / "hist.pkl"
    if cache.exists() and (SAIDA_G06 / "novos.pkl").exists():
        return pd.read_pickle(cache), pd.read_pickle(SAIDA_G06 / "novos.pkl")
    base, mov = F.pedidos_base(), F.movimentacao_agregada()
    hist = F.montar(base[base.tipo_base == "historico"], mov, F.bureau_historico())
    novos = F.montar(base[base.tipo_base == "novo"], mov, bureau_cache(), chave_bureau="id_cliente")
    assert novos["score"].notna().all()
    hist.to_pickle(cache)
    novos.to_pickle(SAIDA_G06 / "novos.pkl")
    return hist, novos


def cenarios_src(hist, x):
    """Mesma montagem de src/cenarios.py::main, devolvendo as decisões de cada cenário."""
    meta_antigo = M.treinar(hist)  # grava em out/g06_saida (redirecionado)
    antigo = M.carregar()
    m, meta = C.treinar_corrigido(hist)
    x = x.copy()
    x["r_saidas"] = x["mov_saidas_media"] / x["mov_entradas_media"]
    extra = (x["r_saidas"] >= 0.8) | (x["entradas_sobre_renda"] < 0.6)

    def com_filtros(dec):
        dec = dec.copy()
        bloq = dec["id_pedido"].isin(x.loc[extra, "id_pedido"])
        dec.loc[bloq, ["aprova", "valor"]] = [False, 0.0]
        return dec

    W = C.m_wrap(m)
    cen = {
        "A": P.politica_atual(x),
        "B": P.politica_proposta(x, antigo, {"min_score": 0, "risco_max": 0.20}),
        "C": P.politica_proposta(x, antigo, {"min_score": 600, "risco_max": 0.20}),
    }
    cen["D"] = com_filtros(cen["C"])
    cen["E"] = P.politica_proposta(x, W, {"risco_max": 0.175, "min_score": 600})
    cen["F"] = com_filtros(cen["E"])
    cen["G"] = P.politica_proposta(x, W, {"risco_max": 0.175, "min_score": 0})
    cen["H"] = P.politica_proposta(x, W, {"risco_max": 0.175, "min_score": 499})
    return cen, m, antigo, meta, meta_antigo, x, extra


# ---------------------------------------------------------------- 2a. avaliador independente: KM por célula
def celulas(df: pd.DataFrame, valor) -> pd.DataFrame:
    """Perfil de risco em poucas variáveis, calculado com o VALOR em avaliação (parcela depende do valor)."""
    v = np.asarray(valor, float)
    parc = F.parcela_price(v, df["prazo_meses"])
    renda_real = np.minimum(df["renda_declarada"], df["mov_entradas_media"].clip(lower=1))
    comp = parc / renda_real
    r_sai = df["mov_saidas_media"] / df["mov_entradas_media"]
    out = pd.DataFrame(index=df.index)
    out["aperto"] = ((r_sai >= 0.8) | (df["mov_meses_cheque"].fillna(0) >= 2)).astype(int)
    out["restr"] = (df["restricoes_ativas"] > 0).astype(int)
    out["comp"] = pd.cut(comp, [-1, 0.10, 0.20, 0.28, 0.35, 99], labels=["<10", "10-20", "20-28", "28-35", "35+"]).astype(str)
    out["score"] = pd.cut(df["score"], [-1, 600, 2000], labels=["<=600", ">600"]).astype(str)
    out["prazo"] = np.where(df["prazo_meses"] <= 6, "6", np.where(df["prazo_meses"] <= 12, "12", "18+"))
    return out


NIVEIS = [["aperto", "restr", "comp", "score", "prazo"], ["aperto", "restr", "comp", "score"],
          ["aperto", "restr", "comp"], ["aperto", "comp"], ["aperto"]]


class AvaliadorKM:
    """PD e P(em dia) de vida inteira por célula, nos aprovados históricos (KM relativo, g_util).
    Célula com < MIN contratos cai para a próxima mais grossa."""
    MIN = 60

    def __init__(self, ap_hist: pd.DataFrame, ap_out: pd.DataFrame):
        cel = celulas(ap_hist, ap_hist["valor_aprovado"])
        self.ap = pd.concat([ap_out.reset_index(drop=True), cel.reset_index(drop=True)], axis=1)
        self.tab = {}
        for niv in NIVEIS:
            t = {}
            for k, g in self.ap.groupby(niv):
                if len(g) >= self.MIN:
                    pdv, _, _ = km_vida(g)
                    t[k if isinstance(k, tuple) else (k,)] = (pdv, km_em_dia(g), len(g))
            self.tab[tuple(niv)] = t

    def prever(self, df: pd.DataFrame, valor) -> np.ndarray:
        cel = celulas(df, valor)
        res = np.full((len(df), 2), np.nan)
        for i, (_, r) in enumerate(cel.iterrows()):
            for niv in NIVEIS:
                k = tuple(r[c] for c in niv)
                if k in self.tab[tuple(niv)]:
                    pdv, emdia, _ = self.tab[tuple(niv)][k]
                    res[i] = (pdv, min(emdia, 1 - pdv))
                    break
        return res  # colunas: p_nao_paga, p_em_dia


def avaliar_probs(valor, p_d, p_ok):
    p_l = np.clip(1 - p_d - p_ok, 0, 1)
    g = 0.15 * p_ok + 0.05 * p_l - 0.60 * p_d
    return float((g * valor).sum()), float((p_d * valor).sum() / valor.sum())


def main():
    hist, x = bases_src()
    cen, m, antigo, meta, meta_antigo, x, extra = cenarios_src(hist, x)
    md("# Auditoria dos cenários A–H e da tabela de inadimplência por grupo")
    md("")
    md("Script: `analysis/scripts-guilherme/g06_auditoria_cenarios.py` (só leitura; reproduz `src/cenarios.py` com "
       "as saídas redirecionadas para `out/g06_saida/`). Birô dos novos: cache `data/cache/bureau/` (2.000/2.000).")
    md("")
    md(f"Modelo 'antigo' (3 classes, `src/modelo.py`): {meta_antigo}. Modelo corrigido (`src/cenarios.py`): {meta}.")
    md("")

    md(RESUMO)
    md("")
    # --- avaliação original (modelo corrigido, como src/cenarios.py)
    ref = pd.DataFrame({
        "A": (1145, 8.86e6, 292e3), "B": (1550, 10.16e6, 817e3), "C": (1209, 7.97e6, 645e3), "D": (1208, 7.96e6, 645e3),
        "E": (1192, 8.09e6, 679e3), "F": (1191, 8.08e6, 679e3), "G": (1527, 10.22e6, 859e3), "H": (1435, 9.59e6, 800e3),
    }, index=["aprov_prompt", "vol_prompt", "res_prompt"]).T

    # avaliador independente 2: tool_risco (hazard), carregado sob demanda
    import tool_risco as T
    caminho_tr = str(SAIDA_G06 / "tool_risco_full.joblib")
    if not Path(caminho_tr).exists():
        T.treinar(caminho_tr)
    mod_tr = T.carregar_modelo(caminho_tr)
    ped_novos = T.carregar_pedidos("novo")
    bc = bureau_cache().set_index("id_cliente")
    for c in ["score", "restricoes_ativas", "parcelas_outras_instituicoes", "consultas_90_dias", "meses_historico_bureau"]:
        ped_novos[c] = ped_novos["id_cliente"].map(bc[c]).astype(float)
    ped_novos["outras_renda"] = ped_novos["parcelas_outras_instituicoes"] / ped_novos["renda"]
    ped_novos = ped_novos.set_index("id_pedido")

    ap_hist = hist[hist.decisao == "aprovado"].reset_index(drop=True)
    from g_util import carregar as gcar
    _, _, ap_g, _ = gcar()
    ap_out = ap_hist[["id_pedido"]].merge(ap_g[["id_pedido", "parou", "k_parada", "k_obs", "prazo_meses", "n_decididas",
                                                "k_1o_atraso", "valor_aprovado"]], on="id_pedido", how="left")
    km_av = AvaliadorKM(ap_hist, ap_out.drop(columns=["id_pedido"]))

    linhas = []
    for nome, dec in cen.items():
        assert dec["id_pedido"].is_unique
        d = dec.merge(x, on="id_pedido")
        d = d[d["valor"] > 0].reset_index(drop=True)
        v = d["valor"].to_numpy(float)
        r0 = C.resultado(dec, x, m)
        r_pess = C.resultado(dec, x, m, 1.2)["resultado"]
        # avaliador KM por célula
        pk = km_av.prever(d, v)
        res_km, pd_km = avaliar_probs(v, pk[:, 0], pk[:, 1])
        # avaliador tool_risco (vida inteira, recalibrado por KM)
        pt = T.prever_df(ped_novos.loc[d["id_pedido"]].reset_index(), v, mod_tr)
        res_tr, pd_tr = avaliar_probs(v, pt["p_nao_paga"].to_numpy(), pt["p_em_dia"].to_numpy())
        # modelo antigo (3 classes) como avaliador
        pa = M.probabilidades(antigo, d, v)
        res_ant = float(((pa @ M.GANHO) * v).sum())
        linhas.append({"cenario": nome, "aprovados": len(d), "volume": v.sum(), "ticket": v.mean(),
                       "res_corrigido": r0["resultado"], "pd_corrigido": r0["inad_esperada"],
                       "res_corrigido_pess": r_pess, "res_antigo": res_ant,
                       "res_km_celula": res_km, "pd_km_celula": pd_km,
                       "res_tool_risco": res_tr, "pd_tool_risco": pd_tr})
    R = pd.DataFrame(linhas).set_index("cenario")
    for c in ["res_corrigido", "res_corrigido_pess", "res_antigo", "res_km_celula", "res_tool_risco"]:
        R["ganho_" + c[4:]] = R[c] - R.loc["A", c]
    R = R.join(ref)
    R.to_csv(OUT / "g06_cenarios.csv", encoding="utf-8")
    pd.to_pickle({"cen": cen, "R": R}, SAIDA_G06 / "cenarios.pkl")

    md("## 1. Reprodução dos cenários (avaliador original: modelo corrigido de `src/cenarios.py`)")
    md("")
    t1 = pd.DataFrame({
        "aprov. prompt": R["aprov_prompt"], "aprov. reproduzido": R["aprovados"],
        "volume prompt (mi)": R["vol_prompt"] / 1e6, "volume reprod. (mi)": R["volume"] / 1e6,
        "resultado prompt (mil)": R["res_prompt"] / 1e3, "resultado reprod. (mil)": R["res_corrigido"] / 1e3,
        "ganho reprod. (mil)": R["ganho_corrigido"] / 1e3, "PD média reprod.": R["pd_corrigido"].map(pct),
    })
    t1.index.name = "cenário"
    md(tab(t1, "{:,.2f}"))
    md("")
    md("## 2. Mesmas decisões, avaliadores diferentes (R$ mil, vida inteira, regra +15/+5/−60)")
    md("")
    t2 = pd.DataFrame({
        "corrigido (original)": R["res_corrigido"] / 1e3, "ganho": R["ganho_corrigido"] / 1e3,
        "corrigido +20% risco": R["res_corrigido_pess"] / 1e3, "ganho ": R["ganho_corrigido_pess"] / 1e3,
        "KM por célula": R["res_km_celula"] / 1e3, "ganho  ": R["ganho_km_celula"] / 1e3,
        "PD KM": R["pd_km_celula"].map(pct),
        "tool_risco (hazard)": R["res_tool_risco"] / 1e3, "ganho   ": R["ganho_tool_risco"] / 1e3,
        "PD tool": R["pd_tool_risco"].map(pct),
        "modelo antigo (3 cl.)": R["res_antigo"] / 1e3, "ganho    ": R["ganho_antigo"] / 1e3,
    })
    t2.index.name = "cenário"
    md(tab(t2, "{:,.0f}"))
    md("")
    print(R.round(3).to_string())

    parte3_reduzidos(hist, x, cen, m, km_av)
    parte4_filtros(x, cen, extra)
    parte5_tabela_grupos()
    parte6_backtest(hist)
    (OUT / "g06_auditoria.md").write_text("\n".join(LINHAS_MD) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 3. reduzidos pela regra dos 30%
def parte3_reduzidos(hist, x, cen, m, km_av):
    from g_util import carregar as gcar
    _, _, ap, _ = gcar()
    md("## 3. Reduzidos pela regra dos 30% (política atual)")
    md("")
    lin = {}
    for nome, g in [("reduzidos (histórico)", ap[ap.reduzido]), ("não reduzidos, política atual", ap[~ap.reduzido & (ap.politica_aplicada == "atual")]),
                    ("todos os aprovados", ap)]:
        r = resumo_grupo(g)
        lin[nome] = {"contratos": r["contratos"], "pararam": r["pararam"], "ingênua": pct(r["ingenua"]),
                     "PD vida (KM)": pct(r["pd_vida"]), "IC95": f"{pct(r['ic_inf'])} – {pct(r['ic_sup'])}",
                     "P(em dia)": pct(r["p_em_dia"]), "margem por R$": f"{r['margem_R$']:+.3f}"}
    t = pd.DataFrame(lin).T
    t.index.name = "grupo"
    md(tab(t))
    md("")
    # política atual nos novos: quem ela reduz
    a = cen["A"].merge(x, on="id_pedido")
    a = a[a.valor > 0].reset_index(drop=True)
    red = a.valor < a.valor_solicitado - 0.01
    v = a.valor.to_numpy(float)
    p_m = m.predict_proba(M.atributos_para_valor(a, v))[:, 1]
    pk = km_av.prever(a, v)
    md(f"Nos 2.000 novos, a política atual aprova {len(a)} e **reduz o valor de {int(red.sum())}** (parcela = 30% da renda declarada). "
       f"PD média atribuída a esses reduzidos: modelo corrigido **{pct(p_m[red].mean())}**, KM por célula **{pct(pk[red.to_numpy(), 0].mean())}**; "
       f"nos não reduzidos: {pct(p_m[~red].mean())} vs {pct(pk[~red.to_numpy(), 0].mean())}. "
       f"Resultado de A só nos reduzidos: modelo corrigido R$ {avaliar_probs(v[red], p_m[red], (1 - p_m[red]) * (1 - R_ATRASO))[0] / 1e3:,.0f} mil; "
       f"KM por célula R$ {avaliar_probs(v[red], pk[red.to_numpy(), 0], pk[red.to_numpy(), 1])[0] / 1e3:,.0f} mil.")
    md("")


# ---------------------------------------------------------------- 4. por que D≈C e F≈E
def parte4_filtros(x, cen, extra):
    md("## 4. Por que D ≈ C e F ≈ E (filtros de saídas e renda real)")
    md("")
    xx = x.set_index("id_pedido")
    f1 = xx["r_saidas"] >= 0.8
    f2 = xx["entradas_sobre_renda"] < 0.6
    ex = xx.index[extra.values]
    lin = {}
    for nome, base in [("C", cen["C"]), ("E", cen["E"]), ("G", cen["G"]), ("A", cen["A"])]:
        b = base.set_index("id_pedido")
        ja_neg = ~b.loc[ex, "aprova"]
        motivos = b.loc[ex[ja_neg.values], "motivo"].value_counts().to_dict() if "motivo" in b else {}
        lin[nome] = {"pegos pelos filtros extras": len(ex), "já negados": int(ja_neg.sum()),
                     "ainda aprovados (D/F removem)": int((~ja_neg).sum()), "motivo da negação já existente": str(motivos)}
    t = pd.DataFrame(lin).T
    t.index.name = "política base"
    md(f"Nos novos: saídas ≥ 80% das entradas = {int(f1.sum())}; renda real < 60% da declarada = {int(f2.sum())}; "
       f"união = {len(ex)} pedidos.")
    md("")
    md(tab(t))
    md("")


# ---------------------------------------------------------------- 5. tabela 19,4% / 7,7% / 8,0%
def _w90(ap, venc):
    a = ap.merge(venc, on="id_pedido", how="left")
    jan = np.ceil(a.prazo_meses * 2 / 3)
    w = np.where(a.situacao_final == "inadimplente", 1.0, (np.minimum(a.venc.fillna(0), jan) / jan).clip(0, 1))
    y = (a.situacao_final == "inadimplente").astype(int).to_numpy()
    ok = w > 0
    return (y[ok].sum() / w[ok].sum()) if ok.any() else np.nan, int(ok.sum())


def _boot_diff(g1, g2, B=500, seed=7):
    rng = np.random.default_rng(seed)
    a, b = g1.reset_index(drop=True), g2.reset_index(drop=True)
    diffs = []
    for _ in range(B):
        s1 = a.iloc[rng.integers(0, len(a), len(a))]
        s2 = b.iloc[rng.integers(0, len(b), len(b))]
        diffs.append(km_vida(s1)[0] - km_vida(s2)[0])
    diffs = np.array(diffs)
    return np.percentile(diffs, 2.5), np.percentile(diffs, 97.5)


def parte5_tabela_grupos():
    from g_util import carregar as gcar
    _, _, ap, _ = gcar()
    venc = _consulta("select id_pedido, count(*) filter (where data_vencimento <= '2026-09-30') venc from hackathon.parcelas group by 1")
    s6 = ap.score <= 600
    r0 = ap.restricoes_ativas == 0
    n1 = ap.cheq_meses <= 1  # = meses com saldo mínimo negativo (dias de cheque > 0 ⇔ saldo mínimo < 0 na base)
    c20 = ap.parcela_aprov / ap.renda_declarada <= 0.20 + 1e-9
    ex = (ap.sai_media / ap.ent_media >= 0.8) | (ap.ent_media / ap.renda_declarada < 0.6)
    filt = r0 & n1 & c20 & ~ex
    md("## 5. Tabela \"inadimplência projetada por grupo\" (19,4% / 7,7% / 8,0%)")
    md("")
    md("**Definição que reproduz os números** (testadas: KM, w do time com regra de 61 dias, cal3×2,92, w com rótulo de 90 dias): "
       "é o estimador `pesos_censura` de `src/cenarios.py` — evento = `situacao_final = 'inadimplente'` (90+ dias), "
       "peso w = min(parcelas vencidas até o corte, janela)/janela, janela = ⌈2/3 do prazo⌉, inadimplente pesa 1; taxa = eventos / Σw. "
       "Filtros = os da v2 (restrição = 0, ≤1 mês com saldo negativo, parcela aprovada ≤ 20% da renda declarada) **mais** os extras de D "
       "(saídas ≥ 80% das entradas, renda real < 60% da declarada).")
    md("")
    lin = {}
    grupos = [("score ≤ 600, sem filtro", s6), ("score ≤ 600, filtrado", s6 & filt), ("score > 600, sem filtro", ~s6),
              ("score > 600, filtrado", ~s6 & filt), ("score > 600, filtrado, só piloto", ~s6 & filt & (ap.politica_aplicada == "piloto")),
              ("score > 600, filtrado, safras 2025T4–2026T1", ~s6 & filt & ap.safra.isin(["2025Q4", "2026Q1"]))]
    G = {}
    for nome, mask in grupos:
        g = ap[mask]
        G[nome] = g
        w90, n_w = _w90(g, venc)
        r = resumo_grupo(g)
        lin[nome] = {"contratos": len(g), "com peso > 0": n_w, "pararam (61d)": r["pararam"],
                     "inadimplente (90d)": int((g.situacao_final == "inadimplente").sum()),
                     "w-90d (time)": pct(w90), "KM vida (61d)": pct(r["pd_vida"]), "IC95 KM": f"{pct(r['ic_inf'])} – {pct(r['ic_sup'])}",
                     "% piloto": pct((g.politica_aplicada == "piloto").mean()), "safra mediana": str(g.data_pedido.median().date())}
    t = pd.DataFrame(lin).T
    t.index.name = "grupo (aprovados históricos)"
    md(tab(t))
    md("")
    # decomposição sequencial dos filtros no grupo score <= 600
    md("**Decomposição da queda no grupo score ≤ 600** (filtros aplicados em sequência):")
    md("")
    seq = [("todos (score ≤ 600)", s6), ("+ restrição = 0", s6 & r0), ("+ ≤1 mês com saldo negativo", s6 & r0 & n1),
           ("+ parcela ≤ 20% da renda declarada", s6 & r0 & n1 & c20), ("+ saídas < 80% e renda real ≥ 60%", s6 & filt)]
    lin, prev = {}, None
    for nome, mask in seq:
        g = ap[mask]
        w90, _ = _w90(g, venc)
        r = resumo_grupo(g)
        rem = "" if prev is None else f"{len(prev) - len(g)} contratos / {int(prev.parou.sum() - g.parou.sum())} paradas"
        lin[nome] = {"contratos": len(g), "paradas (61d)": int(g.parou.sum()), "w-90d (time)": pct(w90),
                     "KM vida": pct(r["pd_vida"]), "removidos (contratos / paradas)": rem}
        prev = g
    t = pd.DataFrame(lin).T
    t.index.name = "passo"
    md(tab(t))
    md("")
    # efeito isolado de cada filtro
    lin = {}
    for nome, mask in [("restrição ≥ 1", ~r0), ("2+ meses saldo negativo", ~n1), ("parcela > 20% renda", ~c20), ("filtros extras de D", ex)]:
        g = ap[s6 & mask]
        lin[nome] = {"contratos (score ≤ 600)": len(g), "paradas": int(g.parou.sum()),
                     "KM vida do grupo removido": pct(km_vida(g)[0]) if len(g) >= 15 else "n pequeno",
                     "contratos (score > 600)": int((~s6 & mask).sum()),
                     "KM vida (score > 600)": pct(km_vida(ap[~s6 & mask])[0])}
    t = pd.DataFrame(lin).T
    t.index.name = "filtro (isolado)"
    md(tab(t))
    md("")
    lo, hi = _boot_diff(G["score ≤ 600, filtrado"], G["score > 600, filtrado"])
    lo2, hi2 = _boot_diff(G["score ≤ 600, filtrado"], G["score > 600, filtrado, só piloto"])
    d1 = km_vida(G["score ≤ 600, filtrado"])[0] - km_vida(G["score > 600, filtrado"])[0]
    d2 = km_vida(G["score ≤ 600, filtrado"])[0] - km_vida(G["score > 600, filtrado, só piloto"])[0]
    md(f"Diferença KM (≤600 − >600), filtrados: **{100 * d1:+.1f} p.p.**, IC95 bootstrap [{100 * lo:+.1f}; {100 * hi:+.1f}] (500 reamostragens). "
       f"Contra >600 só do piloto (mesma safra e política): **{100 * d2:+.1f} p.p.**, IC95 [{100 * lo2:+.1f}; {100 * hi2:+.1f}].")
    md("")


# ---------------------------------------------------------------- 6. backtest fora do tempo
def _situacao_em(corte: pd.Timestamp):
    """Reconstrói o desfecho de cada contrato como se o corte fosse `corte` (pagamentos posteriores apagados)."""
    x = _consulta("select id_pedido, numero_parcela, data_vencimento, data_pagamento from hackathon.parcelas")
    x["data_vencimento"] = pd.to_datetime(x.data_vencimento)
    x["data_pagamento"] = pd.to_datetime(x.data_pagamento)
    x = x[x.data_vencimento <= corte]
    paga = x.data_pagamento.notna() & (x.data_pagamento <= corte)
    atraso_pago = paga & ((x.data_pagamento - x.data_vencimento).dt.days > 0)
    dias = (corte - x.data_vencimento).dt.days
    x["inad90"] = ~paga & (dias >= 90)
    x["atr"] = atraso_pago | (~paga & (dias > 0))
    g = x.groupby("id_pedido")
    return pd.DataFrame({"venc": g.size(), "inad90": g.inad90.any(), "atr": g.atr.any()}).reset_index()


def parte6_backtest(hist):
    S = pd.Timestamp("2025-09-30")
    md("## 6. Backtest fora do tempo (corte simulado em 30/09/2025)")
    md("")
    sit = _situacao_em(S)
    h = hist.copy()
    ap = h[(h.decisao == "aprovado") & (h.data_pedido <= S)].merge(sit, on="id_pedido", how="left")
    ap[["venc"]] = ap[["venc"]].fillna(0)
    ap[["inad90", "atr"]] = ap[["inad90", "atr"]].fillna(False)
    # modelo corrigido treinado só com o que se sabia em S
    jan = np.ceil(ap.prazo_meses * 2 / 3)
    w = np.where(ap.inad90, 1.0, (np.minimum(ap.venc, jan) / jan).clip(0, 1))
    X = M.atributos_para_valor(ap, ap.valor_aprovado)
    y = ap.inad90.astype(int)
    ok = w > 0
    from sklearn.ensemble import HistGradientBoostingClassifier
    cfg = dict(max_iter=300, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0, random_state=42)
    m_s = HistGradientBoostingClassifier(**cfg).fit(X[ok], y[ok], sample_weight=w[ok])
    # modelo antigo (3 classes) treinado com contratos de 6+ meses em S e rótulo em S
    ap6 = ap[ap.data_pedido <= S - pd.DateOffset(months=6)]
    cls = np.where(ap6.inad90, 2, np.where(ap6.atr, 1, 0))
    ant_s = M.novo_modelo().fit(M.atributos_para_valor(ap6, ap6.valor_aprovado), cls)

    teste = h[(h.data_pedido > S) & (h.data_pedido <= "2026-03-31")].copy()
    from g_util import carregar as gcar
    _, _, apg, _ = gcar()
    teste = teste.merge(apg[["id_pedido", "parou", "atrasou", "k_parada", "k_obs", "prazo_meses", "n_decididas", "k_1o_atraso"]]
                        .rename(columns={"prazo_meses": "prazo_g"}), on="id_pedido", how="left")
    # política com VALOR FIXO = aprovado histórico (só aprova/nega)
    tv = teste.copy()
    tv["valor_solicitado"] = np.where(tv.decisao == "aprovado", tv.valor_aprovado, tv.valor_solicitado)
    P.FRACOES = np.array([1.0])
    W = C.m_wrap(m_s)
    dec = {
        "A (atual)": P.politica_atual(tv),
        "C (antigo, risco≤20%, score>600)": P.politica_proposta(tv, ant_s, {"min_score": 600, "risco_max": 0.20})[["id_pedido", "aprova", "valor"]],
        "G (corrigido, risco≤17,5%, sem score)": P.politica_proposta(tv, W, {"min_score": 0, "risco_max": 0.175})[["id_pedido", "aprova", "valor"]],
        "aprovados históricos (atual+piloto)": pd.DataFrame({"id_pedido": tv.id_pedido, "aprova": tv.decisao == "aprovado", "valor": tv.valor_solicitado}),
    }
    P.FRACOES = np.round(np.arange(1.0, 0.05, -0.05), 2)
    lin, subs = {}, {}
    for nome, dd in dec.items():
        z = teste.merge(dd, on="id_pedido")
        sem = int((z.aprova & (z.decisao != "aprovado")).sum())
        z = z[z.aprova & (z.decisao == "aprovado")].copy()
        # valor = o da regra, limitado ao aprovado na época (desfecho observado vale para valor <= aprovado; conservador)
        v = np.minimum(z.valor.to_numpy(float), z.valor_aprovado.to_numpy(float))
        n_red = int((v < z.valor_aprovado.to_numpy(float) - 100).sum())
        ganho_obs = np.where(z.parou, -0.60, np.where(z.atrasou, 0.05, 0.15))
        subs[nome] = pd.DataFrame({"id_pedido": z.id_pedido.values, "v": v})
        g = z.rename(columns={"prazo_g": "prazo_meses_g"}).copy()
        g["prazo_meses"] = g["prazo_meses_g"]
        r = resumo_grupo(g)
        p_proj = m_s.predict_proba(M.atributos_para_valor(z, v))[:, 1]
        res_proj = float((v * (0.15 * (1 - p_proj) * (1 - R_ATRASO) + 0.05 * (1 - p_proj) * R_ATRASO - 0.60 * p_proj)).sum())
        lin[nome] = {"aprova com desfecho": len(z), "dos quais com valor reduzido": n_red, "aprova sem desfecho (negados no histórico)": sem,
                     "volume (mi)": v.sum() / 1e6, "paradas obs.": int(z.parou.sum()),
                     "resultado no horizonte observado (mil)": (ganho_obs * v).sum() / 1e3,
                     "PD vida KM": pct(r["pd_vida"]), "resultado vida KM (mil)": r["margem_R$"] * v.sum() / 1e3,
                     "PD prevista (modelo em S)": pct(p_proj.mean()), "resultado projetado (mil)": res_proj / 1e3}
    t = pd.DataFrame(lin).T
    for c in ["resultado no horizonte observado (mil)", "resultado vida KM (mil)", "resultado projetado (mil)"]:
        t[c.replace("resultado", "ganho vs A")] = t[c] - t.loc["A (atual)", c]
    t.index.name = "regra (valor = aprovado histórico)"
    md(f"Treino: {int(ok.sum())} aprovados até 30/09/2025 com desfecho reconstruído nessa data (pagamentos posteriores apagados). "
       f"Teste: pedidos de out/2025 a mar/2026 ({len(teste)}; {int((teste.decisao == 'aprovado').sum())} aprovados com desfecho até 30/09/2026, "
       f"6 a 12 parcelas observadas). Valor = o da regra limitado ao aprovado na época, com o desfecho observado daquele contrato "
       f"(conservador para quem reduz: o risco no valor menor seria igual ou menor).")
    md("")
    md(tab(t, "{:,.1f}"))
    md("")
    t.to_csv(OUT / "g06_backtest.csv", encoding="utf-8")
    # bootstrap pareado (reamostra contratos do teste) do ganho de vida inteira (KM) e no horizonte observado
    base = teste[teste.decisao == "aprovado"].reset_index(drop=True)
    base["prazo_meses"] = base["prazo_g"]
    ids = base.id_pedido.values
    rng = np.random.default_rng(11)
    nomes = list(subs)
    vmap = {n: subs[n].set_index("id_pedido")["v"] for n in nomes}
    res = {n: [] for n in nomes}
    for _ in range(300):
        amostra = base.iloc[rng.integers(0, len(base), len(base))]
        for n in nomes:
            g = amostra[amostra.id_pedido.isin(vmap[n].index)].copy()
            g["valor_aprovado"] = g.id_pedido.map(vmap[n]).values
            r = resumo_grupo(g)
            obs = (np.where(g.parou, -0.60, np.where(g.atrasou, 0.05, 0.15)) * g.valor_aprovado).sum()
            res[n].append((r["margem_R$"] * g.valor_aprovado.sum(), obs))
    a = np.array(res[nomes[0]])
    md("IC95 do ganho sobre A por bootstrap pareado (300 reamostragens de contratos do teste), R$ mil:")
    md("")
    for n in nomes[1:]:
        dlt = np.array(res[n]) - a
        md(f"- {n}: vida inteira (KM) [{np.percentile(dlt[:, 0], 2.5) / 1e3:+,.0f}; {np.percentile(dlt[:, 0], 97.5) / 1e3:+,.0f}] · "
           f"horizonte observado [{np.percentile(dlt[:, 1], 2.5) / 1e3:+,.0f}; {np.percentile(dlt[:, 1], 97.5) / 1e3:+,.0f}]")
    md("")


if __name__ == "__main__":
    main()
