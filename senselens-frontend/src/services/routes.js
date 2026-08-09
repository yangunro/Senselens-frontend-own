import { apiGet, delay, withApiFallback } from "./http";

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

export async function getRouteOptions(destination) {
  return withApiFallback(
    () => apiGet(`/routes?destination=${encodeURIComponent(destination)}`),
    async () => {
      await delay(500);
      return mockRouteOptions;
    }
  );
}
