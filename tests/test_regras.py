"""Testes que não precisam do banco: regras do manual, políticas, validador, bureau, tools e agente."""
import json

import numpy as np
import pandas as pd
import pytest

from features import parcela_price


# ---------------------------------------------------------------- parcela (dicionário de dados, tabela Price a 3%)
@pytest.mark.parametrize("valor,prazo,esperado", [
    (7000, 12, 703.23), (8000, 12, 803.70), (10000, 12, 1004.62), (15000, 24, 885.71), (25000, 24, 1476.19),
    (2700, 24, 159.43),
])
def test_parcela_price_bate_com_dicionario(valor, prazo, esperado):
    assert parcela_price(valor, prazo) == pytest.approx(esperado, abs=0.005)


# ---------------------------------------------------------------- políticas
def _pedidos(**kw):
    base = dict(id_pedido=["P-00001"], valor_solicitado=[10000.0], prazo_meses=[12], renda_declarada=[5000.0],
                score=[700], restricoes_ativas=[0], parcelas_outras_instituicoes=[0.0], mov_meses_cheque=[0],
                mov_entradas_media=[5000.0], tipo_vinculo=["assalariado"])
    base.update({k: [v] for k, v in kw.items()})
    return pd.DataFrame(base)


def test_politica_atual_reduz_valor_ate_30_por_cento():
    from politica import politica_atual
    d = politica_atual(_pedidos(renda_declarada=3000.0)).iloc[0]   # parcela de 10 mil/12m = 1.004,62 > 900
    assert d.aprova and d.valor < 10000
    assert parcela_price(d.valor, 12) <= 0.30 * 3000 + 0.01


@pytest.mark.parametrize("campo,valor", [("score", 600), ("renda_declarada", 2000.0), ("restricoes_ativas", 1)])
def test_politica_atual_nega_fora_das_regras(campo, valor):
    from politica import politica_atual
    assert not politica_atual(_pedidos(**{campo: valor})).iloc[0].aprova


class ModeloFixo:
    """Modelo falso: P(não paga) fixa, para testar só as regras da política."""
    def __init__(self, p):
        self.p = p

    def predict_proba(self, X):
        n = len(X)
        return np.column_stack([np.full(n, (1 - self.p) * 0.77), np.full(n, (1 - self.p) * 0.23), np.full(n, self.p)])


def _proposta(df, p=0.05, params=None, monkeypatch=None):
    import politica
    monkeypatch.setattr(politica, "probabilidades", lambda m, x, v: m.predict_proba(np.zeros(len(x))))
    return politica.politica_proposta(df, ModeloFixo(p), params)


def test_proposta_respeita_teto_de_parcela_e_solicitado(monkeypatch):
    d = _proposta(_pedidos(), monkeypatch=monkeypatch).iloc[0]
    assert d.aprova
    assert 500 <= d.valor <= 10000
    from politica import PARAMS
    assert parcela_price(d.valor, 12) <= PARAMS["max_comprometimento"] * 5000 + 0.01


@pytest.mark.parametrize("campo,valor,motivo", [
    ("restricoes_ativas", 1, "restrição"), ("mov_meses_cheque", 2, "saldo negativo"),
])
def test_proposta_filtros_negam(monkeypatch, campo, valor, motivo):
    d = _proposta(_pedidos(**{campo: valor}), params={"max_meses_negativos": 1}, monkeypatch=monkeypatch).iloc[0]
    assert not d.aprova and d.valor == 0 and motivo in d.motivo


def test_proposta_filtros_do_bilosca(monkeypatch):
    apertada = _proposta(_pedidos(mov_meses_saida_maior_3m=1), monkeypatch=monkeypatch).iloc[0]
    assert not apertada.aprova and "conta apertada" in apertada.motivo
    # renda declarada 5.000, mas só entram 2.000 na conta: parcela de 10 mil/12m (1.004,62) = 50% da renda real
    pesada = _proposta(_pedidos(mov_entradas_media=2000.0), monkeypatch=monkeypatch).iloc[0]
    assert not pesada.aprova and "renda real" in pesada.motivo
    desligado = _proposta(_pedidos(mov_entradas_media=2000.0), monkeypatch=monkeypatch,
                          params={"teto_parcela_renda_real": 0}).iloc[0]
    assert desligado.aprova


def test_saldo_negativo_desligado_por_padrao(monkeypatch):
    assert _proposta(_pedidos(mov_meses_cheque=3), monkeypatch=monkeypatch).iloc[0].aprova


def test_proposta_nega_risco_acima_do_limite(monkeypatch):
    d = _proposta(_pedidos(), p=0.30, monkeypatch=monkeypatch).iloc[0]
    assert not d.aprova


def test_proposta_corte_de_score_opcional(monkeypatch):
    sem = _proposta(_pedidos(score=550), params={"min_score": 0}, monkeypatch=monkeypatch).iloc[0]
    com = _proposta(_pedidos(score=550), params={"min_score": 600}, monkeypatch=monkeypatch).iloc[0]
    assert sem.aprova and not com.aprova


# ---------------------------------------------------------------- validador do CSV (offline)
def _csv(tmp_path, texto, bom=False):
    p = tmp_path / "x.csv"
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + texto.encode("utf-8"))
    return p


OK = "id_pedido,decisao,valor_aprovado\nP-00001,APROVADO,8500.00\nP-00002,NEGADO,0.00\n"


