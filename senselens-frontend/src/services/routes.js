import { apiGet, delay, API_BASE } from "./http";

// Fallback starting point when real geolocation isn't available (denied,
// unsupported, or too inaccurate) — Flinders Street Station, matching the
// old fixed-origin mock behaviour and the map mock data (see services/map.js).
// Also happens to sit right next to the live pedestrian sensors currently
// reporting the most data (Flinders Ln / Degraves St), so it's a reasonable
// default for seeing a real sensory score without granting location.
export const FALLBACK_ORIGIN = { lat: -37.8183, lng: 144.9671 };

const mockRouteOptions = [
  {
    id: "quiet-flinders",
    tag: "RECOMMENDED FOR YOU",
    level: "low",
    levelLabel: "LOW SENSORY",
    name: "Quiet Route via Flinders Lane",
    description: "Fewer crowds, less noise, leafy path.",
    duration: "18 min",
    footnote: "Calmest route",
    recommended: true,
    factors: [],
    transit: { stop: "Flinders Street Station", type: "train", walk: "4 min" },
  },
  {
    id: "balanced-collins",
    tag: "Alt route",
    level: "medium",
    levelLabel: "MEDIUM SENSORY",
    name: "Balanced Route via Collins St",
    description: "Slightly busy intersection near retail zone. Medium pace.",
    duration: "14 min",
    factors: [{ icon: "users", label: "Moderate pedestrian volume" }],
    transit: { stop: "Collins St/Elizabeth St", type: "tram", walk: "2 min" },
  },
  {
    id: "direct-bourke",
    tag: "Fastest route",
    level: "high",
    levelLabel: "HIGH SENSORY",
    name: "Direct Route via Bourke St Mall",
    description: "High tram noise, street performances, very dense crowds.",
    duration: "12 min",
    factors: [
      { icon: "users", label: "Very dense crowds" },
      { icon: "megaphone", label: "Street performances" },
    ],
    transit: { stop: "Melbourne Central Station", type: "train", walk: "3 min" },
  },
];

// destinationPoint is only set once the user picks a real place from Home's
// autocomplete — the backend computes real sensory-scored routes (crowd
// percentile against live pedestrian sensors) when given real coordinates,
// vs. just a destination string. origin defaults to Flinders Street Station
// when real geolocation isn't available.
export async function getRouteOptions(destination, destinationPoint, origin = FALLBACK_ORIGIN) {
  // No backend configured at all (local dev without .env) — mock is the only
  // option. Once a backend is configured, a failed request throws instead of
  // silently swapping in mock data, so a genuine outage shows an error state
  // rather than pretending to be a real route.
  if (!API_BASE) {
    await delay(500);
    return mockRouteOptions;
  }

  const params = new URLSearchParams({ destination });
  if (destinationPoint) {
    params.set("originLat", origin.lat);
    params.set("originLng", origin.lng);
    params.set("destinationLat", destinationPoint.lat);
    params.set("destinationLng", destinationPoint.lng);
  }

  return apiGet(`/routes?${params.toString()}`);
}
