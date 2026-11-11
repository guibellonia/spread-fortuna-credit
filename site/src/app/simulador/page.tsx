import type { Metadata } from "next";
import { Simulador } from "@/components/Simulador";

export const metadata: Metadata = { title: "Spread · Simulador" };

export default function Page() {
  return <Simulador />;
}
