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

// Predictive alerts (US 2.2): the route's overall crowd level forecast one
// hour from now, derived from historical pedestrian trend data on the backend.
const mockForecasts = {
  "quiet-flinders": null,
  "balanced-collins": {
    levelLabel: "MEDIUM SENSORY",
    level: "medium",
    basis: "Pedestrian traffic near Collins St intersection is trending up and may get busier within the hour, based on historical patterns.",
  },
  "direct-bourke": {
    levelLabel: "HIGH SENSORY",
    level: "high",
    basis: "Crowd levels near Bourke St Mall are forecast to peak within the hour, based on historical patterns.",
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
    async () => {
      const real = await apiGet(`/routes/${routeId}/quiet-spaces`);
      // Real shape (refugeId/name/lat/lng/category/distanceFromRouteM)
      // doesn't line up with what the map marker rendering expects
      // (id/label/lat/lng) — normalise rather than leaving marker titles blank.
      return real.map((space) => ({
        id: space.refugeId,
        label: space.name,
        lat: space.lat,
        lng: space.lng,
        category: space.category,
        distanceFromRouteM: space.distanceFromRouteM,
      }));
    },
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

const mockPedestrianForecast = {
  horizonHours: 3,
  forecasts: [
    {
      hoursAhead: 1,
      sensors: [
        { sensorId: 1, name: "Flinders Street Station", lat: -37.8183, lng: 144.9671, level: "medium", predictedCountPerMinute: 15 },
        { sensorId: 2, name: "Melbourne Central", lat: -37.811, lng: 144.9643, level: "high", predictedCountPerMinute: 28 },
      ],
    },
    {
      hoursAhead: 2,
      sensors: [
        { sensorId: 1, name: "Flinders Street Station", lat: -37.8183, lng: 144.9671, level: "low", predictedCountPerMinute: 8 },
        { sensorId: 2, name: "Melbourne Central", lat: -37.811, lng: 144.9643, level: "medium", predictedCountPerMinute: 18 },
      ],
    },
    {
      hoursAhead: 3,
      sensors: [
        { sensorId: 1, name: "Flinders Street Station", lat: -37.8183, lng: 144.9671, level: "low", predictedCountPerMinute: 6 },
        { sensorId: 2, name: "Melbourne Central", lat: -37.811, lng: 144.9643, level: "low", predictedCountPerMinute: 10 },
      ],
    },
  ],
  alerts: [
    {
      level: "high",
      message: "Melbourne Central may reach 28 pedestrians per minute in about 1 hour(s).",
      hoursAhead: 1,
    },
  ],
};

// Map-wide (not route-specific) crowd predictions for every reporting
// sensor, 1-3 hours ahead — powers the map's forecast time-toggle and its
// "high crowd predicted" alerts. Always requested at the full 3-hour horizon
// so the toggle can switch hours locally without re-fetching.
export async function getPedestrianForecast() {
  return withApiFallback(
    () => apiGet("/pedestrian-forecasts?horizonHours=3"),
    async () => {
      await delay(500);
      return mockPedestrianForecast;
    }
  );
}

export async function getForecast(routeId) {
  return withApiFallback(
    async () => {
      // Backend 404s instead of returning null when there's no forecast for
      // this route — that's a valid "nothing to report" state, not a failure.
      const real = await apiGet(`/routes/${routeId}/forecast`, { notFoundIsNull: true });
      if (!real) return null;
      // Real shape is a single next-hour crowd-level prediction for the whole
      // route (level/basis) — not the area+ETA-range the UI was originally
      // written for.
      return { levelLabel: real.sensoryIndicator, level: real.level, basis: real.basis };
    },
    async () => {
      await delay(550);
      return mockForecasts[routeId] ?? null;
    }
  );
}
