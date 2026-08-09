import { delay } from "./http";

const defaultPreferences = {
  sliders: [{ key: "crowd", label: "Crowd sensitivity", value: 0 }],
  toggles: [
    {
      key: "refuges",
      label: "Always show refuge spaces",
      note: "Keep parks, quiet libraries and cafes highlighted on-screen.",
      value: true,
    },
    {
      key: "contrast",
      label: "High contrast mode",
      note: "Increase contrast to make text and interface elements easier to distinguish.",
      value: false,
    },
  ],
};

export async function getPreferences() {
  // TODO: replace with apiGet("/preferences")
  await delay(350);
  return defaultPreferences;
}

export async function savePreferences(preferences) {
  // TODO: replace with apiPost("/preferences", preferences)
  await delay(500);
  return { ok: true };
}
