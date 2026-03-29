import type { ChatRequest, ChatResponse } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${detail}`);
  }

  return res.json() as Promise<ChatResponse>;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const base = API_BASE.replace(/\/api$/, "");
    const res = await fetch(`${base}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}
