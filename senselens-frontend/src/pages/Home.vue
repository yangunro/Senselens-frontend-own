<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import { getCbdStatus } from "../services/home";
import { useMapboxSearch } from "../composables/useMapboxSearch";

const router = useRouter();

// Left blank, the route still starts from the user's live location (or the
// Flinders St fallback if that's denied/unavailable) — same as before. Only
// overrides it when the user actually types/picks a starting point.
const origin = useMapboxSearch();
const destination = useMapboxSearch();

const cbdStatus = ref(null);
const loading = ref(true);

onMounted(async () => {
  cbdStatus.value = await getCbdStatus();
  loading.value = false;
});

async function findCalmRoute() {
  await Promise.all([origin.waitForPending(), destination.waitForPending()]);
  router.push({
    path: "/routes",
    query: {
      destination: destination.query.value || "Collins Street",
      ...(destination.point.value
        ? { destLat: destination.point.value.lat, destLng: destination.point.value.lng }
        : {}),
      ...(origin.query.value.trim() ? { origin: origin.query.value } : {}),
      ...(origin.point.value ? { originLat: origin.point.value.lat, originLng: origin.point.value.lng } : {}),
    },
  });
}
</script>

<template>
  <PageShell>
    <header class="top-bar">
      <div class="brand">
        <div class="brand-icon">
          <Icon name="leaf" :size="16" />
        </div>
        <span>SenseLens</span>
      </div>

      <button class="profile-button" aria-label="Open profile">
        <Icon name="user" :size="18" />
      </button>
    </header>

    <section class="hero-section">
      <div class="hero-text">
        <h1>Where would you like to go?</h1>

        <p>
          We’ll find the calmest routes for your sensory comfort.
        </p>
      </div>

      <div v-if="loading" class="desktop-preview">
        <span class="preview-label">Sensory forecast</span>
        <SkeletonBlock width="70%" height="16px" />
        <SkeletonBlock width="90%" height="12px" />
      </div>
      <div v-else-if="cbdStatus" class="desktop-preview">
        <span class="preview-label">Sensory forecast</span>
        <strong>{{ cbdStatus.label }}</strong>
        <p>Conditions are expected to become calmer after 10am.</p>
      </div>
    </section>

    <div class="content-grid">
      <div class="main-column">
        <section class="status-card">
          <div class="status-dot"></div>

          <div v-if="loading" class="status-skeleton">
            <SkeletonBlock width="180px" height="12px" />
            <SkeletonBlock width="110px" height="10px" />
          </div>
          <div v-else-if="cbdStatus">
            <strong>{{ cbdStatus.label }}</strong>
            <p>{{ cbdStatus.note }}</p>
          </div>
        </section>

        <section class="search-section">
          <div class="search-wrap">
            <div class="search-box">
              <Icon class="search-icon" name="tent" :size="19" />

              <input
                v-model="origin.query.value"
                type="text"
                placeholder="Starting point (optional, defaults to your location)"
                autocomplete="off"
                @input="origin.onInput"
                @keyup.enter="findCalmRoute"
                @focus="origin.showSuggestions.value = true"
                @blur="origin.showSuggestions.value = false"
              />
            </div>

            <ul v-if="origin.showSuggestions.value && origin.suggestions.value.length" class="suggestion-list">
              <li v-for="s in origin.suggestions.value" :key="s.mapbox_id" @mousedown.prevent="origin.select(s)">
                <strong>{{ s.name }}</strong>
                <span v-if="s.place_formatted">{{ s.place_formatted }}</span>
              </li>
            </ul>
          </div>

          <div class="search-wrap search-wrap-destination">
            <div class="search-box">
              <Icon class="search-icon" name="search" :size="19" />

              <input
                v-model="destination.query.value"
                type="text"
                placeholder="Enter your destination"
                autocomplete="off"
                @input="destination.onInput"
                @keyup.enter="findCalmRoute"
                @focus="destination.showSuggestions.value = true"
                @blur="destination.showSuggestions.value = false"
              />
            </div>

            <ul v-if="destination.showSuggestions.value && destination.suggestions.value.length" class="suggestion-list">
              <li v-for="s in destination.suggestions.value" :key="s.mapbox_id" @mousedown.prevent="destination.select(s)">
                <strong>{{ s.name }}</strong>
                <span v-if="s.place_formatted">{{ s.place_formatted }}</span>
              </li>
            </ul>
          </div>

          <button class="search-button" @click="findCalmRoute">
            Find a calm route
          </button>
        </section>
      </div>

      <aside class="side-column">
        <section class="info-card">
          <span class="info-label">Plan ahead</span>
          <h3>Travel when conditions feel calmer</h3>
          <p>
            SenseLens compares crowd conditions and helps you choose
            a more comfortable time and route.
          </p>
        </section>

        <p class="tagline">
          Plan once. Travel calm.
        </p>
      </aside>
    </div>
  </PageShell>
</template>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 9px;

  color: var(--color-primary-dark);
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.2px;
}

.brand-icon {
  display: grid;
  place-items: center;

  width: 30px;
  height: 30px;

  background: var(--color-primary-soft);
  border-radius: 50%;

  color: var(--color-primary);
}

