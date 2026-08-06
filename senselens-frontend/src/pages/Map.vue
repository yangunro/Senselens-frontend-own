<script setup>
import { ref, watch, onMounted } from "vue";
import { useRoute } from "vue-router";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import ProgressBar from "../components/ProgressBar.vue";
import { getRouteDetail, getQuietSpaces, getSensoryAlert } from "../services/map";

const route = useRoute();

const activeRoute = ref(null);
const quietSpaces = ref([]);
const alert = ref(null);
const alertDismissed = ref(false);
const loading = ref(true);

async function loadMap() {
  const routeId = route.query.route;
  loading.value = true;
  alertDismissed.value = false;
  [activeRoute.value, quietSpaces.value, alert.value] = await Promise.all([
    getRouteDetail(routeId),
    getQuietSpaces(routeId),
    getSensoryAlert(routeId),
  ]);
  loading.value = false;
}

onMounted(loadMap);
watch(() => route.query.route, loadMap);

function reroute() {
  alertDismissed.value = true;
}
</script>

<template>
  <PageShell>
    <transition name="fade">
      <div v-if="alert && !alertDismissed" class="alert-banner">
        <div class="alert-text">
          <Icon class="alert-icon" name="alert" :size="18" />

          <div>
            <strong>{{ alert.title }}</strong>
            <p>{{ alert.message }}</p>
          </div>
        </div>

        <button class="reroute-button" @click="reroute">
          <Icon name="refresh" :size="13" />
          Reroute
        </button>
      </div>
    </transition>

    <div class="map-area">
      <div class="map-grid"></div>

      <div v-if="loading" class="map-loading">
        <span class="map-loading-dot"></span>
        Finding your calm route…
      </div>

      <template v-else>
        <svg class="map-path" viewBox="0 0 300 340" preserveAspectRatio="none">
          <path d="M 40 40 L 40 200 L 220 200" fill="none" stroke="var(--color-primary)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>

        <div class="map-marker start" style="top: 8%; left: 10%;">
          <span class="dot"></span>
        </div>

        <div
          v-for="space in quietSpaces"
          :key="space.id"
          class="map-marker refuge"
          :style="{ top: space.top, left: space.left }"
        >
          <span class="pin"><Icon name="tent" :size="14" /></span>
          <span class="pin-label">{{ space.label }}</span>
        </div>
      </template>
    </div>

    <section v-if="loading" class="route-summary skeleton-summary">
      <div class="summary-top">
        <SkeletonBlock width="130px" height="17px" />
        <SkeletonBlock width="80px" height="20px" radius="999px" />
      </div>
      <SkeletonBlock width="100%" height="6px" radius="999px" />
      <div class="skeleton-stat-grid">
        <SkeletonBlock v-for="n in 4" :key="n" width="100%" height="34px" />
      </div>
    </section>

    <section v-else-if="activeRoute" class="route-summary">
      <div class="summary-top">
        <h2>{{ activeRoute.name }}</h2>

        <span class="sensory-badge" :class="`level-${activeRoute.level}`">
          {{ activeRoute.levelLabel }}
        </span>
      </div>

      <div class="progress-row">
        <ProgressBar :value="activeRoute.progress" />
        <span class="progress-label">
          <Icon name="check" :size="13" />
          {{ activeRoute.progress }}% of the way there
        </span>
      </div>

      <div class="stat-grid">
        <div class="stat">
          <span class="stat-label">Duration</span>
          <strong class="stat-value">{{ activeRoute.duration }}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Distance</span>
          <strong class="stat-value">{{ activeRoute.distance }}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Quiet spaces</span>
          <strong class="stat-value">{{ quietSpaces.length }}</strong>
        </div>
        <div class="stat">
          <span class="stat-label">Wayfinding</span>
          <strong class="stat-value stat-value-tag">
            <Icon name="sun" :size="13" />
            Sunflower
          </strong>
        </div>
      </div>
    </section>
  </PageShell>
</template>

<style scoped>
.alert-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;

  gap: 12px;
  padding: 15px 16px;

  background: var(--color-alert-bg);
  border: 1px solid var(--color-alert-border);
  border-radius: var(--radius-md);
}

.alert-text {
  display: flex;
  align-items: flex-start;
  gap: 11px;
}

.alert-icon {
  flex: 0 0 auto;
  margin-top: 1px;

  color: var(--color-alert);
}

.alert-text strong {
  display: block;

  color: #6b4d16;
  font-size: 13px;
  font-weight: 700;
}

.alert-text p {
  margin: 3px 0 0;

  color: #8a6a2a;
  font-size: 12px;
}

.reroute-button {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;

  padding: 9px 15px;

  background: var(--color-surface);
  border: 1px solid var(--color-alert-border);
  border-radius: var(--radius-pill);

  color: #8a6a2a;
  font-size: 12px;
  font-weight: 700;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.map-area {
  position: relative;
  overflow: hidden;

  height: 340px;

  margin-top: 16px;

  background: var(--color-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.map-grid {
  position: absolute;
  inset: 0;

  background-image: radial-gradient(circle, #d8d2bf 1px, transparent 1px);
  background-size: 22px 22px;
  opacity: 0.7;
}

.map-path {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.85;
}

.map-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);

  display: flex;
  align-items: center;
  gap: 9px;

  padding: 11px 18px;

  background: var(--color-surface);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-sm);

  color: var(--color-text-muted);
  font-size: 12.5px;
  font-weight: 600;
  white-space: nowrap;
}

.map-loading-dot {
  width: 8px;
  height: 8px;

  background: var(--color-primary);
  border-radius: 50%;

  animation: map-loading-pulse 1.1s ease-in-out infinite;
}

@keyframes map-loading-pulse {
  0%,
  100% {
    opacity: 0.35;
  }
  50% {
    opacity: 1;
  }
}

.map-marker {
  position: absolute;
  transform: translate(-50%, -50%);
}

.map-marker.start .dot {
  display: block;

  width: 16px;
  height: 16px;

  background: var(--color-primary);
  border: 3px solid var(--color-surface);
  border-radius: 50%;
  box-shadow: var(--shadow-sm);
}

.map-marker.refuge {
  display: flex;
  flex-direction: column;
  align-items: center;

  gap: 3px;
}

.pin {
  display: grid;
  place-items: center;

  width: 28px;
  height: 28px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 50%;
  box-shadow: var(--shadow-sm);

  color: var(--color-primary);
}

.pin-label {
  padding: 3px 7px;

  background: var(--color-surface);
  border-radius: 6px;

  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
}

.route-summary {
  padding: 19px;

  margin-top: 16px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.summary-top {
  display: flex;
  align-items: center;
  justify-content: space-between;

  gap: 10px;
}

.skeleton-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-top h2 {
  margin: 0;

  color: var(--color-text);
  font-size: 16px;
  font-weight: 700;
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

.progress-row {
  margin-top: 16px;
}

.progress-label {
  display: flex;
  align-items: center;
  gap: 6px;

  margin-top: 9px;

  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px 10px;

  margin-top: 18px;
  padding-top: 16px;

  border-top: 1px solid var(--color-border);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.stat-label {
  color: var(--color-text-faint);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}

.stat-value {
  color: var(--color-text);
  font-size: 15px;
  font-weight: 700;
}

.stat-value-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;

  color: var(--color-primary);
  font-size: 13px;
}

.skeleton-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;

  padding-top: 16px;

  border-top: 1px solid var(--color-border);
}

@media (min-width: 768px) {
  .map-area {
    height: 420px;
  }
}

@media (min-width: 1024px) {
  .route-summary {
    max-width: 480px;
  }
}
</style>
