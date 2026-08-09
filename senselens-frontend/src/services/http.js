export const API_BASE = import.meta.env.VITE_API_BASE || "";

// Simulates network latency for mock data so loading states are visible
// during development. Remove call sites once real endpoints are wired up —
// fetch() already has real latency.
export function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function apiGet(path, { notFoundIsNull = false } = {}) {
  const res = await fetch(`${API_BASE}${path}`);
  // Some endpoints (e.g. forecast) 404 instead of returning `null` when
  // there's nothing to report for this route — that's a valid empty state,
  // not a failure, so callers can opt in to treating it as one.
  if (notFoundIsNull && res.status === 404) return null;
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

// Tries the real backend first (only if VITE_API_BASE is configured), falling
// back to mock data if it's unset or the request fails — so the app keeps
// working with mocks during local dev / while the backend is still unstable,
// and switches over automatically the moment API_BASE points at a working API.
export async function withApiFallback(request, fallback) {
  if (!API_BASE) return fallback();
  try {
    return await request();
  } catch (err) {
    console.warn("API request failed, using mock data instead:", err);
    return fallback();
  }
}
