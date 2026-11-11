"""Gera o painel de experimentação (saida/painel.html) a partir das ferramentas determinísticas."""
import html
import json

import pandas as pd

import backtest
import padroes
from modelo import SAIDA
from politica import PARAMS


def brl(v):
    return ("R$ " + f"{v:,.0f}").replace(",", ".")


def pct(v):
    return f"{v:.0%}"


def linhas_padroes(lista):
    out = []
    for p in lista:
        rr = p["risco_relativo"]
        cls = "alto" if rr >= 1.4 else ("baixo" if rr <= 0.75 else "neutro")
        largura = min(100, p["inadimplencia"] * 100 / 0.8 * 100 / 100)
        out.append(
            f"<tr class='{cls}'><td>{html.escape(p['grupo'])}</td>"
            f"<td class='n'>{pct(p['inadimplencia'])}<div class='barra'><span style='width:{largura:.0f}%'></span></div></td>"
            f"<td class='n'>{rr:.1f}×</td><td class='n'>{p['clientes']}</td></tr>")
    return "\n".join(out)


def gerar():
    hist = pd.read_pickle(SAIDA / "hist.pkl")
    pad = padroes.calcular(hist)
    meta = json.loads((SAIDA / "modelo_meta.json").read_text(encoding="utf-8"))
    atual, prop = backtest.rodar(verbose=False)
    ganho = prop["resultado"] - atual["resultado"]
    b = pad["base"]

    novos_html = "<p class='aviso'>Decisões dos novos pedidos ainda não geradas: rode <code>gerar_decisoes.py</code> com o token do bureau.</p>"
    det_path = SAIDA / "decisoes_detalhadas.csv"
    if det_path.exists():
        d = pd.read_csv(det_path)
        mot = d.motivo.value_counts()
        novos_html = f"""
        <div class='cards'>
          <div class='card'><b>{int(d.aprova.sum())}</b><span>aprovados de {len(d)}</span></div>
          <div class='card'><b>{brl(d.valor.sum())}</b><span>valor total aprovado</span></div>
          <div class='card'><b>{int((d.aprova != d.atual_aprova).sum())}</b><span>decisões diferentes da política atual</span></div>
          <div class='card'><b>{int((d.aprova & ~d.atual_aprova).sum())}</b><span>aprovados que a atual negaria</span></div>
        </div>
        <table><tr><th>Motivo</th><th class='n'>Pedidos</th></tr>
        {''.join(f"<tr><td>{html.escape(str(k))}</td><td class='n'>{v}</td></tr>" for k, v in mot.items())}</table>"""

    pagina = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Painel Fortuna Spread</title>
<style>
:root{{--bg:#fafaf7;--fg:#1d1d1b;--mut:#6b6b66;--card:#fff;--bd:#e4e2da;--alto:#c2410c;--baixo:#15803d;--acc:#b8860b;--barbg:#eeece4}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#161614;--fg:#ecebe6;--mut:#a3a29b;--card:#20201d;--bd:#34332e;--alto:#fb923c;--baixo:#4ade80;--acc:#facc15;--barbg:#2c2b27}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:980px;margin:0 auto;padding:32px 16px 64px}}
h1{{font-size:28px;margin:0 0 4px}} h2{{margin-top:40px;border-bottom:2px solid var(--acc);padding-bottom:4px}}
.sub{{color:var(--mut)}} table{{width:100%;border-collapse:collapse;margin:12px 0;background:var(--card)}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--bd);text-align:left;vertical-align:top}} th{{font-size:13px;color:var(--mut)}}
.n{{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}}
tr.alto td:first-child{{border-left:4px solid var(--alto)}} tr.baixo td:first-child{{border-left:4px solid var(--baixo)}} tr.neutro td:first-child{{border-left:4px solid var(--bd)}}
.barra{{height:5px;background:var(--barbg);margin-top:4px;min-width:80px}} .barra span{{display:block;height:100%;background:var(--alto)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0}}
.card{{background:var(--card);border:1px solid var(--bd);padding:14px}} .card b{{display:block;font-size:22px}} .card span{{color:var(--mut);font-size:13px}}
ol.passos li{{margin-bottom:10px}} code{{background:var(--barbg);padding:1px 5px}}
.aviso{{border-left:4px solid var(--acc);padding:8px 12px;background:var(--card)}}
.wrap{{overflow-x:auto}}
</style></head><body><main>
<h1>Fortuna Crédito: painel de experimentação</h1>
<p class="sub">Time Spread · Hackathon GOW 2026 · histórico até 30/09/2026</p>

