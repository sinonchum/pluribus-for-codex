import type {
  DemoSnapshot,
  MemoryCapsule,
  MemoryInstall,
  MemoryStar,
  UsageReceipt,
} from "./contracts";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`API ${response.status}: ${detail || response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function memoryQuery(options: { query?: string; tag?: string; sort?: string } = {}) {
  const params = new URLSearchParams();
  if (options.query) params.set("query", options.query);
  if (options.tag) params.set("tag", options.tag);
  if (options.sort) params.set("sort", options.sort);
  const query = params.toString();
  return `/api/memories${query ? `?${query}` : ""}`;
}

export const memoryApi = {
  list: (options?: { query?: string; tag?: string; sort?: string }) =>
    request<MemoryCapsule[]>(memoryQuery(options)),
  create: (capsule: MemoryCapsule) =>
    request<MemoryCapsule>("/api/memories", { method: "POST", body: JSON.stringify(capsule) }),
  detail: (slug: string) => request<MemoryCapsule>(`/api/memories/${encodeURIComponent(slug)}`),
  star: (slug: string) =>
    request<MemoryStar>(`/api/memories/${encodeURIComponent(slug)}/star`, { method: "POST" }),
  install: (slug: string) =>
    request<MemoryInstall>(`/api/memories/${encodeURIComponent(slug)}/install`, { method: "POST" }),
  installed: () => request<MemoryCapsule[]>("/api/installed"),
  createReceipt: (receipt: UsageReceipt) =>
    request<UsageReceipt>("/api/usage-receipts", { method: "POST", body: JSON.stringify(receipt) }),
  receipt: (id: string) => request<UsageReceipt>(`/api/usage-receipts/${encodeURIComponent(id)}`),
  demoSnapshot: () => request<DemoSnapshot>("/api/demo/snapshot"),
};
