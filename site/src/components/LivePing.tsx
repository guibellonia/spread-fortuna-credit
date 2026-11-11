"use client";

import { useCallback, useEffect, useState } from "react";
import config from "../../site.config.json";
import { IconButton, IconRefresh } from "./ui";

type Estado = { s: "testando" } | { s: "ok"; ms: number } | { s: "erro" };

/**
 * Teste ao vivo do GET /health do bureau, feito do navegador de quem abre o painel.
 * Não usa token (o /health é aberto) e não lê a resposta: a API não libera CORS, então o fetch
 * vai em modo no-cors e só mede se o servidor respondeu e em quanto tempo.
 */
export function LivePing() {
  const [st, setSt] = useState<Estado>({ s: "testando" });

  const testar = useCallback(async () => {
    setSt({ s: "testando" });
    const t0 = performance.now();
    try {
      await fetch(`${config.bureauOrigin}/health`, {
        mode: "no-cors",
        cache: "no-store",
        credentials: "omit",
        referrerPolicy: "no-referrer",
        signal: AbortSignal.timeout(10000),
      });
      setSt({ s: "ok", ms: Math.round(performance.now() - t0) });
    } catch {
      setSt({ s: "erro" });
    }
  }, []);

  useEffect(() => {
    testar();
  }, [testar]);

  const texto = st.s === "ok" ? `Agora: respondeu em ${st.ms} ms` : st.s === "erro" ? "Agora: sem resposta" : "Testando…";
  return (
    <>
      <span className={`live is-${st.s}`} role="status" title="Teste ao vivo: o bureau está respondendo agora?">
        <i aria-hidden />
        {texto}
      </span>
      <IconButton label="Testar de novo" onClick={testar}><IconRefresh /></IconButton>
    </>
  );
}