<div class="cards">
 <div class="card"><b>{b['clientes']}</b><span>contratos com desfecho observável (aprovados até {b['ate'][8:]}/{b['ate'][5:7]}/{b['ate'][:4]})</span></div>
 <div class="card"><b>{pct(b['inadimplencia_media'])}</b><span>inadimplência média (90+ dias sem pagar)</span></div>
 <div class="card"><b>{brl(ganho)}</b><span>ganho da proposta sobre a atual no teste fora da amostra</span></div>
 <div class="card"><b>{meta['auc_inadimplencia_validacao_temporal']:.2f}</b><span>AUC do modelo de risco (treino até set/25, teste out/25–mar/26)</span></div>
</div>

<h2>Parte 1. Padrões encontrados</h2>
<p>Comparação da inadimplência de cada grupo com a média de {pct(b['inadimplencia_media'])}. Contratos aprovados há menos de 6 meses ficam de fora, porque ainda não tiveram tempo de dar inadimplência.</p>
<div class="wrap"><table><tr><th>Clientes com…</th><th class="n">Inadimplência</th><th class="n">vs média</th><th class="n">Clientes</th></tr>
{linhas_padroes(pad['padroes'])}</table></div>

<h3>Combinações encontradas pela árvore de decisão</h3>
<p>O algoritmo procurou sozinho as combinações de atributos que mais separam quem paga de quem não paga.</p>
<div class="wrap"><table><tr><th>Clientes com…</th><th class="n">Inadimplência</th><th class="n">vs média</th><th class="n">Clientes</th></tr>
{linhas_padroes(pad['combinacoes'])}</table></div>

<h3>O que isso diz sobre a política atual</h3>
<ul>
<li><b>Acima de 600, o score não separa bons de maus pagadores:</b> as faixas 600–699, 700–799 e 800+ têm inadimplência projetada parecida (15–16%). Abaixo de 600 o risco bruto sobe (21–27% projetado), mas isso vem de conta apertada e parcela alta: <b>depois dos filtros da proposta, score até 600 tem ~7% de inadimplência projetada, igual a score acima de 600</b> (confirmado por uma validação independente). Por isso a proposta não corta por score.</li>
<li><b>O teto de 30% da renda é alto demais.</b> Quando a parcela fica entre 25% e 30% da renda, a inadimplência sobe para mais de 40%. A política atual ainda <i>reduz o valor até a parcela caber em 30%</i>, o que leva o cliente exatamente para a faixa de maior risco.</li>
<li><b>A conta corrente avisa antes do bureau.</b> Saldo negativo em 2 ou mais meses e pouca sobra entre entradas e saídas são os sinais mais fortes, e a política atual não olha para nenhum deles.</li>
<li><b>A renda declarada engana.</b> Quando a parcela passa de 28% da renda que de fato entra na conta, o cliente não paga, mesmo dentro da regra atual: no teste fora da amostra, 114 desses clientes deram 42% de inadimplência (−R$ 145 mil). Reduzir o valor não resolve; é o cliente que é de risco.</li>
<li><b>A Fortuna já testou afrouxar a regra, e perdeu.</b> Entre out/25 e mar/26 ela aprovou 427 pedidos fora da regra: −2,4% de retorno. Separando por motivo, o prejuízo veio de restrição (−7,8%) e renda baixa (−3,4%). Score até 600 com conta saudável rendeu +8,3%, igual a quem está dentro da regra.</li>
</ul>

