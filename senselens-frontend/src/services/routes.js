import { delay } from "./http";

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
  },
  {
    id: "balanced-collins",
    tag: "Alt route",
    level: "medium",
    levelLabel: "MEDIUM SENSORY",
    name: "Balanced Route via Collins St",
    description: "Slightly busy intersection near retail zone. Medium pace.",
    duration: "14 min",
  },
  {
    id: "direct-bourke",
    tag: "Fastest route",
    level: "high",
    levelLabel: "HIGH SENSORY",
    name: "Direct Route via Bourke St Mall",
    description: "High tram noise, street performances, very dense crowds.",
    duration: "12 min",
  },
];

export async function getRouteOptions(destination) {
  // TODO: replace with apiGet(`/routes?destination=${encodeURIComponent(destination)}`)
  await delay(500);
  return mockRouteOptions;
}
