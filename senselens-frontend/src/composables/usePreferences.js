import { reactive } from "vue";
import { getPreferences } from "../services/preferences";

// Single shared instance so every page reads/writes the same preferences —
// toggles like "contrast" need to be visible app-wide (App.vue), not just on the Setting page.
const state = reactive({ ready: false, sliders: [], toggles: [] });
let loadPromise = null;

export function usePreferences() {
  if (!loadPromise) {
    loadPromise = getPreferences().then((preferences) => {
      state.sliders = preferences.sliders;
      state.toggles = preferences.toggles;
      state.ready = true;
    });
  }
  return state;
}

export function toggleValue(preferencesState, key, fallback = false) {
  return preferencesState.toggles.find((toggle) => toggle.key === key)?.value ?? fallback;
}
