<script setup>
import { ref, computed } from "vue";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import { savePreferences as savePreferencesRequest } from "../services/preferences";
import { usePreferences } from "../composables/usePreferences";

const preferences = usePreferences();
const sliders = computed(() => preferences.sliders);
const toggles = computed(() => preferences.toggles);
const levelLabels = ["Low", "Medium", "High"];
const loading = computed(() => !preferences.ready);

const saved = ref(false);
const saving = ref(false);
let savedTimeout;

async function savePreferences() {
  saving.value = true;
  await savePreferencesRequest({ sliders: preferences.sliders, toggles: preferences.toggles });
  saving.value = false;

  saved.value = true;
  clearTimeout(savedTimeout);
  savedTimeout = setTimeout(() => (saved.value = false), 1800);
}
</script>

<template>
  <PageShell>
    <header class="page-header">
      <h1>Your sensory preferences</h1>
      <p>
        We use these to choose calmer routes. We never ask about medical
        conditions.
      </p>
    </header>

    <section v-if="loading" class="sliders">
      <div v-for="n in 3" :key="n" class="slider-row skeleton-slider">
        <div class="slider-label">
          <SkeletonBlock width="120px" height="12px" />
          <SkeletonBlock width="45px" height="12px" />
        </div>
        <SkeletonBlock width="100%" height="6px" radius="999px" />
      </div>
    </section>

    <section v-else class="sliders">
      <div v-for="slider in sliders" :key="slider.key" class="slider-row">
        <div class="slider-label">
          <span>{{ slider.label }}</span>
          <strong>{{ levelLabels[slider.value] }}</strong>
        </div>

        <input v-model.number="slider.value" type="range" min="0" max="2" step="1" />

        <div class="slider-scale">
          <span>Low</span>
          <span>High</span>
        </div>
      </div>
    </section>

    <section v-if="loading" class="toggles">
      <div v-for="n in 3" :key="n" class="toggle-row skeleton-toggle">
        <div class="skeleton-lines">
          <SkeletonBlock width="65%" height="12px" />
          <SkeletonBlock width="90%" height="10px" />
        </div>
        <SkeletonBlock width="44px" height="26px" radius="999px" />
      </div>
    </section>

    <section v-else class="toggles">
      <label v-for="toggle in toggles" :key="toggle.key" class="toggle-row">
        <div>
          <span class="toggle-label">{{ toggle.label }}</span>
          <p>{{ toggle.note }}</p>
        </div>

        <span class="switch" :class="{ on: toggle.value }">
          <input v-model="toggle.value" type="checkbox" />
          <span class="switch-thumb"></span>
        </span>
      </label>
    </section>

    <button class="save-button" :disabled="saving || loading" @click="savePreferences">
      <Icon v-if="saved && !saving" name="check" :size="16" />
      {{ saving ? "Saving…" : saved ? "Preferences saved" : "Save preferences" }}
    </button>

    <p class="footnote">These settings adjust your route recommendations</p>
  </PageShell>
</template>

<style scoped>
.page-header h1 {
  margin: 0;

  color: var(--color-text);
  font-size: 21px;
  font-weight: 800;
  letter-spacing: -0.3px;
}

.page-header p {
  margin: 7px 0 0;

  max-width: 420px;

  color: var(--color-text-muted);
  font-size: 13.5px;
  line-height: 1.55;
}

.sliders {
  display: flex;
  flex-direction: column;
  gap: 14px;

  margin-top: 26px;
}

.slider-row {
  padding: 17px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.slider-label {
  display: flex;
  align-items: center;
  justify-content: space-between;

  color: var(--color-text);
  font-size: 13px;
  font-weight: 700;
}

.slider-label strong {
  color: var(--color-primary);
}

.slider-row input[type="range"] {
  width: 100%;

  margin-top: 13px;

  accent-color: var(--color-primary);
}

.slider-scale {
  display: flex;
  justify-content: space-between;

  margin-top: 5px;

  color: var(--color-text-faint);
  font-size: 11px;
}

.skeleton-slider {
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.skeleton-toggle .skeleton-lines {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 8px;
}

.toggles {
  display: flex;
  flex-direction: column;
  gap: 12px;

  margin-top: 22px;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;

  gap: 16px;
  padding: 17px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);

  cursor: pointer;
}

.toggle-label {
  display: block;

  color: var(--color-text);
  font-size: 13px;
  font-weight: 700;
}

.toggle-row p {
  margin: 5px 0 0;

  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.45;
}

.switch {
  position: relative;
  flex: 0 0 auto;

  display: inline-block;

  width: 44px;
  height: 26px;
}

.switch input {
  position: absolute;
  opacity: 0;
}

.switch-thumb {
  position: absolute;
  inset: 0;

  background: var(--color-border);
  border-radius: var(--radius-pill);

  transition: background 0.15s ease;
}

.switch-thumb::after {
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;

  width: 20px;
  height: 20px;

  background: var(--color-surface);
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);

  transition: transform 0.15s ease;
}

.switch.on .switch-thumb {
  background: var(--color-primary);
}

.switch.on .switch-thumb::after {
  transform: translateX(18px);
}

.save-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  width: 100%;

  margin-top: 26px;
  padding: 16px 20px;

  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);

  color: white;
  font-size: 14.5px;
  font-weight: 700;
  transition: background 0.15s ease;
}

.save-button:hover {
  background: var(--color-primary-dark);
}

.save-button:disabled {
  background: var(--color-text-faint);
  cursor: progress;
}

.footnote {
  margin-top: 13px;

  color: var(--color-text-faint);
  font-size: 11px;
  text-align: center;
}

@media (min-width: 768px) {
  .sliders,
  .toggles {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }

  .save-button {
    max-width: 320px;
  }
}
</style>