def test_validador_aceita_arquivo_correto(tmp_path):
    from validar_csv import validar_formato
    erros, _, rel = validar_formato(_csv(tmp_path, OK))
    assert erros == [] and rel["aprovados"] == 1 and rel["negados"] == 1


@pytest.mark.parametrize("texto,trecho", [
    (OK.replace("APROVADO", "aprovado"), "decisao"),
    (OK.replace("NEGADO,0.00", "NEGADO,10.00"), "negado com valor"),
    (OK.replace("8500.00", "8500"), "fora do formato"),
    (OK.replace("8500.00", "8500,00"), "colunas"),
    (OK.replace("id_pedido,decisao", "pedido,decisao"), "cabeçalho"),
    (OK + "P-00001,NEGADO,0.00\n", "repetido"),
    (OK.replace("8500.00", "45000.00"), "30 mil"),
    (OK.replace("P-00002", "X2"), "P-00000"),
])
def test_validador_rejeita_erros_do_manual(tmp_path, texto, trecho):
    from validar_csv import validar_formato
    erros, _, _ = validar_formato(_csv(tmp_path, texto))
    assert any(trecho in e for e in erros), erros


def test_validador_rejeita_bom(tmp_path):
    from validar_csv import validar_formato
    erros, _, _ = validar_formato(_csv(tmp_path, OK, bom=True))
    assert any("BOM" in e for e in erros)


def test_validador_com_base_confere_ids_e_solicitado(tmp_path):
    from validar_csv import validar_formato
    erros, _, _ = validar_formato(_csv(tmp_path, OK), {"P-00001": 8000.0, "P-00003": 1000.0})
    texto = " | ".join(erros)
    assert "acima do solicitado" in texto and "não existe" in texto and "ausentes" in texto


# ---------------------------------------------------------------- bureau: retry e 401
class Resp:
    def __init__(self, status, corpo=None):
        self.status_code, self._c = status, corpo or {}

    def json(self):
        return self._c


def test_bureau_tenta_de_novo_em_503(monkeypatch):
    import bureau
    monkeypatch.setenv("FORTUNA_BUREAU_TOKEN", "teste")
    monkeypatch.setattr(bureau.time, "sleep", lambda s: None)
    ok = {"score": 700, "restricoes_ativas": 0, "parcelas_outras_instituicoes": 0, "consultas_90_dias": 1,
          "meses_historico_bureau": 10}
    seq = iter([Resp(503), Resp(503), Resp(200, ok)])

    class S:
        def get(self, *a, **k):
            return next(seq)
    r = bureau.consultar("C-1", sessao=S())
    assert r["score"] == 700


def test_bureau_para_em_401(monkeypatch):
    import bureau
    monkeypatch.setenv("FORTUNA_BUREAU_TOKEN", "teste")

    class S:
        def get(self, *a, **k):
            return Resp(401)
    with pytest.raises(bureau.TokenInvalido):
        bureau.consultar("C-1", sessao=S())


def test_bureau_sem_token_falha_claro(monkeypatch):
    import bureau
    monkeypatch.delenv("FORTUNA_BUREAU_TOKEN", raising=False)
    with pytest.raises(bureau.TokenInvalido):
        bureau.consultar("C-1")


# ---------------------------------------------------------------- tools e agente
def test_tools_tem_schema_valido_e_funcao():
    from tools import _FUNCS, TOOLS, executar
    nomes = [t["function"]["name"] for t in TOOLS]
    assert len(nomes) == len(set(nomes)) and set(nomes) == set(_FUNCS)
    json.dumps(TOOLS)
    assert "erro" in executar("nao_existe", {})


def test_agente_fallback_e_guarda(monkeypatch):
    import agente
    import llm
    monkeypatch.setattr(agente, "_registrar", lambda e: None)
    monkeypatch.setattr(agente, "executar", lambda nome, args: {"ok": nome})
    respostas = iter([
        {"tool_calls": [{"id": "1", "function": {"name": "simular_politica", "arguments": "{}"}}]},
        {"content": "pronto"},
    ])
    chamadas = []

    def falso(cfg, modelo, msgs, tools=None, **kw):
        chamadas.append(cfg["nome"])
        if cfg["nome"] == "zai":
            raise RuntimeError("HTTP 500: fora")
        return next(respostas)
    monkeypatch.setattr(llm, "chamar_um", falso)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    for k, v in {"LLM_ORDEM": "zai,groq", "ZAI_API_KEY": "x", "GROQ_API_KEY": "y"}.items():
        monkeypatch.setenv(k, v)
    resp, _, ch, quem = agente.perguntar("teste", log=lambda *a: None)
    assert resp == "pronto" and quem.startswith("groq/") and ch[0]["tool"] == "simular_politica"
    assert "zai" in chamadas
    assert "erro" in agente._guarda("gerar_csv", {"confirmar": True}, interativo=False)
    assert agente._guarda("gerar_csv", {"confirmar": False}, interativo=False) is None


def test_llm_sem_provedor(monkeypatch):
    import llm
    for n in llm.PROVEDORES:
        monkeypatch.delenv(f"{n.upper()}_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ORDEM", "zai")
    with pytest.raises(llm.SemProvedor):
        llm.chamar([{"role": "user", "content": "oi"}], log=lambda *a: None)
