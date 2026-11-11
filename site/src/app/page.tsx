import { Dashboard } from "@/components/Dashboard";
import raw from "@/data/dashboard.json";
import type { Dados } from "@/lib/types";

export default function Page() {
  return <Dashboard dados={raw as Dados} />;
}
