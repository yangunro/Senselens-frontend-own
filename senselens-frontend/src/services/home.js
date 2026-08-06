import { delay } from "./http";

const mockCbdStatus = {
  level: "moderate",
  label: "CBD is MODERATELY BUSY now",
  note: "Calmer after 10am",
};

const mockSavedRoutes = [
  { label: "Home to Work", destination: "Collins Street" },
  { label: "Work to Station", destination: "Southern Cross Station" },
];

export async function getCbdStatus() {
  // TODO: replace with apiGet("/cbd-status") once the backend endpoint exists
  await delay(350);
  return mockCbdStatus;
}

export async function getSavedRoutes() {
  // TODO: replace with apiGet("/saved-routes")
  await delay(400);
  return mockSavedRoutes;
}
