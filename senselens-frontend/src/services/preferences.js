import { delay } from "./http";

const defaultPreferences = {
  sliders: [
    { key: "noise", label: "Noise sensitivity", value: 1 },
    { key: "crowd", label: "Crowd sensitivity", value: 0 },
    { key: "light", label: "Bright light sensitivity", value: 2 },
  ],
  toggles: [
    {
      key: "construction",
      label: "Avoid construction zones",
      note: "Steer routes away from sudden loud sounds or dust.",
      value: true,
    },
    {
      key: "refuges",
      label: "Always show refuge spaces",
      note: "Keep parks, quiet libraries and cafes highlighted on-screen.",
      value: true,
    },
    {
      key: "contrast",
      label: "High contrast / reduced motion mode",
      note: "Use stronger colors and fewer animations for comfort.",
      value: true,
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
