import type { Metadata, Viewport } from "next";
import { Montserrat, Poppins } from "next/font/google";
import type { ReactNode } from "react";
import "./globals.css";

// As fontes são baixadas no build e servidas pelo próprio site (nada é carregado do Google no navegador).
const poppins = Poppins({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-poppins", display: "swap" });
const montserrat = Montserrat({ subsets: ["latin"], weight: ["600", "700"], variable: "--font-montserrat", display: "swap" });

export const metadata: Metadata = {
  title: "Spread · Painel Fortuna",
  description: "Decisões de crédito dos pedidos novos, padrões do histórico e saúde da API do bureau.",
  referrer: "no-referrer",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { themeColor: "#f4f6fa", colorScheme: "light" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" className={`${poppins.variable} ${montserrat.variable}`}>
      <body>{children}</body>
    </html>
  );
}
