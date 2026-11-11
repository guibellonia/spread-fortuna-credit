/* Ícone de chat do Hermes no canto inferior direito; abre o chat (servido pela API no Railway) num painel.
   Um arquivo só, sem dependências. Carregado pelo painel (layout.tsx) e pela página inicial (index.html).
   Acesso: o login de membro do painel (Supabase, o mesmo da aba Revisão) é repassado ao chat por postMessage,
   só para a origem do Hermes. Nenhuma chave fica neste código. */
(function () {
  "use strict";
  if (window.__hermesWidget) return;
  window.__hermesWidget = true;

  var URL_CHAT = "https://hermes-production-5adc5d67.up.railway.app/";
  var ORIGEM_CHAT = "https://hermes-production-5adc5d67.up.railway.app";

  // login de membro (Supabase, o mesmo da aba Revisão). A chave anon é pública por desenho (site.config.json).
  var SUPABASE = "https://vjxwagiqgecsscoogxln.supabase.co";
  var ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZqeHdhZ2lxZ2Vjc3Njb29neGxuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQ0MDI0NzYsImV4cCI6MjEwOTk3ODQ3Nn0.h-DifBlWRtYa3QkChzlqPN_mfCVhOo_EMcGDOsVNoOw";
  var CHAVE_SESSAO = "spread-painel";  // mesma chave que o painel (site/src/lib/supabase.ts) usa

  function sessao() { try { return JSON.parse(localStorage.getItem(CHAVE_SESSAO) || "null"); } catch (e) { return null; } }
  function guardarSessao(s) {
    try {
      if (s && s.expires_in && !s.expires_at) s.expires_at = Math.floor(Date.now() / 1000) + s.expires_in;
      localStorage.setItem(CHAVE_SESSAO, JSON.stringify(s));
    } catch (e) {}
  }
  function tokenDoPainel() {
    var s = sessao();
    var t = s && (s.access_token || (s.currentSession && s.currentSession.access_token));
    var exp = s && (s.expires_at || (s.currentSession && s.currentSession.expires_at));
    if (!t || (exp && exp * 1000 < Date.now() + 30000)) return "";
    return t;
  }
  function autenticar(corpo, tipo) {
    return fetch(SUPABASE + "/auth/v1/token?grant_type=" + tipo, {
      method: "POST", headers: { "Content-Type": "application/json", apikey: ANON }, body: JSON.stringify(corpo)
    }).then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.error_description || j.msg || "falha no login"); return j; }); });
  }
  function renovar() {  // login vencido: tenta o refresh_token antes de pedir senha de novo
    var s = sessao();
    if (tokenDoPainel() || !s || !s.refresh_token) return Promise.resolve(tokenDoPainel());
    return autenticar({ refresh_token: s.refresh_token }, "refresh_token")
      .then(function (j) { guardarSessao(j); return j.access_token; })
      .catch(function () { return ""; });
  }

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
    "#hermes-login{display:none;flex-direction:column;gap:10px;padding:20px;font:14px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif;color:#1e293b}" +
    "#hermes-login input{padding:10px;border:1px solid #cbd5e1;border-radius:8px;font:inherit}" +
    "#hermes-login button{padding:10px;border:0;border-radius:8px;background:#1f3a8a;color:#fff;font:600 14px system-ui,sans-serif;cursor:pointer}" +
    "#hermes-login button:disabled{opacity:.6}.hermes-erro{color:#b42318;min-height:1em;margin:0}" +
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

    var carregado = false, frame = null;
    var login = document.createElement("form");
    login.id = "hermes-login";
    login.innerHTML = "<p>Entre com o seu e-mail de membro do time (o mesmo da aba Revisão).</p>" +
      '<input type="email" name="email" placeholder="e-mail" autocomplete="username" required>' +
      '<input type="password" name="senha" placeholder="senha" autocomplete="current-password" required>' +
      '<button type="submit">Entrar</button><p class="hermes-erro" aria-live="polite"></p>';
    login.addEventListener("submit", function (e) {
      e.preventDefault();
      var b = login.querySelector("button"), erro = login.querySelector(".hermes-erro");
      b.disabled = true; erro.textContent = "";
      autenticar({ email: login.email.value.trim(), password: login.senha.value }, "password")
        .then(function (j) { guardarSessao(j); login.senha.value = ""; mostrarChat(); })
        .catch(function (err) { erro.textContent = "Não foi possível entrar: " + err.message; })
        .then(function () { b.disabled = false; });
    });
    function enviarToken() {
      if (frame && frame.contentWindow) {
        frame.contentWindow.postMessage({ tipo: "hermes-token", token: tokenDoPainel() }, ORIGEM_CHAT);
      }
    }
    function mostrarChat() {
      login.style.display = "none";
      if (!carregado) {
        var f = document.createElement("iframe");
        f.src = URL_CHAT;
        f.title = "Chat do Hermes";
        f.referrerPolicy = "no-referrer";
        f.addEventListener("load", enviarToken);
        painel.appendChild(f);
        frame = f;
        carregado = true;
        setInterval(function () { renovar().then(enviarToken); }, 60000);  // repassa o token renovado
      } else {
        frame.style.display = "block";
        enviarToken();
      }
    }
    function abrir(sim) {
      if (sim) {
        renovar().then(function (t) {
          if (t) mostrarChat();
          else { login.style.display = "flex"; if (frame) frame.style.display = "none"; login.email.focus(); }
        });
      }
      painel.classList.toggle("aberto", sim);

      btn.setAttribute("aria-expanded", sim ? "true" : "false");
      btn.setAttribute("aria-label", sim ? "Fechar o chat do Hermes" : "Abrir o chat do Hermes");
    }
    btn.addEventListener("click", function () { abrir(!painel.classList.contains("aberto")); });
    painel.querySelector("#hermes-topo button").addEventListener("click", function () { abrir(false); btn.focus(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && painel.classList.contains("aberto")) abrir(false); });

    painel.appendChild(login);
    document.body.appendChild(painel);
    document.body.appendChild(btn);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", montar);
  else montar();
})();
