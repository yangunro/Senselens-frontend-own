import { delay } from "./http";

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

export async function getRouteDetail(routeId) {
  // TODO: replace with apiGet(`/routes/${routeId}`)
  await delay(300);
  return mockRouteDetails[routeId] ?? mockRouteDetails["quiet-flinders"];
}

export async function getQuietSpaces(routeId) {
  // TODO: replace with apiGet(`/routes/${routeId}/quiet-spaces`)
  await delay(450);
  return mockQuietSpaces;
}

export async function getSensoryAlert(routeId) {
  // TODO: replace with apiGet(`/routes/${routeId}/alerts`) — return null when there's nothing to warn about
  await delay(600);
  return routeId === "quiet-flinders" ? null : mockAlert;
}

export async function getForecast(routeId) {
  // TODO: replace with apiGet(`/routes/${routeId}/forecast`) — return null when nothing is forecast
  await delay(550);
  return mockForecasts[routeId] ?? null;
}
