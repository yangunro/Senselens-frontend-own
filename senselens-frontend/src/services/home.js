import { apiGet, delay } from "./http";

const mockSavedRoutes = [
  { label: "Home to Work", destination: "Collins Street" },
  { label: "Work to Station", destination: "Southern Cross Station" },
];

export async function getCbdStatus() {
  return apiGet("/cbd-status");
}

export async function getSavedRoutes() {
  // TODO: replace with apiGet("/saved-routes")
  await delay(400);
  return mockSavedRoutes;
}
