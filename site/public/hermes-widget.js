/* Ícone de chat do Hermes no canto inferior direito; abre o chat (servido pela API no Railway) num painel.
   Um arquivo só, sem dependências. Carregado pelo painel (layout.tsx) e pela página inicial (index.html).
   A chave de acesso é digitada dentro do chat e nunca aparece neste código. */
(function () {
  "use strict";
  if (window.__hermesWidget) return;
  window.__hermesWidget = true;

  var URL_CHAT = "https://hermes-production-5adc5d67.up.railway.app/";

  var css =
    "#hermes-btn{position:fixed;right:20px;bottom:20px;z-index:2147483000;width:56px;height:56px;border-radius:50%;" +
    "border:0;cursor:pointer;background:#1f3a8a;color:#fff;box-shadow:0 6px 20px rgba(15,23,42,.25);display:flex;" +
    "align-items:center;justify-content:center;transition:transform .15s}" +
    "#hermes-btn:hover{transform:scale(1.06)}#hermes-btn:focus-visible{outline:3px solid #facc15;outline-offset:3px}" +
    "#hermes-btn svg{width:26px;height:26px}" +
    "#hermes-painel{position:fixed;right:20px;bottom:88px;z-index:2147483000;width:400px;height:620px;" +
    "max-height:calc(100vh - 108px);background:#fff;border-radius:14px;overflow:hidden;" +
    "box-shadow:0 12px 40px rgba(15,23,42,.3);display:none;flex-direction:column;border:1px solid #e2e8f0}" +
    "#hermes-painel.aberto{display:flex}" +
    "#hermes-topo{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:#1f3a8a;" +
    "color:#fff;font:600 14px/1.2 system-ui,-apple-system,'Segoe UI',sans-serif}" +
    "#hermes-topo button{background:none;border:0;color:#fff;font-size:20px;line-height:1;cursor:pointer;padding:2px 6px}" +
    "#hermes-painel iframe{flex:1;width:100%;border:0;background:#fff}" +
    "@media (max-width:640px){#hermes-painel{right:0;bottom:0;width:100vw;height:100dvh;max-height:none;border-radius:0}" +
    "#hermes-btn{right:16px;bottom:16px}}";

  function montar() {
    var estilo = document.createElement("style");
    estilo.textContent = css;
    document.head.appendChild(estilo);

    var btn = document.createElement("button");
    btn.id = "hermes-btn";
    btn.type = "button";
    btn.setAttribute("aria-label", "Abrir o chat do Hermes");
    btn.setAttribute("aria-expanded", "false");
    btn.title = "Pergunte ao Hermes";
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';

    var painel = document.createElement("div");
    painel.id = "hermes-painel";
    painel.setAttribute("role", "dialog");
    painel.setAttribute("aria-label", "Chat do Hermes");
    painel.innerHTML = '<div id="hermes-topo"><span>Hermes · assistente de risco</span>' +
      '<button type="button" aria-label="Fechar o chat">×</button></div>';

    var carregado = false;
    function abrir(sim) {
      if (sim && !carregado) {
        var f = document.createElement("iframe");
        f.src = URL_CHAT;
        f.title = "Chat do Hermes";
        f.referrerPolicy = "no-referrer";
        painel.appendChild(f);
        carregado = true;
      }
      painel.classList.toggle("aberto", sim);
      btn.setAttribute("aria-expanded", sim ? "true" : "false");
      btn.setAttribute("aria-label", sim ? "Fechar o chat do Hermes" : "Abrir o chat do Hermes");
    }
    btn.addEventListener("click", function () { abrir(!painel.classList.contains("aberto")); });
    painel.querySelector("#hermes-topo button").addEventListener("click", function () { abrir(false); btn.focus(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && painel.classList.contains("aberto")) abrir(false); });

    document.body.appendChild(painel);
    document.body.appendChild(btn);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", montar);
  else montar();
})();
