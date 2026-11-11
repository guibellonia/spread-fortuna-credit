// Confere que o motor TS (src/lib/motor.ts) dá as mesmas decisões que o Python nos 2.000 pedidos novos.
// Os arquivos vêm de supabase/publicar_motor.py em data/cache/motor/ (fora do Git: têm ids e dados de cliente).
// Uso, da raiz do repositório: node --experimental-strip-types site/scripts/paridade-motor.mjs
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { decidir, sinais } from "../src/lib/motor.ts";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const ler = (n) => JSON.parse(readFileSync(join(raiz, "data", "cache", "motor", n), "utf8"));
const motor = ler("modelo.json");
const { entradas, esperado } = ler("paridade.json");

const erros = [];
let maxRisco = 0;
entradas.forEach((e, i) => {
  const py = esperado[i];
  const ts = decidir(e, motor);
  maxRisco = Math.max(maxRisco, Math.abs(Math.round(ts.risco * 1e4) / 1e4 - py.p_nao_paga));
  const dif = [];
  if (ts.aprova !== py.aprova) dif.push(`aprova ${ts.aprova} × ${py.aprova}`);
  if (Math.abs(ts.valor - py.valor) > 0.005) dif.push(`valor ${ts.valor} × ${py.valor}`);
  if (ts.motivo !== py.motivo) dif.push(`motivo "${ts.motivo}" × "${py.motivo}"`);
  if (Math.abs(ts.ganho - py.ganho_esperado) > 0.01) dif.push(`ganho ${ts.ganho.toFixed(2)} × ${py.ganho_esperado}`);
  // sinais da faixa de risco: o Python só guarda o texto para quem passou nas barreiras
  if (py.pontos_detalhe && py.pontos_detalhe !== "barrado antes da pontuação") {
    const txt = sinais(e, ts.valor).map((s) => `${s.peso > 0 ? "+" : "−"}1 ${s.nome}`).join(", ") || "nenhum sinal";
    if (txt !== py.pontos_detalhe) dif.push(`sinais "${txt}" × "${py.pontos_detalhe}"`);
  }
  if (dif.length) erros.push(`pedido ${i + 1}: ${dif.join("; ")}`);
});

console.log(`motor TS × Python: ${entradas.length - erros.length} de ${entradas.length} iguais` +
  ` (decisão, valor, motivo, ganho e sinais da faixa) · maior diferença de risco ${maxRisco.toFixed(4)}`);
if (erros.length || maxRisco > 0.0001) {
  console.error(erros.slice(0, 10).join("\n"));
  process.exit(1);
}
