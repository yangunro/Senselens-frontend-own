<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import { getRoutes as getRouteOptions } from "../services/map";
import { getAccurateCurrentLocation } from "../services/geolocation";

const route = useRoute();
const router = useRouter();

const destination = computed(() => route.query.destination || "Collins Street");
const destinationLocation = computed(
  () => {
    const lat = Number(
      route.query.destinationLat,
    );
    const lng = Number(
      route.query.destinationLng,
    );

    return Number.isFinite(lat) &&
      Number.isFinite(lng)
      ? { lat, lng }
      : null;
  },
);

const routeOptions = ref([]);
const selectedId = ref(null);
const loading = ref(true);
const errorMessage = ref("");
const locationAccuracy = ref(null);

let loadSequence = 0;

async function loadRoutes() {
  const sequence = ++loadSequence;

  loading.value = true;
  errorMessage.value = "";
  locationAccuracy.value = null;
  routeOptions.value = [];
  selectedId.value = null;

  try {
    const origin =
      await getAccurateCurrentLocation();

    if (sequence !== loadSequence) {
      return;
    }

    locationAccuracy.value =
      Math.round(origin.accuracy);
    routeOptions.value =
      await getRouteOptions(
        destination.value,
        origin,
        destinationLocation.value,
      );

    if (sequence !== loadSequence) {
      return;
    }

    const recommended =
      routeOptions.value.find(
        (item) => item.recommended,
      );

    selectedId.value =
      recommended?.id ??
      routeOptions.value[0]?.id ??
      null;
  } catch (error) {
    if (sequence === loadSequence) {
      errorMessage.value =
        error.message ||
        "Unable to calculate routes from your current location.";
    }
  } finally {
    if (sequence === loadSequence) {
      loading.value = false;
    }
  }
}

onMounted(loadRoutes);
watch(destination, loadRoutes);

function startCalmRoute() {
  router.push({ path: "/map", query: { route: selectedId.value } });
}
</script>

<template>
  <PageShell>
    <header class="page-header">
      <button class="back-button" aria-label="Go back" @click="router.back()">
        <Icon name="chevronLeft" :size="18" />
      </button>

      <div>
        <h1>Current location to {{ destination }}</h1>
        <p v-if="locationAccuracy">
          Location accuracy: ±{{ locationAccuracy }} m
        </p>
        <p v-else>Finding your precise starting location</p>
      </div>
    </header>

    <div v-if="loading" class="route-list">
      <div v-for="n in 3" :key="n" class="route-card skeleton-card">
        <div class="route-card-top">
          <SkeletonBlock width="90px" height="10px" />
          <SkeletonBlock width="70px" height="20px" radius="999px" />
        </div>
        <SkeletonBlock width="70%" height="15px" />
        <SkeletonBlock width="95%" height="12px" />
        <SkeletonBlock width="60px" height="12px" />
      </div>
    </div>

    <div v-else-if="errorMessage" class="route-error">
      <strong>We need your location to calculate an accurate route.</strong>
      <p>{{ errorMessage }}</p>
      <button type="button" @click="loadRoutes">
        Try location again
      </button>
    </div>

    <div v-else class="route-list">
      <button
        v-for="option in routeOptions"
        :key="option.id"
        class="route-card"
        :class="[`level-${option.level}`, { selected: selectedId === option.id }]"
        @click="selectedId = option.id"
      >
        <div class="route-card-top">
          <span class="route-tag">{{ option.tag }}</span>
          <span class="sensory-badge" :class="`level-${option.level}`">
            {{ option.levelLabel }}
          </span>
        </div>

        <h2>{{ option.name }}</h2>
        <p>{{ option.description }}</p>

        <div class="route-card-bottom">
          <span class="duration">
            <Icon name="clock" :size="14" />
            {{ option.duration }}
          </span>
          <span v-if="option.footnote" class="footnote">{{ option.footnote }}</span>
        </div>
      </button>
    </div>

    <button class="start-button" :disabled="!selectedId" @click="startCalmRoute">
      Start calm route
    </button>
  </PageShell>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.back-button {
  display: grid;
  flex: 0 0 auto;
  place-items: center;

  width: 38px;
  height: 38px;

  background: var(--color-surface-muted);
  border: none;
  border-radius: var(--radius-sm);

  color: var(--color-primary-dark);
}

.page-header h1 {
  margin: 4px 0 0;

  color: var(--color-text);
  font-size: 18px;
  font-weight: 800;
  line-height: 1.3;
  letter-spacing: -0.2px;
}

.page-header p {
  margin: 5px 0 0;

  color: var(--color-text-muted);
  font-size: 13px;
}

.route-list {
  display: flex;
  flex-direction: column;
  gap: 14px;

  margin-top: 24px;
}

.route-error {
  margin-top: 24px;
  padding: 18px;

  background: var(--color-alert-bg);
  border: 1px solid var(--color-alert-border);
  border-radius: var(--radius-md);
}

.route-error strong {
  color: #6b4d16;
  font-size: 13px;
}

.route-error p {
  margin: 7px 0 14px;

  color: #8a6a2a;
  font-size: 12.5px;
  line-height: 1.5;
}

.route-error button {
  padding: 9px 14px;

  background: var(--color-surface);
  border: 1px solid var(--color-alert-border);
  border-radius: var(--radius-pill);

  color: #6b4d16;
  font-weight: 700;
}

.route-card {
  display: block;

  padding: 18px;

  background: var(--color-surface);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);

  text-align: left;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.1s ease;
}

.route-card:hover {
  border-color: #cfe3da;
}

.skeleton-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-card .route-card-top {
  margin-bottom: 4px;
}

.route-card.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.route-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;

  gap: 10px;
}

.route-tag {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}

.sensory-badge {
  flex: 0 0 auto;

  padding: 4px 11px;

  border-radius: var(--radius-pill);

  font-size: 11px;
  font-weight: 700;
}

.sensory-badge.level-low {
  background: var(--color-low-bg);
  color: var(--color-low);
}

.sensory-badge.level-medium {
  background: var(--color-medium-bg);
  color: var(--color-medium);
}

.sensory-badge.level-high {
  background: var(--color-high-bg);
  color: var(--color-high);
}

.route-card h2 {
  margin: 12px 0 5px;

  color: var(--color-text);
  font-size: 15.5px;
  font-weight: 700;
}

.route-card p {
  margin: 0;

  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.55;
}

.route-card-bottom {
  display: flex;
  align-items: center;
  gap: 14px;

  margin-top: 13px;
}

.duration {
  display: inline-flex;
  align-items: center;
  gap: 5px;

  color: var(--color-text-muted);
  font-size: 12.5px;
  font-weight: 600;
}

.footnote {
  color: var(--color-primary);
  font-size: 12.5px;
  font-weight: 700;
}

.start-button {
  width: 100%;

  margin-top: 24px;
  padding: 16px 20px;

  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);

  color: white;
  font-size: 14.5px;
  font-weight: 700;
  transition: background 0.15s ease;
}

.start-button:hover {
  background: var(--color-primary-dark);
}

.start-button:disabled {
  background: var(--color-text-faint);
  cursor: not-allowed;
}

@media (min-width: 768px) {
  .route-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }

  .start-button {
    max-width: 320px;
  }
}
</style>
