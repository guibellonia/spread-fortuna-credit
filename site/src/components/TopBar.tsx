import type { ReactNode } from "react";

// Links comuns (sem next/link): no export estático do Next 16 o prefetch das rotas pede arquivos com nome
// diferente do que o build grava e dá 404 no GitHub Pages. Com duas páginas, recarregar não pesa.
const BASE = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

type Aba = "geral" | "historico" | "simulador" | "revisao";

export function TopBar({ ativo, fim }: { ativo: Aba; fim?: ReactNode }) {
  const aba = (id: Aba, href: string, nome: string) => (
    <a className={`tab${ativo === id ? " is-active" : " sl"}`} aria-current={ativo === id ? "page" : undefined} href={href}>
      {nome}
    </a>
  );
  return (
    <header className="topbar">
      <a className="brand" href={`${BASE}/../`}>
        <span className="logo" aria-hidden>S</span>
        <span className="brand-name">Spread</span>
        <span className="brand-sub">Fortuna Crédito</span>
      </a>
      <nav className="tabs" aria-label="Seções">
        {aba("geral", `${BASE}/`, "Visão geral")}
        {aba("historico", `${BASE}/historico/`, "Histórico")}
        {aba("simulador", `${BASE}/simulador/`, "Simulador")}
        {aba("revisao", `${BASE}/revisao/`, "Revisão")}
        <a className="tab sl" href={`${BASE}/../`}>Time</a>
      </nav>
      <span className="stamp">{fim}</span>
    </header>
  );
}
