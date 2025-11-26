// src/api/client.ts

import axios from "axios";
import type {
  ChatRequest,
  ChatResponse,
  MemoryBasePayload,
  MemorySearchRequest,
  MemorySearchResponse,
  MemoryRecord
} from "./types";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 30000
});

// Vite env'den API key
const API_KEY = import.meta.env.VITE_JETLINK_API_KEY as string | undefined;

// Her isteğe X-API-Key header'ı ekle
api.interceptors.request.use((config) => {
  if (API_KEY) {
    (config.headers ??= {})["X-API-Key"] = API_KEY;
  }
  return config;
});

/* ---------- Chat ---------- */

export async function sendChatMessage(
  payload: ChatRequest
): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>("/api/chat", payload);
  return response.data;
}

/* ---------- Memory ---------- */

export async function addLocalMemory(
  payload: MemoryBasePayload
): Promise<MemoryRecord> {
  const response = await api.post<MemoryRecord>("/api/memory/local", payload);
  return response.data;
}

export async function addGlobalMemory(
  payload: MemoryBasePayload
): Promise<MemoryRecord> {
  const response = await api.post<MemoryRecord>("/api/memory/global", payload);
  return response.data;
}

export async function searchMemory(
  payload: MemorySearchRequest
): Promise<MemorySearchResponse> {
  const response = await api.post<MemorySearchResponse>(
    "/api/memory/search",
    payload
  );
  return response.data;
}
