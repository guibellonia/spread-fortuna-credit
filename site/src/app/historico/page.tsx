import type { Metadata } from "next";
import { Historico } from "@/components/Historico";
import raw from "@/data/historico.json";
import type { DadosHistorico } from "@/lib/types";

export const metadata: Metadata = { title: "Spread · Histórico" };

export default function Page() {
  return <Historico dados={raw as DadosHistorico} />;
}
