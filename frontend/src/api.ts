import type { MissionEvent, MissionSnapshot } from "./contracts";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) throw new Error(`API ${response.status}: ${response.statusText}`);
  return response.json() as Promise<T>;
}

async function requestVoid(path: string, init?: RequestInit): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) throw new Error(`API ${response.status}: ${response.statusText}`);
}

export const missionApi = {
  create: (body: object) => request<{ id: string }>("/api/missions", { method: "POST", body: JSON.stringify(body) }),
  start: (id: string) => request<MissionSnapshot>(`/api/missions/${encodeURIComponent(id)}/start`, { method: "POST" }),
  stop: (id: string) => requestVoid(`/api/missions/${encodeURIComponent(id)}/stop`, { method: "POST" }),
  get: (id: string) => request<MissionSnapshot>(`/api/missions/${encodeURIComponent(id)}`),
  report: (id: string) => request<MissionSnapshot>(`/api/missions/${encodeURIComponent(id)}/report`),
  events(id: string, onEvent: (event: MissionEvent) => void, onState: (state: "connected" | "reconnecting") => void) {
    const source = new EventSource(`${API_BASE}/api/missions/${encodeURIComponent(id)}/events`);
    source.onopen = () => onState("connected");
    source.onmessage = (message) => { try { onEvent(JSON.parse(message.data) as MissionEvent); } catch { /* malformed events are ignored, never trusted */ } };
    source.onerror = () => onState("reconnecting");
    return () => source.close();
  }
};
