export const API_BASE = import.meta.env.VITE_API_BASE || "";

// Simulates network latency for mock data so loading states are visible
// during development. Remove call sites once real endpoints are wired up —
// fetch() already has real latency.
export function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}
