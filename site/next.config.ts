import type { NextConfig } from "next";

// Export estático para o GitHub Pages. O workflow passa o caminho de publicação
// (ex.: /spread-fortuna-credit/dashboard); localmente fica vazio.
const basePath = process.env.PAGES_BASE_PATH ?? "";

const config: NextConfig = {
  output: "export",
  basePath,
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
  productionBrowserSourceMaps: false,
};

export default config;