<h2>Parte 2. Política proposta</h2>
<ol class="passos">
{f"<li><b>Filtro de score:</b> nega pedidos com score até {PARAMS['min_score']}.</li>" if PARAMS['min_score'] else ""}
<li><b>Filtro de restrição:</b> nega pedidos com {PARAMS['max_restricoes'] + 1} ou mais restrições ativas no bureau.</li>
{f"<li><b>Filtro de conta:</b> nega quem teve {PARAMS['max_meses_negativos'] + 1} ou mais meses com saldo negativo nos últimos 12 meses.</li>" if PARAMS['max_meses_negativos'] < 12 else ""}
<li><b>Conta apertada:</b> nega quem gastou mais do que recebeu em algum dos 3 meses antes do pedido.</li>
<li><b>Renda real:</b> nega se a parcela do valor pedido (limitado a 30% da renda declarada) passa de {pct(PARAMS['teto_parcela_renda_real'])} da renda real (a menor entre a declarada e a média de entradas na conta).</li>
<li><b>Teto de parcela:</b> a parcela não pode passar de {pct(PARAMS['max_comprometimento'])} da renda declarada. Acima disso, o valor é reduzido até caber.</li>
<li><b>Risco:</b> um modelo treinado no histórico estima, para cada valor possível (100%, 95%… 10% do solicitado), a chance de o cliente pagar em dia, pagar com atraso ou não pagar. A conta usa o valor, o prazo, a renda, a movimentação da conta e o bureau.</li>
<li><b>Valor:</b> aprova o valor com o maior ganho esperado (15% × chance de pagar em dia + 5% × chance de atraso − 60% × chance de não pagar), desde que a chance de não pagar fique em até {pct(PARAMS['risco_max'])}. Se nenhum valor dá ganho positivo, nega.</li>
<li><b>Limites do produto:</b> mínimo de R$ 500, máximo de R$ 30 mil e nunca acima do valor solicitado.</li>
</ol>

<h3>Teste fora da amostra (out/2025 a mar/2026)</h3>
<p>O modelo foi treinado só com pedidos até set/2025 e aplicado aos pedidos seguintes, cujo desfecho já se conhece. Quando a proposta aprova alguém que foi negado na época, não há desfecho conhecido, então esse pedido conta como zero (estimativa conservadora).</p>
<table><tr><th></th><th class="n">Aprovados</th><th class="n">Volume</th><th class="n">Não pagaram</th><th class="n">Resultado</th></tr>
<tr><td>Política atual</td><td class="n">{atual['aprovados']}</td><td class="n">{brl(atual['volume'])}</td><td class="n">{atual['nao_pagou_aprovados']}</td><td class="n">{brl(atual['resultado'])}</td></tr>
<tr><td>Política proposta</td><td class="n">{prop['aprovados']}</td><td class="n">{brl(prop['volume'])}</td><td class="n">{prop['nao_pagou_aprovados']}</td><td class="n">{brl(prop['resultado'])}</td></tr>
</table>

<h2>Novos pedidos (outubro/2026)</h2>
{novos_html}

<h2>Como o analista valida</h2>
<ul>
<li>Cada parâmetro acima (teto de parcela, risco máximo, filtros) é ajustável, e o teste fora da amostra é refeito na hora.</li>
<li>Cada decisão traz o motivo e as chances estimadas em <code>decisoes_detalhadas.csv</code>.</li>
<li>A IA sugere e o analista decide: nenhuma política entra em produção sem aprovação humana.</li>
</ul>
</main></body></html>"""
    (SAIDA / "painel.html").write_text(pagina, encoding="utf-8")
    return SAIDA / "painel.html"


if __name__ == "__main__":
    print(gerar())
