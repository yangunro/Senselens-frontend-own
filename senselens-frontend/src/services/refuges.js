import { delay } from "./http";

const mockRefuges = [
  {
    id: 1,
    name: "State Library Victoria",
    type: "Library",
    icon: "book",
    distance: "0.4 km",
    note: "Quiet reading rooms, low lighting, sensory-friendly hours.",
  },
  {
    id: 2,
    name: "Flagstaff Gardens",
    type: "Park",
    icon: "tree",
    distance: "0.6 km",
    note: "Open lawn away from tram noise, shaded seating.",
  },
  {
    id: 3,
    name: "City Library, Melbourne Town Hall",
    type: "Library",
    icon: "book",
    distance: "0.9 km",
    note: "Quiet study pods available, sunflower-friendly staff.",
  },
  {
    id: 4,
    name: "Treasury Gardens",
    type: "Park",
    icon: "tree",
    distance: "1.1 km",
    note: "Low pedestrian traffic, minimal construction noise.",
  },
];

export async function getRefuges() {
  // TODO: replace with apiGet("/refuges")
  await delay(450);
  return mockRefuges;
}
