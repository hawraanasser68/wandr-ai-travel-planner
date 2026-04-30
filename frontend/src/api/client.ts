/**
 * API client — thin wrappers around fetch.
 * All requests go to /auth or /agent which Vite proxies to FastAPI.
 */

import { useAuthStore } from "../store/auth";

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function register(email: string, password: string, webhookEmail?: string) {
  const res = await fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, webhook_email: webhookEmail || null }),
  });
  return handleResponse<{ access_token: string }>(res);
}

export async function login(email: string, password: string) {
  const res = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handleResponse<{ access_token: string }>(res);
}

export async function getMe() {
  const res = await fetch("/auth/me", { headers: authHeaders() });
  return handleResponse<{ email: string }>(res);
}

// ── Agent streaming ───────────────────────────────────────────────────────────

export interface StreamChunk {
  type: "token" | "tool_call" | "tool_result" | "done" | "error";
  content: string;
  run_id: string | null;
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

/**
 * Calls POST /agent/chat and yields StreamChunk objects as they arrive.
 * Sends the full conversation history so the agent has multi-turn context.
 */
export async function* streamChat(
  query: string,
  history: HistoryMessage[] = []
): AsyncGenerator<StreamChunk> {
  const res = await fetch("/agent/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ query, history }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "Chat request failed");
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const chunk: StreamChunk = JSON.parse(line.slice(6));
          yield chunk;
        } catch {
          // ignore malformed lines
        }
      }
    }
  }
}

// ── Run history ───────────────────────────────────────────────────────────────

export interface AgentRun {
  id: string;
  query: string;
  response: string | null;
  tools_used: string[];
  created_at: string;
}

export async function getRuns(): Promise<AgentRun[]> {
  const res = await fetch("/agent/runs", { headers: authHeaders() });
  return handleResponse<AgentRun[]>(res);
}

export async function getRun(id: string): Promise<AgentRun> {
  const res = await fetch(`/agent/runs/${id}`, { headers: authHeaders() });
  return handleResponse<AgentRun>(res);
}

// ── Geocoding (Nominatim / OpenStreetMap — free, no key) ──────────────────────

export interface GeoResult {
  name: string;
  lat: number;
  lng: number;
}

export async function geocode(place: string): Promise<GeoResult | null> {
  try {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(place)}&format=json&limit=1`;
    const res = await fetch(url, {
      headers: { "User-Agent": "AITravelPlanner/1.0" },
    });
    const data = await res.json();
    if (data.length === 0) return null;
    return { name: place, lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
  } catch {
    return null;
  }
}
