const inteiro = new Intl.NumberFormat("pt-BR");
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export const int = (n: number) => inteiro.format(n);

export const pct = (x: number, casas = 1) =>
  new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: casas, maximumFractionDigits: casas }).format(x);

const dec = (x: number, casas: number) =>
  x.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

/** R$ 8,86 mi · R$ 861 mil · R$ 920 */
export function brl(v: number) {
  const a = Math.abs(v);
  if (a >= 1e6) return `R$ ${dec(v / 1e6, 2)} mi`;
  if (a >= 1e3) return `R$ ${dec(v / 1e3, a >= 1e5 ? 0 : 1)} mil`;
  return `R$ ${dec(v, 0)}`;
}

/** +R$ 1,29 mi · −R$ 141 mil */
export const brlSinal = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${brl(Math.abs(v))}`;

const real = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
/** R$ 12.100,00 */
export const moeda = (v: number) => real.format(v);

/** ISO com fuso -> "11/11/26 10:45" no horário de quem vê */
export const quando = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

export const segundos = (s: number) => `${dec(s, s < 1 ? 2 : 1)} s`;

/** "2024-10" -> "out/24" */
export function mes(m: string) {
  const [a, n] = m.split("-");
  return `${MESES[Number(n) - 1]}/${a.slice(2)}`;
}

/** "2026-11-11T09:51" -> "11/11/2026 09:51" */
export function dataHora(s: string) {
  const [d, h] = s.split("T");
  const [a, m, dia] = d.split("-");
  return `${dia}/${m}/${a}${h ? ` ${h.slice(0, 5)}` : ""}`;
}

export const VINCULO: Record<string, string> = {
  assalariado: "Assalariado",
  autonomo: "Autônomo",
  aposentado: "Aposentado",
  empresario: "Empresário",
};
