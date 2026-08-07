import { delay } from "./http";

const mockCbdStatus = {
  level: "moderate",
  label: "CBD is MODERATELY BUSY now",
  note: "Calmer after 10am",
};

export async function getCbdStatus() {
  // TODO: replace with apiGet("/cbd-status") once the backend endpoint exists
  await delay(350);
  return mockCbdStatus;
}
