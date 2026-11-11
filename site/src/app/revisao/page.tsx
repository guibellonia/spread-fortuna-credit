import type { Metadata } from "next";
import { Revisao } from "@/components/Revisao";

export const metadata: Metadata = { title: "Spread · Revisão" };

export default function Page() {
  return <Revisao />;
}
