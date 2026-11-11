import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import config from "../../site.config.json";

// A chave anon é pública por desenho: quem protege os dados é o RLS do schema painel (login + lista de membros).
export const supabaseConfigurado = /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(config.supabaseUrl) && config.supabaseAnonKey.length > 20;

let cliente: SupabaseClient<any, "painel"> | null = null;

export function supabase() {
  if (!supabaseConfigurado) return null;
  cliente ??= createClient<any, "painel">(config.supabaseUrl, config.supabaseAnonKey, {
    db: { schema: "painel" },
    auth: { persistSession: true, autoRefreshToken: true, storageKey: "spread-painel" },
  });
  return cliente;
}

export type Decisao = {
  id_pedido: string;
  id_cliente: string;
  valor_solicitado: number;
  prazo_meses: number;
  decisao: "APROVADO" | "NEGADO";
  valor_aprovado: number;
  motivo: string | null;
  p_nao_paga: number | null;
  ganho_esperado: number | null;
  atual_decisao: "APROVADO" | "NEGADO" | null;
  atual_valor: number | null;
  fonte: string;
  publicado_em: string;
  revisao_acao: "confirmar" | "aprovar" | "negar" | null;
  revisao_valor: number | null;
  revisao_justificativa: string | null;
  revisao_por: string | null;
  revisao_em: string | null;
  decisao_final: "APROVADO" | "NEGADO";
  valor_final: number;
  diverge_atual: boolean;
};

export type Revisao = {
  id: number;
  id_pedido: string;
  acao: "confirmar" | "aprovar" | "negar";
  valor: number | null;
  justificativa: string;
  decisao_ia: string;
  valor_ia: number;
  analista_email: string;
  criado_em: string;
};

export type Bureau = {
  dados: Record<string, number | string>;
  tentativas: number;
  ms: number;
  consultado_em: string;
  fonte: "api" | "cache";
};
