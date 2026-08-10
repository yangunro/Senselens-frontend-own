import { ref } from "vue";

const MELBOURNE_CBD = { lat: -37.8136, lng: 144.9631 };

// Shared destination/starting-point search behaviour (debounced suggestions +
// coordinate lookup on selection) — used by both search boxes on Home.vue,
// each with its own independent state and Mapbox search session.
export function useMapboxSearch() {
  const query = ref("");
  // Set only when the user picks a real suggestion — free-typed text with no
  // selection has no coordinates, so callers fall back to geocoding it.
  const point = ref(null);
  const suggestions = ref([]);
  const showSuggestions = ref(false);
  let sessionToken = crypto.randomUUID();
  let debounceTimer = null;
  let pendingRetrieve = null;

  function onInput() {
    point.value = null;
    showSuggestions.value = true;
    window.clearTimeout(debounceTimer);
    const q = query.value.trim();
    if (!q) {
      suggestions.value = [];
      return;
    }
    debounceTimer = window.setTimeout(() => fetchSuggestions(q), 250);
  }

  async function fetchSuggestions(q) {
    try {
      const params = new URLSearchParams({
        q,
        access_token: import.meta.env.VITE_MAPBOX_ACCESS_TOKEN,
        session_token: sessionToken,
        proximity: `${MELBOURNE_CBD.lng},${MELBOURNE_CBD.lat}`,
        country: "au",
        limit: "5",
      });
      const res = await fetch(`https://api.mapbox.com/search/searchbox/v1/suggest?${params}`);
      if (!res.ok) throw new Error(`Suggest failed: ${res.status}`);
      const data = await res.json();
      suggestions.value = data.suggestions ?? [];
    } catch (err) {
      // Suggestions are a nice-to-have — if the request fails, the plain
      // text input still works via the caller's geocoding fallback.
      console.warn("Search suggestions unavailable:", err);
      suggestions.value = [];
    }
  }

  function select(suggestion) {
    showSuggestions.value = false;
    query.value = suggestion.place_formatted ? `${suggestion.name}, ${suggestion.place_formatted}` : suggestion.name;
    suggestions.value = [];
    pendingRetrieve = (async () => {
      try {
        const params = new URLSearchParams({
          access_token: import.meta.env.VITE_MAPBOX_ACCESS_TOKEN,
          session_token: sessionToken,
        });
        const res = await fetch(`https://api.mapbox.com/search/searchbox/v1/retrieve/${suggestion.mapbox_id}?${params}`);
        if (!res.ok) throw new Error(`Retrieve failed: ${res.status}`);
        const data = await res.json();
        const coordinates = data.features?.[0]?.geometry?.coordinates;
        if (coordinates) point.value = { lat: coordinates[1], lng: coordinates[0] };
      } catch (err) {
        console.warn("Failed to resolve the selected place:", err);
      } finally {
        sessionToken = crypto.randomUUID();
      }
    })();
  }

  // Tapping a submit button right after picking a suggestion must wait for
  // the coordinate lookup instead of racing off with a still-null point.
  async function waitForPending() {
    if (pendingRetrieve) {
      await pendingRetrieve;
      pendingRetrieve = null;
    }
  }

  return { query, point, suggestions, showSuggestions, onInput, select, waitForPending };
}
