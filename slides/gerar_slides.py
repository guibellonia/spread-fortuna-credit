"""Gera slides/index.html (deck do pitch, 8 slides, 5 minutos). Determinístico, sem LLM, sem dependência externa.
Rodar: python3 slides/gerar_slides.py
Visual e navegação herdados do deck das 10h30 (Enio Rocha, 11/11/2026). Todo número abaixo tem fonte no rodapé do slide.
Ganhos são estimativa de modelo, em dados fictícios do hackathon.
"""
import html as H
from pathlib import Path

OUT = Path(__file__).resolve().parent / "index.html"
esc = H.escape
NOTA = "Dados fictícios do hackathon; ganho é estimativa de modelo."

SL = []


def slide(kicker, titulo, corpo, fonte, cls=""):
    SL.append(dict(kicker=kicker, titulo=titulo, corpo=corpo, fonte=fonte, cls=cls))


def kpis(items):
    out = '<div class="kpis">'
    for it in items:
        v, l = it[0], it[1]
        c = it[2] if len(it) > 2 else ""
        out += f'<div class="kpi {c}"><div class="v">{v}</div><div class="l">{l}</div></div>'
    return out + "</div>"


def ul(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def table(head, rows, cls="sm"):
    t = f'<div class="tw"><table class="{cls}"><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
    for r in rows:
        t += "<tr" + (' class="hl"' if isinstance(r, tuple) else "") + ">"
        cells = r[0] if isinstance(r, tuple) else r
        t += "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
    return t + "</table></div>"


def note(t):
    return f'<p class="note">{t}</p>'


def call(t):
    return f'<div class="call">{t}</div>'


# 1 ---------------------------------------------------------------------------------------------
slide("1 · O problema", "A atual barra por score e reduz o valor. As duas coisas falham.",
      '<div class="cols c2"><div class="col">'
      + kpis([("56%", "dos 177 pedidos que a atual reduz (histórico maduro) não pagam; resultado −R$ 670.271", "r")])
      + ul(["<b>Reduzir não resolve:</b> a parcela cai para 30% da renda declarada, mas a renda real é menor.",
            "<b>Score acima de 600 separa pouco:</b> calote projetado de 16,1% (600–699), 15,6% (700–799) e 16,9% (800+)."])
      + '</div><div class="col">'
      + call("A pergunta do Head de Crédito: dá para ganhar mais, sem aprovar quem não paga?")
      + note(NOTA) + "</div></div>",
      "deck das 10h30 (slide 3): hackathon-gow-fortuna/slides/index.html · motor2/projecao.py (faixas_score) · analise/testes/teste3.py (reduzidos)")

# 2 ---------------------------------------------------------------------------------------------
slide("2 · A régua", "O jogo em uma conta: +15 / +5 / −60, com equilíbrio em 17,5%",
      kpis([("+15%", "do valor, se paga em dia", "g"), ("+5%", "do valor, se paga com atraso", "y"),
            ("−60%", "do valor, se não paga", "r"), ("0", "se o pedido é negado")])
      + "<p>Cada R$ 100 pago em dia rende R$ 15. Cada R$ 100 que vira calote perde R$ 60. Quatro pagadores em dia pagam um calote.</p>"
      + call("Ponto de equilíbrio: 17,4% a 17,5% de calote. Acima disso, aprovar perde dinheiro. É o corte de risco do modelo: 17,5%.")
      + table(["Faixa de score (histórico limpo)", "n", "Calote", "Folga até 17,4%"],
              [["450–499", "72", "3,0%", "folga de 14,4 pp"], ["500–549", "73", "15,1%", "folga de 2,3 pp"], ["550–600", "67", "16,8%", "folga de 0,6 pp"]])
      + note(NOTA),
      "motor2/projecao.py e ponto-ideal.json (régua e equilíbrio) · motor2/saida/piso/celulas_hist_todos_x_limpos.csv (faixas de score)", "ap")

# 3 ---------------------------------------------------------------------------------------------
slide("3 · Os padrões", "Dois padrões explicam o calote; consulta ao CPF não virou regra",
      '<div class="cols c3"><div class="col">'
      + kpis([("91%", "de calote com conta apertada (67 contratos maduros)", "r")])
      + "<p>Conta apertada: nos 3 meses antes do pedido, a saída média passa de 80% da entrada.</p></div><div class='col'>"
      + kpis([("≈50%", "de calote com parcela acima de 28% da renda real", "r")])
      + "<p>A renda real é menor que a declarada; a parcela só pesa quando medida nela.</p></div><div class='col'>"
      + kpis([("R$ 16 a 84 mil", "é o que se perderia ao negar por consulta ao CPF")])
      + "<p>As consultas já estão cobertas pelas barreiras. Negar por consulta perderia de R$ 16 mil a R$ 84 mil.</p></div></div>"
      + note(NOTA),
      "motor2/saida/consultas/ (impacto de negar por consulta) · padrões de conta apertada e parcela sobre renda real: analise do time e motor2/projecao.py")

# 4 ---------------------------------------------------------------------------------------------
slide("4 · A política", "A política em passos: a híbrida do time",
      '<div class="cols c2"><div class="col">'
      + '<table class="q"><tr><td>1</td><td><b>Barreiras:</b> restrição ativa, conta apertada nos 3 meses antes, parcela acima de 28% da renda real.</td></tr>'
        '<tr><td>2</td><td><b>Modelo:</b> escolhe o valor de maior ganho com risco de calote até 17,5%.</td></tr>'
        '<tr><td>3</td><td><b>Sem corte de score nem de renda.</b></td></tr>'
        '<tr><td>4</td><td><b>Idade fora do modelo.</b></td></tr></table>'
      + '</div><div class="col">'
      + call("Quem passa nas barreiras é decidido pelo risco previsto e pelo valor, não por um corte fixo de score.")
      + note("Política oficial do time: src/politica.py, repositório guibellonia/spread-fortuna-credit.") + note(NOTA)
      + "</div></div>",
      "src/politica.py (repositório do time)")

# 5 ---------------------------------------------------------------------------------------------
slide("5 · O resultado", "A híbrida aprova 1.412 pedidos (a atual, 1.145) e ganha de R$ 385 a 500 mil",
      kpis([("1.412", "aprovados pela híbrida; a atual aprova 1.145", "y"),
            ("R$ 385 a 500 mil", "ganho declarado pelo time, pelos 3 avaliadores", "g"),
            ("R$ 398 mil", "ganho declarado fora da amostra", "g"),
            ("+R$ 1,29 mi", "nos 10.000 pedidos passados (página Histórico)", "g")])
      + call("São os números do time. O que o nosso motor mediu à parte está no slide 6, com o limite dele.")
      + note(NOTA),
      "números declarados pelo time: página Histórico do painel e resumo de resultado (src/politica.py); não recalculados aqui")

# 6 ---------------------------------------------------------------------------------------------
slide("6 · O ponto honesto", "As faixas de score 500–600 ficam no limite do equilíbrio",
      '<div class="cols c2"><div class="col">'
      + table(["Variante (motor v2)", "Aprovados", "Ganho", "Fora do tempo"],
              [(["<b>híbrida (a do time)</b>", "1.412", "R$ 374.570", "R$ 171.113"],),
                 ["seletiva (libera só score 450–499 e renda baixa com score > 600)", "1.179", "R$ 327.373", "R$ 217.884"],
                 ["só-aperta", "1.043", "R$ 308.200", "R$ 272.924"]], "sm")
      + note("Fora do tempo = ganho do motor sobre a atual no teste fora do tempo (campo fora_do_tempo_motor_vs_atual). Na tabela, quanto mais a variante aprova, maior o ganho e menor o ganho fora do tempo.")
      + '</div><div class="col">'
      + call("Auditoria do próprio time: fora do tempo, a política G não ganha da atual com significância. O modelo previa 3,1% de calote e o observado foi 16,4%.")
      + call("A decisão do time é: <b>híbrida</b>.")
      + note(NOTA) + "</div></div>",
      "motor2/saida/piso/seletiva.json e resultado_piso.json · celulas_hist_todos_x_limpos.csv · analysis/scripts-guilherme/out/g06_auditoria.md:42-46 (repositório do time)")

# 7 ---------------------------------------------------------------------------------------------
slide("7 · Ética e controle", "O analista decide: a IA sugere, mostra a faixa de risco e responde ao vivo",
      '<div class="cols c2"><div class="col">'
      + ul(["<b>Fora do modelo:</b> idade, gênero, estado civil e CEP.",
            "Tirar a idade custou −R$ 2.255 de ganho, dentro do ruído.",
            "<b>Faixa de risco por pedido:</b> o analista vê onde o pedido está.",
            "<b>A IA sugere, o analista decide.</b>",
            "<b>O agente responde ao vivo</b> sobre qualquer pedido na tela."])
      + '</div><div class="col">'
      + call("O analista de crédito fica no controle. A ferramenta mostra o motivo; a decisão é dele.")
      + note(NOTA) + "</div></div>",
      "motor2/saida/sem_idade/resultado.json (−R$ 2.255 sem idade) · escopo do painel e do agente do time (site/, hermes/); não medido aqui")

# 8 ---------------------------------------------------------------------------------------------
slide("8 · Riscos", "Riscos e o que não medimos",
      '<div class="cols c2"><div class="col">'
      + "<p class='lead'>O que pode dar errado</p>"
      + ul(["Fora do tempo, a híbrida não ganha da atual com significância (auditoria do time, slide 6).",
            "Faixas de score 500–600 ficam no limite do equilíbrio (17,4–17,5%).",
            "<b>Fora da curva:</b> a híbrida deixa passar 3 pedidos com renda declarada inflada (R$ 24 mil).",
            "4 grupos de risco com degrau: parecem regras do gerador, não comportamento real."])
      + '</div><div class="col">'
      + "<p class='lead'>O que não medimos</p>"
      + ul(["Desfecho real dos pedidos novos: vem de regras escondidas do organizador.",
            "Ganho é estimativa de modelo, em dados fictícios.",
            "0 valores impossíveis encontrados na base."])
      + note(NOTA) + "</div></div>",
      "motor2/saida/fora_da_curva/RESULTADO.md · analysis/scripts-guilherme/out/g06_auditoria.md:42-46 (repositório do time)")

# ----------------------------------------------------------------------------------------------- html
CSS = r"""
:root{--bg:#1e1c1d;--panel:#2a2728;--panel2:#343031;--tx:#f2efe9;--mu:#a9a29a;--y:#f5d20a;--r:#ff6b5b;--g:#6fcf97;--bd:#4a4546}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--tx);font-family:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
#wrap{position:relative;width:100%;height:100vh;overflow:hidden}
#deck{position:absolute;left:50%;top:50%;width:1366px;height:720px;transform-origin:center center}
.slide{display:none;position:absolute;inset:0;width:1366px;height:720px;overflow:hidden;background:var(--bg);padding:34px 56px 52px}
.slide.on{display:block}
.slide:before{content:"";position:absolute;left:0;top:0;width:10px;height:100%;background:var(--y)}
.kicker{font-size:15px;letter-spacing:.14em;text-transform:uppercase;color:var(--y);font-weight:700}
h1{font-size:35px;line-height:1.12;margin:6px 0 14px;font-weight:800;letter-spacing:-.01em;max-width:1240px}
.slide p,.slide li{font-size:19px;line-height:1.36;margin:0 0 9px}
.slide ul{margin:0 0 6px;padding-left:22px}
.lead{font-size:23px!important;font-weight:700;color:var(--y)}
.note{color:var(--mu);font-size:15px!important}
.call{background:var(--panel);border-left:6px solid var(--y);padding:11px 16px;margin:8px 0;font-size:19px;line-height:1.35;font-weight:600}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin:0 0 12px}
.kpi{background:var(--panel);border:1px solid var(--bd);border-radius:10px;padding:11px 16px;flex:1 1 220px;min-width:0}
.kpi .v{font-size:34px;font-weight:800;line-height:1.05}
.kpi .l{font-size:15px;color:var(--mu);margin-top:4px;line-height:1.3}
.kpi.y .v{color:var(--y)}.kpi.g .v{color:var(--g)}.kpi.r .v{color:var(--r)}
.cols{display:grid;gap:30px}.c2{grid-template-columns:1fr 1fr}.c3{grid-template-columns:1fr 1fr 1fr;gap:18px}
.col{min-width:0}
.tw{overflow-x:auto;margin:0 0 8px}
table{border-collapse:collapse;width:100%;font-size:16px}
th,td{border-bottom:1px solid var(--bd);padding:6px 9px;text-align:left;vertical-align:top}
th{color:var(--y);font-weight:700;font-size:14px;text-transform:none}
table.sm{font-size:15px}table.sm th,table.sm td{padding:4px 8px}
table.cmp{font-size:15px}table.cmp td:first-child{color:var(--mu);white-space:nowrap}table.cmp td{width:27%}
table.q td{font-size:16px}table.q td:first-child{color:var(--y);font-weight:700;width:30px}
table.hm{table-layout:fixed;font-size:15px}
table.hm td{text-align:center;padding:9px 4px;border:3px solid var(--bg);border-radius:6px}
table.hm td b{display:block;font-size:19px}table.hm td small{font-size:12px;opacity:.85}
table.hm td.over{border-color:var(--y)}table.hm td.thin b,table.hm td.thin small{opacity:.6}
table.hm th{font-size:13px;text-align:center}
.bars{margin:6px 0 14px}.bar{display:flex;align-items:center;gap:12px;margin:8px 0;font-size:17px}
.bl{width:360px;flex:none}.bt{flex:1;background:var(--panel);height:26px;border-radius:5px;overflow:hidden}
.bt i{display:block;height:100%;background:#8d8680}.bt i.y{background:var(--y)}.bt i.r{background:var(--r)}
.bv{width:70px;font-weight:800;font-size:20px}
.fonte{position:absolute;left:56px;bottom:14px;right:260px;font-size:12px;color:#8d8680;line-height:1.25}
.pg{position:absolute;right:24px;top:30px;font-size:14px;color:#8d8680}
.marca{position:absolute;right:24px;top:52px;font-size:14px;font-weight:800;color:var(--y);letter-spacing:.08em}
.capa h1{font-size:56px;max-width:1100px;margin-top:70px;line-height:1.08}
.capa .lead{font-size:26px!important;color:var(--tx);max-width:1000px;margin-bottom:26px}
.capa .kpi .v{font-size:40px}
.chart{width:100%;height:auto;max-height:520px;display:block}
.chart .gl{stroke:#3d3839;stroke-width:1}.chart .ax{fill:#a9a29a;font-size:12px}.chart .an{fill:#fff;font-size:13px;font-weight:700}
.leg{font-size:14px;color:var(--mu);margin-top:4px}.sw{display:inline-block;width:14px;height:14px;border-radius:3px;margin:0 6px -2px 10px}
.sim{display:grid;grid-template-columns:400px 1fr;gap:26px}
.ctl{display:grid;gap:7px;align-content:start}
.ctl label{display:flex;flex-direction:column;font-size:13px;color:var(--mu);gap:2px}
.ctl select{background:var(--panel);color:var(--tx);border:1px solid var(--bd);border-radius:6px;padding:6px 8px;font-size:16px}
.pre{display:flex;gap:8px;margin-top:4px}
button{background:var(--y);color:#1e1c1d;border:0;border-radius:6px;padding:8px 14px;font-weight:800;font-size:15px;cursor:pointer}
.pre button{flex:1}
.out .kpis .kpi{flex:1 1 180px}.out .kpi .v{font-size:30px}
.dlt{font-size:14px;margin-top:3px}.up{color:var(--g)}.dn{color:var(--r)}
.rng{margin:8px 0}.rl{font-size:15px;margin-bottom:6px}.rb{position:relative;height:22px;background:var(--panel);border-radius:5px}
.rb i{position:absolute;top:0;bottom:0;background:rgba(245,210,10,.35);border-left:3px solid var(--y);border-right:3px solid var(--y)}
.rb u{position:absolute;top:-4px;bottom:-4px;width:2px;background:#fff;text-decoration:none}
#nav{position:fixed;right:14px;bottom:10px;display:flex;gap:8px;align-items:center;z-index:9;background:rgba(30,28,29,.88);padding:5px 8px;border-radius:8px;font-size:14px}
#nav button{padding:5px 12px}
#md{max-width:1100px;margin:0 auto;padding:20px 16px 70px}
#md summary{cursor:pointer;color:var(--y);font-weight:700}
#md pre{white-space:pre-wrap;background:var(--panel);padding:16px;border-radius:8px;font-size:13px;line-height:1.45;overflow-x:auto}
.ex .cols{gap:16px}.ex .lead{font-size:20px!important;margin-bottom:4px}.ex table{font-size:14px}.ex .call{font-size:15px;padding:8px 12px}.ex .slide p{font-size:17px}
.simslide .out p{font-size:15px}
@media (max-width:900px){
 #wrap{height:auto;overflow:visible}
 #deck{position:static;width:auto;height:auto;transform:none!important}
 .slide{position:relative;width:auto;height:auto;min-height:100vh;padding:20px 16px 70px 22px}
 .slide:before{width:6px}
 h1{font-size:26px}.capa h1{font-size:32px;margin-top:20px}
 .slide p,.slide li{font-size:16px}.lead{font-size:18px!important}
 .cols,.c2,.c3,.sim{grid-template-columns:1fr}
 .bar{flex-wrap:wrap}.bl{width:100%}
 .fonte{position:static;margin-top:18px}.pg,.marca{position:static;display:inline-block;margin-right:12px}
 .kpi .v{font-size:26px}.capa .kpi .v{font-size:28px}
 table.cmp{font-size:13px;min-width:520px}table.cmp td{width:auto}table.cmp td:first-child{white-space:normal}
}

table.sm tr.hl td{background:#3a3520;font-weight:700}
.slide{padding-top:40px}h1{max-width:1130px;margin-bottom:22px}
.slide p,.slide li{font-size:25px;line-height:1.38;margin-bottom:14px}
.lead{font-size:28px!important}.note{font-size:17px!important}
.call{font-size:25px;padding:16px 20px;margin:14px 0}
.kpi{padding:16px 20px}.kpi .v{font-size:46px}.kpi .l{font-size:19px}
table.sm{font-size:22px}table.sm th{font-size:17px}table.sm th,table.sm td{padding:9px 10px}
table.q td{font-size:25px;padding:12px 10px}table.q td:first-child{width:44px}
.fonte{font-size:13px}
.ap .kpi .v{font-size:34px}.ap .kpi .l{font-size:17px}.ap p{font-size:22px;margin-bottom:8px}.ap .call{font-size:22px;padding:11px 16px;margin:8px 0}.ap table.sm{font-size:19px}.ap table.sm th,.ap table.sm td{padding:5px 10px}
.fonte{right:200px}
"""

JS = r"""
(function(){
var slides=[].slice.call(document.querySelectorAll('.slide')),cur=0,N=slides.length;
function show(i){i=Math.max(0,Math.min(N-1,i));cur=i;slides.forEach(function(s,k){s.classList.toggle('on',k===i)});
 document.getElementById('pos').textContent=(i+1)+' / '+N;
 try{history.replaceState(null,'','#s='+(i+1))}catch(e){location.hash='s='+(i+1)}
 if(innerWidth<=900)window.scrollTo(0,0)}
function fromHash(){var m=/s=(\d+)/.exec(location.hash);return m?parseInt(m[1],10)-1:0}
function fit(){var d=document.getElementById('deck');
 if(innerWidth<=900){d.style.transform='';return}
 var s=Math.min(innerWidth/1366,innerHeight/720);d.style.transform='translate(-50%,-50%) scale('+s+')'}
document.getElementById('prev').onclick=function(){show(cur-1)};
document.getElementById('next').onclick=function(){show(cur+1)};
addEventListener('keydown',function(e){
 if(e.key==='ArrowRight'||e.key==='PageDown'||e.key===' '){e.preventDefault();show(cur+1)}
 else if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();show(cur-1)}
 else if(e.key==='Home')show(0);else if(e.key==='End')show(N-1)});
addEventListener('hashchange',function(){show(fromHash())});
addEventListener('resize',fit);
fit();show(fromHash());
})();
"""

secs = []
for i, s in enumerate(SL, 1):
    secs.append(f'<section class="slide {s["cls"]}" id="s{i}"><div class="kicker">{esc(s["kicker"])}</div><div class="pg">{i} / {len(SL)}</div>'
                f'<div class="marca">SPREAD</div><h1>{esc(s["titulo"])}</h1>{s["corpo"]}<div class="fonte">Fonte: {esc(s["fonte"])}</div></section>')

page = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Spread · Fortuna Crédito · pitch</title>
<style>{CSS}</style></head><body>
<div id="wrap"><div id="deck">
{chr(10).join(secs)}
</div></div>
<div id="nav"><button id="prev" aria-label="Anterior">&#9664;</button><span id="pos"></span><button id="next" aria-label="Próximo">&#9654;</button></div>
<script>{JS}</script>
</body></html>"""
OUT.write_text(page, encoding="utf-8")
print("ok", OUT, len(SL), "slides")
