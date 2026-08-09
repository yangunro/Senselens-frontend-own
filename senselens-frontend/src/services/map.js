import { apiGet, delay, withApiFallback } from "./http";
import { decodePolyline } from "./polyline";

const mockRouteDetails = {
  "quiet-flinders": {
    name: "Quiet Route",
    level: "low",
    levelLabel: "LOW SENSORY",
    duration: "18 min",
    distance: "1.2 km",
    progress: 35,
    factors: [],
    transit: { stop: "Flinders Street Station", type: "train", walk: "4 min" },
    alternativeId: null,
    // Illustrative waypoints (not a real routed path) — plotted on the Google Map.
    path: [
      { lat: -37.8183, lng: 144.9671 }, // Flinders Street Station
      { lat: -37.814, lng: 144.9663 },
      { lat: -37.8099, lng: 144.9656 }, // near State Library Victoria
    ],
  },
  "balanced-collins": {
    name: "Balanced Route",
    level: "medium",
    levelLabel: "MEDIUM SENSORY",
    duration: "14 min",
    distance: "1.0 km",
    progress: 35,
    factors: [{ icon: "users", label: "Moderate pedestrian volume near retail zone" }],
    transit: { stop: "Collins St/Elizabeth St", type: "tram", walk: "2 min" },
    alternativeId: "quiet-flinders",
    path: [
      { lat: -37.8183, lng: 144.9671 }, // Flinders Street Station
      { lat: -37.8168, lng: 144.965 },
      { lat: -37.8155, lng: 144.9631 }, // Collins St / Elizabeth St
    ],
  },
  "direct-bourke": {
    name: "Direct Route",
    level: "high",
    levelLabel: "HIGH SENSORY",
    duration: "12 min",
    distance: "0.9 km",
    progress: 35,
    factors: [
      { icon: "users", label: "Very dense crowds" },
      { icon: "megaphone", label: "Street performances" },
    ],
    transit: { stop: "Melbourne Central Station", type: "train", walk: "3 min" },
    alternativeId: "quiet-flinders",
    path: [
      { lat: -37.8183, lng: 144.9671 }, // Flinders Street Station
      { lat: -37.8145, lng: 144.966 },
      { lat: -37.8103, lng: 144.9628 }, // Bourke St Mall / Melbourne Central
    ],
  },
};

// Predictive alerts (US 2.2): areas forecast to become overwhelming within the next hour,
// derived from historical pedestrian trend data on the backend.
const mockForecasts = {
  "quiet-flinders": null,
  "balanced-collins": {
    area: "Collins St intersection",
    etaMinutesStart: 25,
    etaMinutesEnd: 40,
    message: "Pedestrian traffic is trending up here and may get busier within the hour, based on historical patterns.",
  },
  "direct-bourke": {
    area: "Bourke St Mall",
    etaMinutesStart: 15,
    etaMinutesEnd: 30,
    message: "Crowd levels are forecast to peak here within the hour, based on historical patterns.",
  },
};

const mockQuietSpaces = [
  { id: 1, label: "State Library Victoria", lat: -37.8099, lng: 144.9656 },
  { id: 2, label: "Flagstaff Gardens", lat: -37.8095, lng: 144.9531 },
  { id: 3, label: "Treasury Gardens", lat: -37.8115, lng: 144.9793 },
];

const mockAlert = {
  title: "Busy area ahead near Bourke St",
  message: "A quieter path is available.",
};

const mockPedestrianCounts = {
  observedAt: new Date().toISOString(),
  sensorCount: 4,
  totalCount: 42,
  averageCount: 10.5,
  maximumCount: 20,
  sensors: [
    { sensorId: 1, name: "Flinders Street Station", minuteCount: 20, lat: -37.8183, lng: 144.9671 },
    { sensorId: 2, name: "Melbourne Central", minuteCount: 12, lat: -37.811, lng: 144.9643 },
    { sensorId: 3, name: "Collins Street", minuteCount: 7, lat: -37.8155, lng: 144.9631 },
    { sensorId: 4, name: "Bourke St Mall", minuteCount: 3, lat: -37.8136, lng: 144.9648 },
  ],
};

export async function getRouteDetail(routeId) {
  return withApiFallback(
    async () => {
      const real = await apiGet(`/routes/${routeId}`);
      // Real routes carry an encoded `polyline` instead of a plain path —
      // decode it into the {lat, lng}[] shape the map already draws.
      // Falls back to a straight line between the two endpoints if for some
      // reason there's no polyline.
      const path = real.polyline
        ? decodePolyline(real.polyline)
        : [real.origin, real.destination].filter(Boolean);
      return { ...real, path };
    },
    async () => {
      await delay(300);
      return mockRouteDetails[routeId] ?? mockRouteDetails["quiet-flinders"];
    }
  );
}

export async function getQuietSpaces(routeId) {
  return withApiFallback(
    () => apiGet(`/routes/${routeId}/quiet-spaces`),
    async () => {
      await delay(450);
      return mockQuietSpaces;
    }
  );
}

export async function getSensoryAlert(routeId) {
  return withApiFallback(
    async () => {
      const result = await apiGet(`/routes/${routeId}/alerts`);
      // Backend currently returns a list (possibly empty) instead of a
      // single alert-or-null — normalise here rather than waiting on that
      // to change.
      return Array.isArray(result) ? (result[0] ?? null) : result;
    },
    async () => {
      await delay(600);
      return routeId === "quiet-flinders" ? null : mockAlert;
    }
  );
}

export async function getPedestrianCounts() {
  return withApiFallback(
    () => apiGet("/pedestrian-counts/latest"),
    async () => {
      await delay(400);
      return mockPedestrianCounts;
    }
  );
}

export async function getForecast(routeId) {
  return withApiFallback(
    // Backend 404s instead of returning null when there's no forecast for
    // this route — that's a valid "nothing to report" state, not a failure.
    () => apiGet(`/routes/${routeId}/forecast`, { notFoundIsNull: true }),
    async () => {
      await delay(550);
      return mockForecasts[routeId] ?? null;
    }
  );
}
