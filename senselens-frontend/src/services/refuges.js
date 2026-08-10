import { apiGet, delay, withApiFallback } from "./http";

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

const ICON_BY_CATEGORY = {
  Library: "book",
  Park: "tree",
  Cafe: "coffee",
};

export async function getRefuges() {
  return withApiFallback(
    async () => {
      const real = await apiGet("/refuges");
      // Real shape (refugeId/category/lat/lng/sourceDataset/quietScore)
      // doesn't line up with the mock's (id/type/icon/distance/note) —
      // normalise rather than rewriting the page around two shapes.
      return real.map((refuge) => ({
        id: refuge.refugeId,
        name: refuge.name,
        type: refuge.category,
        icon: ICON_BY_CATEGORY[refuge.category] ?? "refuge",
        lat: refuge.lat,
        lng: refuge.lng,
      }));
    },
    async () => {
      await delay(450);
      return mockRefuges;
    }
  );
}
