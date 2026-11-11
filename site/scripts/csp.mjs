// Pós-build: grava uma Content-Security-Policy em cada HTML do export estático.
// O GitHub Pages não deixa configurar cabeçalhos, então a política vai numa <meta>, logo após o charset.
// Os <script> inline do Next entram por hash (sha256), sem 'unsafe-inline' para script.
import { createHash } from "node:crypto";
import { readdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(raiz, "out");
const { bureauOrigin, supabaseUrl } = JSON.parse(await readFile(join(raiz, "site.config.json"), "utf8"));
if (!/^https:\/\/[a-z0-9.-]+$/i.test(bureauOrigin)) throw new Error("bureauOrigin inválido em site.config.json");
if (supabaseUrl && !/^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(supabaseUrl)) throw new Error("supabaseUrl inválido em site.config.json");
// o painel de revisão fala com a Data API, o Auth e as Edge Functions do projeto (mesma origem)
const conexoes = [bureauOrigin, supabaseUrl].filter(Boolean).join(" ");

const hash = (s) => `'sha256-${createHash("sha256").update(s, "utf8").digest("base64")}'`;

async function* paginas(dir) {
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* paginas(p);
    else if (e.name.endsWith(".html")) yield p;
  }
}

let total = 0;
for await (const arq of paginas(out)) {
  let doc = await readFile(arq, "utf8");
  if (doc.includes('http-equiv="Content-Security-Policy"')) continue;
  const inline = [...doc.matchAll(/<script\b(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => hash(m[1]));
  const csp = [
    "default-src 'self'",
    `script-src 'self' ${[...new Set(inline)].join(" ")}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    `connect-src 'self' ${conexoes}`,
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-src 'none'",
    "worker-src 'none'",
    "upgrade-insecure-requests",
  ].join("; ");
  const meta = `<meta http-equiv="Content-Security-Policy" content="${csp}"/>`;
  const charset = doc.match(/<meta charSet="utf-8"\s*\/?>/i);
  if (charset) doc = doc.replace(charset[0], charset[0] + meta);
  else doc = doc.replace(/<head[^>]*>/i, (h) => h + meta);
  if (!doc.includes(meta)) throw new Error(`não consegui inserir a CSP em ${arq}`);
  await writeFile(arq, doc);
  total++;
}
console.log(`CSP gravada em ${total} página(s)`);