.profile-button {
  display: grid;
  place-items: center;

  width: 38px;
  height: 38px;

  padding: 0;

  background: var(--color-surface-muted);
  border: none;
  border-radius: var(--radius-sm);

  color: var(--color-primary-dark);
}

.hero-section {
  margin-top: 32px;
}

.hero-text h1 {
  margin: 0;

  color: var(--color-text);
  font-size: 28px;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.6px;
}

.hero-text p {
  margin: 10px 0 0;

  color: var(--color-text-muted);
  font-size: 14.5px;
  line-height: 1.55;
}

.desktop-preview {
  display: none;
}

.content-grid {
  margin-top: 26px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 13px;

  padding: 17px 18px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.status-dot {
  flex: 0 0 auto;

  width: 10px;
  height: 10px;

  background: var(--color-alert);
  border-radius: 50%;
}

.status-skeleton {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.status-card strong {
  display: block;

  color: var(--color-text);
  font-size: 13px;
  font-weight: 700;
}

.status-card p {
  margin: 4px 0 0;

  color: var(--color-text-muted);
  font-size: 12.5px;
}

.search-section {
  margin-top: 20px;
}

.search-wrap {
  position: relative;
}

.search-wrap-destination {
  margin-top: 10px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 11px;

  padding: 0 16px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.search-icon {
  color: var(--color-primary);
}

.search-box input {
  width: 100%;
  height: 56px;

  background: transparent;
  border: none;
  outline: none;

  color: var(--color-text);
  font-size: 14.5px;
}

.search-box input::placeholder {
  color: var(--color-text-faint);
}

.suggestion-list {
  position: absolute;
  z-index: 5;
  top: calc(100% + 6px);
  left: 0;
  right: 0;

  overflow: hidden;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}

.suggestion-list li {
  padding: 11px 16px;

  cursor: pointer;
}

.suggestion-list li:not(:last-child) {
  border-bottom: 1px solid var(--color-border);
}

.suggestion-list li:hover {
  background: var(--color-surface-muted);
}

.suggestion-list strong {
  display: block;

  color: var(--color-text);
  font-size: 13.5px;
  font-weight: 600;
}

.suggestion-list span {
  display: block;

  margin-top: 2px;

  color: var(--color-text-muted);
  font-size: 12px;
}

.search-button {
  width: 100%;

  margin-top: 12px;
  padding: 16px 20px;

  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);

  color: white;
  font-size: 14.5px;
  font-weight: 700;
  transition: background 0.15s ease, transform 0.1s ease;
}

.search-button:hover {
  background: var(--color-primary-dark);
}

.search-button:active {
  transform: scale(0.99);
}

.side-column {
  margin-top: 28px;
}

.info-card {
  display: none;
}

.tagline {
  margin-top: 28px;

  color: var(--color-text-faint);
  font-size: 12px;
}

/* 平板 */
@media (min-width: 768px) {
  .hero-text h1 {
    font-size: 38px;
  }

  .hero-text p {
    font-size: 16px;
  }

  .status-card {
    padding: 20px;
  }

  .search-box input {
    height: 60px;
    font-size: 16px;
  }

  .search-button {
    padding: 17px 22px;
    font-size: 15px;
  }
}

/* 电脑 */
@media (min-width: 1024px) {
  .top-bar {
    min-height: 44px;
    padding-right: 410px;
  }

  .profile-button {
    display: none;
  }

  .hero-section {
    display: grid;
    grid-template-columns: minmax(0, 1.3fr) minmax(300px, 0.7fr);
    gap: 60px;
    align-items: end;

    margin-top: 75px;
  }

  .hero-text h1 {
    max-width: 650px;
    font-size: 52px;
  }

  .hero-text p {
    max-width: 570px;
    font-size: 18px;
  }

  .desktop-preview {
    display: flex;
    flex-direction: column;
    gap: 9px;

    padding: 26px;

    background: var(--color-primary-soft);
    border: 1px solid #d3e3da;
    border-radius: var(--radius-lg);
  }

  .preview-label {
    display: block;

    margin-bottom: 8px;

    color: var(--color-primary-dark);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }

  .desktop-preview strong {
    display: block;

    color: var(--color-primary-dark);
    font-size: 19px;
    line-height: 1.3;
  }

  .desktop-preview p {
    margin: 10px 0 0;

    color: var(--color-text-muted);
    font-size: 14px;
    line-height: 1.5;
  }

  .content-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.55fr);
    gap: 40px;

    margin-top: 42px;
  }

  .side-column {
    margin-top: 0;
  }

  .info-card {
    display: block;

    padding: 24px;

    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
  }

  .info-label {
    color: var(--color-primary);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }

  .info-card h3 {
    margin: 10px 0 8px;

    color: var(--color-text);
    font-size: 20px;
  }

  .info-card p {
    margin: 0;

    color: var(--color-text-muted);
    font-size: 14px;
    line-height: 1.55;
  }

  .tagline {
    margin-top: 20px;
  }
}
</style>
