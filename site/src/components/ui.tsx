"use client";

import { useId, useRef, useState, type CSSProperties, type FocusEvent, type PointerEvent, type ReactNode } from "react";

/* Ícones desenhados à mão (traço de 2px, 24px), sem fonte externa. */
const svg = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2,
  strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };

export const IconTable = () => (
  <svg {...svg}><rect x="3.5" y="4.5" width="17" height="15" rx="2.5" /><path d="M3.5 9.5h17M3.5 14.5h17M9.5 9.5v10" /></svg>
);
export const IconChart = () => (
  <svg {...svg}><path d="M5 19.5V12M10 19.5V6M15 19.5v-9M20 19.5V15" /></svg>
);
export const IconRefresh = () => (
  <svg {...svg}><path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3" /><path d="M19.5 4.5v4h-4" /></svg>
);
export const IconCheck = () => (
  <svg {...svg} width={18} height={18}><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
);
export const IconUp = () => (
  <svg {...svg} width={16} height={16}><path d="M12 19V5M6 11l6-6 6 6" /></svg>
);
export const IconDown = () => (
  <svg {...svg} width={16} height={16}><path d="M12 5v14M6 13l6 6 6-6" /></svg>
);
export const IconSpark = () => (
  <svg {...svg} width={16} height={16}><path d="M12 3.5l1.9 5.2 5.1 1.8-5.1 1.9L12 17.5l-1.9-5.1L5 10.5l5.1-1.8z" /></svg>
);

export function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className="icon-btn sl" aria-label={label} title={label} onClick={onClick}>
      {children}
    </button>
  );
}

type CardProps = {
  title: string;
  area: string;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
};

export function Card({ title, area, actions, className = "", children }: CardProps) {
  const id = useId();
  return (
    <section className={`card ${className}`} style={{ gridArea: area }} aria-labelledby={id}>
      <header className="card-head">
        <h2 className="card-title" id={id}>{title}</h2>
        {actions && <div className="card-actions">{actions}</div>}
      </header>
      {children}
    </section>
  );
}

/** Cartão de gráfico: o botão alterna entre o gráfico e a tabela com os mesmos números. */
export function ChartCard({ table, actions, ...props }: CardProps & { table: ReactNode }) {
  const [tabela, setTabela] = useState(false);
  return (
    <Card
      {...props}
      actions={
        <>
          {actions}
          <IconButton label={tabela ? "Ver gráfico" : "Ver tabela"} onClick={() => setTabela(!tabela)}>
            {tabela ? <IconChart /> : <IconTable />}
          </IconButton>
        </>
      }
    >
      {tabela ? <div className="table-wrap">{table}</div> : props.children}
    </Card>
  );
}

/** Tooltip ancorado na marca (não no cursor): aparece igual no hover e no foco por teclado. */
export function useTip() {
  const box = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<{ x: number; y: number; content: ReactNode } | null>(null);

  const show = (el: Element, content: ReactNode) => {
    const b = box.current?.getBoundingClientRect();
    if (!b) return;
    const r = el.getBoundingClientRect();
    const x = Math.min(Math.max(r.left - b.left + r.width / 2, 90), b.width - 90);
    setTip({ x, y: r.top - b.top, content });
  };

  const bind = (content: ReactNode, label: string) => ({
    tabIndex: 0,
    "aria-label": label,
    onPointerEnter: (e: PointerEvent<HTMLElement>) => show(e.currentTarget, content),
    onPointerLeave: () => setTip(null),
    onFocus: (e: FocusEvent<HTMLElement>) => show(e.currentTarget, content),
    onBlur: () => setTip(null),
  });

  const node = tip ? (
    <div className="tip" role="tooltip" style={{ left: tip.x, top: tip.y } as CSSProperties}>
      {tip.content}
    </div>
  ) : null;

  return { box, bind, node };
}

export const vars = (v: Record<string, string | number>) => v as CSSProperties;
