import { setOptions } from "@googlemaps/js-api-loader";

// setOptions() must run before the first importLibrary() call anywhere in the
// app, but different pages use the Maps JS SDK independently (Map.vue for the
// map itself, Home.vue for Places Autocomplete, services/directions.js for
// routing) — whichever loads first must not assume Map.vue already did this.
let configured = false;

export function ensureGoogleMapsConfigured() {
  if (configured) return;
  setOptions({ key: import.meta.env.VITE_GOOGLE_MAPS_API_KEY, v: "weekly" });
  configured = true;
}
