import { delay } from "./http";

const mockRouteDetails = {
  "quiet-flinders": { name: "Quiet Route", level: "low", levelLabel: "LOW SENSORY", duration: "18 min", distance: "1.2 km", progress: 35 },
  "balanced-collins": { name: "Balanced Route", level: "medium", levelLabel: "MEDIUM SENSORY", duration: "14 min", distance: "1.0 km", progress: 35 },
  "direct-bourke": { name: "Direct Route", level: "high", levelLabel: "HIGH SENSORY", duration: "12 min", distance: "0.9 km", progress: 35 },
};

const mockQuietSpaces = [
  { id: 1, label: "Quiet space", top: "22%", left: "62%" },
  { id: 2, label: "Quiet space", top: "48%", left: "82%" },
  { id: 3, label: "Quiet space", top: "68%", left: "18%" },
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
  return mockAlert;
}
