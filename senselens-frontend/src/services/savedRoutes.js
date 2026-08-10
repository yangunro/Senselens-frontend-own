import { apiGet, apiPost, apiDelete, delay, withApiFallback } from "./http";

// Local-dev-without-backend fallback only — mirrors the shape the real API
// returns so SavedRoutes.vue doesn't need to know which one it's talking to.
let mockSavedRoutes = [];

export async function getSavedRoutes() {
  return withApiFallback(
    () => apiGet("/saved-routes"),
    async () => {
      await delay(300);
      return mockSavedRoutes;
    }
  );
}

export async function saveRoute({ label, origin, destination, level, distanceM, durationMin }) {
  return withApiFallback(
    () =>
      apiPost("/saved-routes", {
        label,
        origin,
        destination,
        level,
        distanceM: Math.round(distanceM),
        durationMin: Math.round(durationMin),
      }),
    async () => {
      await delay(300);
      const entry = {
        savedRouteId: `mock-${Date.now()}`,
        label,
        origin,
        destination,
        distanceM,
        durationMin,
        savedAt: new Date().toISOString(),
      };
      mockSavedRoutes = [entry, ...mockSavedRoutes];
      return entry;
    }
  );
}

export async function deleteSavedRoute(savedRouteId) {
  return withApiFallback(
    () => apiDelete(`/saved-routes/${savedRouteId}`),
    async () => {
      await delay(300);
      mockSavedRoutes = mockSavedRoutes.filter((r) => r.savedRouteId !== savedRouteId);
      return { success: true };
    }
  );
}
