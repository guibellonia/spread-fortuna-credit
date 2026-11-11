"""Garante que a base das tools existe (saida/hist.pkl e saida/novos.pkl) e o modelo de sobrevivência foi treinado.

Local: normalmente já existem (gerados por gerar_decisoes.py). No servidor: gera no primeiro start a partir do
banco (FORTUNA_DSN) e da API do bureau (FORTUNA_BUREAU_TOKEN, com cache). Não grava o CSV de entrega.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "saida"
sys.path.insert(0, str(RAIZ / "src"))
sys.path.append(str(RAIZ / "validacao"))


def _log(m):
    print(f"[bootstrap] {m}", file=sys.stderr, flush=True)


def garantir_base():
    SAIDA.mkdir(exist_ok=True)
    if not (SAIDA / "hist.pkl").exists() or not (SAIDA / "novos.pkl").exists():
        import pandas as pd

        import bureau
        from features import bureau_historico, montar, movimentacao_agregada, pedidos_base
        _log("montando base a partir do banco")
        base, mov = pedidos_base(), movimentacao_agregada()
        montar(base[base.tipo_base == "historico"], mov, bureau_historico()).to_pickle(SAIDA / "hist.pkl")
        novos = base[base.tipo_base == "novo"]
        resp = bureau.consultar_lote(novos.id_cliente.tolist(), log=_log)
        b = pd.DataFrame(list(resp.values()), columns=["id_cliente"] + bureau.CAMPOS)
        b["parcelas_outras_instituicoes"] = b["parcelas_outras_instituicoes"].astype(float)
        x = montar(novos, mov, b, chave_bureau="id_cliente")
        if x["score"].isna().any():
            raise RuntimeError(f"{int(x['score'].isna().sum())} pedidos sem bureau; o próximo start tenta de novo")
        x.to_pickle(SAIDA / "novos.pkl")
    import tool_risco
    if not Path(tool_risco.MODELO_PADRAO).exists():
        _log("treinando modelo de sobrevivência")
        tool_risco.treinar()
    _log("base pronta")


if __name__ == "__main__":
    garantir_base()
