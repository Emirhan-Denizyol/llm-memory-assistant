// src/api/types.ts

export type Role = "user" | "assistant";

/* ---------- Chat tipleri ---------- */

export interface ChatRequest {
  user_id: string;
  session_id: string;
  message: string;
  topk_local: number;
  topk_global: number;
  stm_max_turns: number;
  return_sources: boolean;
}

export interface ChatSource {
  scope: string;
  id: number;
  session_id: string;
  score: number;
  snippet: string;
  meta: Record<string, unknown>;
}

export interface ChatResponse {
  reply: string;
  used_stm_turns: number;
  sources: ChatSource[];
}

export interface ChatMessage {
  role: Role;
  content: string;
}

/* ---------- Memory tipleri ---------- */

/*export type MemoryScope = "stm" | "ltm_local" | "ltm_global" | string; */
export type MemoryScope = "stm" | "local" | "global";

export interface MemoryBasePayload {
  scope: MemoryScope;
  user_id: string;
  session_id: string;
  text: string;
  meta?: Record<string, unknown>;
}

export interface MemoryRecord extends MemoryBasePayload {
  id: number;
  emb_version: string;
  model: string;
  dim: number;
  created_at: number;
  updated_at: number;
}

export interface MemorySearchRequest {
  user_id: string;
  q: string;
  scope: MemoryScope;
  session_id: string;
  topk: number;
}

export interface MemorySearchResponse {
  page: number;
  page_size: number;
  total: number;
  items: MemoryRecord[];
}

export type Role = "user" | "assistant";

/* ... senin mevcut ChatRequest / ChatResponse / Memory tiplerin ... */

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
}
