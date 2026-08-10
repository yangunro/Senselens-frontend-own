import { apiGet, delay, withApiFallback } from "./http";

const mockCbdStatus = {
  level: "moderate",
  label: "CBD is MODERATELY BUSY now",
  note: "Calmer after 10am",
};

export async function getCbdStatus() {
  return withApiFallback(
    () => apiGet("/cbd-status"),
    async () => {
      await delay(350);
      return mockCbdStatus;
    }
  );
}
