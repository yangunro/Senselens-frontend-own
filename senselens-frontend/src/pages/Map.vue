<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import { importLibrary } from "@googlemaps/js-api-loader";
import { ensureGoogleMapsConfigured } from "../services/googleMapsLoader";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import ProgressBar from "../components/ProgressBar.vue";
import { getRouteDetail, getQuietSpaces, getSensoryAlert, getForecast, getPedestrianCounts } from "../services/map";
import { getRouteOptions } from "../services/routes";
import { watchCurrentLocation, getAccurateCurrentLocation } from "../services/geolocation";
import { usePreferences, toggleValue } from "../composables/usePreferences";

const route = useRoute();
const router = useRouter();
const preferences = usePreferences();

const activeRoute = ref(null);
const quietSpaces = ref([]);
const alert = ref(null);
const forecast = ref(null);
const pedestrianCounts = ref(null);
const alertDismissed = ref(false);
const loading = ref(true);

const MELBOURNE_CBD = { lat: -37.8136, lng: 144.9631 };

// A calm, round marker for refuge/quiet-space pins — Google's default red teardrop
// pin reads as an alert, which fights the "this is a safe, calming spot" message.
const REFUGE_ICON_URL =
  "data:image/svg+xml;charset=UTF-8," +
  encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 34 34">
      <circle cx="17" cy="17" r="14" fill="#fffdf9" stroke="#2f6f5f" stroke-width="2"/>
      <g transform="translate(9,9)" stroke="#2f6f5f" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none">
        <path d="M8 2 2 14h12L8 2Z"/>
        <line x1="6" y1="14" x2="8" y2="9"/>
        <line x1="10" y1="14" x2="8" y2="9"/>
      </g>
    </svg>
  `);

const mapEl = ref(null);
const mapReady = ref(false);
const mapError = ref(false);
let map = null;
let startMarker = null;
let refugeMarkers = [];
let sensorMarkers = [];
let routePolyline = null;
let currentLocationMarker = null;
let stopLocationWatch = null;

ensureGoogleMapsConfigured();

async function initMap() {
  try {
    const { Map } = await importLibrary("maps");
    await importLibrary("marker");
    map = new Map(mapEl.value, {
      center: MELBOURNE_CBD,
      zoom: 15,
      disableDefaultUI: true,
      zoomControl: true,
      clickableIcons: false,
    });
    mapReady.value = true;
    renderMapLayer();
  } catch (err) {
    console.error("Google Maps failed to load", err);
    mapError.value = true;
  }
}

function clearRefugeMarkers() {
  refugeMarkers.forEach((marker) => marker.setMap(null));
  refugeMarkers = [];
}

function clearSensorMarkers() {
  sensorMarkers.forEach((marker) => marker.setMap(null));
  sensorMarkers = [];
}

// Real-time pedestrian sensor readings, colour-coded on the same low/medium/high
// scale as everything else in the app — relative to today's busiest sensor.
function renderSensorMarkers() {
  clearSensorMarkers();
  if (!map || !pedestrianCounts.value?.sensors?.length) return;

  const max = pedestrianCounts.value.maximumCount || 1;
  sensorMarkers = pedestrianCounts.value.sensors.map((sensor) => {
    const ratio = sensor.minuteCount / max;
    const color = ratio > 0.66 ? "#b8563d" : ratio > 0.33 ? "#a97a1f" : "#2f8f6f";
    return new google.maps.Marker({
      position: { lat: sensor.lat, lng: sensor.lng },
      map,
      title: `${sensor.name}: ${sensor.minuteCount} pedestrians/min`,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 6 + ratio * 6,
        fillColor: color,
        fillOpacity: 0.55,
        strokeColor: color,
        strokeWeight: 1,
      },
      zIndex: 1,
    });
  });
}

// Classic "blue dot" — distinct from the green route-start marker so it
// reads as "you, right now" rather than "where this route begins".
function renderCurrentLocationMarker(position) {
  if (!map) return;
  currentLocationMarker?.setMap(null);
  currentLocationMarker = new google.maps.Marker({
    position: { lat: position.lat, lng: position.lng },
    map,
    title: `Your location (±${Math.round(position.accuracy)} m)`,
    zIndex: 3,
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 7,
      fillColor: "#4285f4",
      fillOpacity: 1,
      strokeColor: "#fffdf9",
      strokeWeight: 3,
    },
  });
}

function renderMapLayer() {
  if (!map || !activeRoute.value) return;

  const path = activeRoute.value.path ?? [];

  routePolyline?.setMap(null);
  if (path.length) {
    routePolyline = new google.maps.Polyline({
      path,
      strokeColor: "#2f6f5f",
      strokeWeight: 5,
      strokeOpacity: 0.85,
      map,
    });
  }

  startMarker?.setMap(null);
  if (path.length) {
    startMarker = new google.maps.Marker({
      position: path[0],
      map,
      title: "Start",
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 8,
        fillColor: "#2f6f5f",
        fillOpacity: 1,
        strokeColor: "#fffdf9",
        strokeWeight: 3,
      },
    });
  }

  clearRefugeMarkers();
  if (showRefuges.value) {
    refugeMarkers = quietSpaces.value.map(
      (space) =>
        new google.maps.Marker({
          position: { lat: space.lat, lng: space.lng },
          map,
          title: space.label,
          icon: {
            url: REFUGE_ICON_URL,
            scaledSize: new google.maps.Size(34, 34),
            anchor: new google.maps.Point(17, 17),
          },
        })
    );
  }

  const bounds = new google.maps.LatLngBounds();
  path.forEach((point) => bounds.extend(point));
  if (showRefuges.value) {
    quietSpaces.value.forEach((space) => bounds.extend({ lat: space.lat, lng: space.lng }));
  }
  if (!bounds.isEmpty()) map.fitBounds(bounds, 48);
}

// "Always show refuge spaces" preference — when off, quiet-space markers stay off the map.
const showRefuges = computed(() => toggleValue(preferences, "refuges", true));

// How much crowding the user can tolerate before a route counts as "too busy" —
// derived from their crowd-sensitivity preference (0 low sensitivity/high tolerance
// … 2 high sensitivity/low tolerance).
const crowdTolerance = computed(() => {
  const crowdSlider = preferences.sliders.find((slider) => slider.key === "crowd");
  return crowdSlider ? 2 - crowdSlider.value : 2;
});
const levelRank = { low: 0, medium: 1, high: 2 };

const crowdExceeded = computed(
  () => !!activeRoute.value && levelRank[activeRoute.value.level] > crowdTolerance.value
);

// Prioritise a personalised "this route is busier than you like" banner over the
// generic conditions alert — both drive users toward the calmer alternativeId route.
const activeBanner = computed(() => {
  if (alertDismissed.value) return null;
  if (crowdExceeded.value) {
    return {
      title: "This route is busier than your comfort setting",
      message: "Your crowd sensitivity preference suggests a calmer path is available.",
    };
  }
  if (alert.value) return alert.value;
  return null;
});

function clearRouteView() {
  loading.value = false;
  activeRoute.value = null;
  quietSpaces.value = [];
  alert.value = null;
  forecast.value = null;
  clearRefugeMarkers();
  routePolyline?.setMap(null);
  startMarker?.setMap(null);
}

async function loadMap() {
  let routeId = route.query.route;
  alertDismissed.value = false;

  // Arrived from a refuge card — no route id yet, but we do have a
  // destination and its coordinates, so generate the route on the fly
  // instead of sending the user back through the Routes picker.
  const destLat = Number(route.query.destLat);
  const destLng = Number(route.query.destLng);
  if (!routeId && route.query.destination && Number.isFinite(destLat) && Number.isFinite(destLng)) {
    loading.value = true;
    try {
      const origin = await getAccurateCurrentLocation();
      const options = await getRouteOptions(route.query.destination, { lat: destLat, lng: destLng }, origin);
      const recommended = options.find((option) => option.recommended) ?? options[0];
      if (recommended) routeId = recommended.id;
    } catch (err) {
      console.warn("On-the-fly route generation failed:", err);
    }
  }

  // No route to show (bare /map, or generation above failed) — show the
  // plain map rather than a route summary for a route the user never chose.
  if (!routeId) {
    clearRouteView();
    return;
  }

  loading.value = true;
  const [routeDetail, spaces, sensoryAlert, sensoryForecast] = await Promise.all([
    getRouteDetail(routeId),
    getQuietSpaces(routeId),
    getSensoryAlert(routeId),
    getForecast(routeId),
  ]);
  activeRoute.value = routeDetail;
  quietSpaces.value = spaces;
  alert.value = sensoryAlert;
  forecast.value = sensoryForecast;
  loading.value = false;
  renderMapLayer();
}

async function loadPedestrianCounts() {
  pedestrianCounts.value = await getPedestrianCounts();
  renderSensorMarkers();
}

onMounted(async () => {
  await initMap();
  loadMap();
  loadPedestrianCounts();
  stopLocationWatch = watchCurrentLocation(
    renderCurrentLocationMarker,
    (err) => console.warn("Live location update failed:", err)
  );
});
watch(() => route.query.route, loadMap);
watch(showRefuges, renderMapLayer);

onBeforeUnmount(() => {
  clearRefugeMarkers();
  clearSensorMarkers();
  routePolyline?.setMap(null);
  startMarker?.setMap(null);
  currentLocationMarker?.setMap(null);
  stopLocationWatch?.();
});

function reroute() {
  if (activeRoute.value?.alternativeId) {
    router.push({ path: "/map", query: { route: activeRoute.value.alternativeId } });
  } else {
    alertDismissed.value = true;
  }
}
</script>

<template>
  <PageShell>
    <div class="map-shell">
      <div class="map-overlays">
        <transition name="fade">
          <div v-if="activeBanner" class="alert-banner">
            <div class="alert-text">
              <Icon class="alert-icon" name="alert" :size="18" />

              <div>
                <strong>{{ activeBanner.title }}</strong>
                <p>{{ activeBanner.message }}</p>
              </div>
            </div>

            <button class="reroute-button" @click="reroute">
              <Icon name="refresh" :size="13" />
              {{ activeRoute?.alternativeId ? "Take calmer route" : "Dismiss" }}
            </button>
          </div>
        </transition>

        <div v-if="forecast" class="forecast-banner">
          <Icon class="forecast-icon" name="trendingUp" :size="18" />

          <div>
            <strong>{{ forecast.levelLabel }} expected in the next hour</strong>
            <p>{{ forecast.basis }}</p>
            <p class="forecast-disclaimer">Estimate based on available pedestrian data — actual conditions may vary.</p>
          </div>
        </div>
      </div>

      <div class="map-area">
        <div ref="mapEl" class="map-canvas"></div>

        <div v-if="loading || !mapReady" class="map-loading">
          <span class="map-loading-dot"></span>
          Finding your calm route…
        </div>

        <div v-if="mapError" class="map-error">
          Couldn't load the map. Check your connection and try again.
        </div>
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
        </div>

        <div v-if="activeRoute.transit" class="transit-row">
          <Icon name="train" :size="15" />
          <span>{{ activeRoute.transit.walk }} walk to {{ activeRoute.transit.stop }}</span>
        </div>

        <div v-if="activeRoute.factors?.length" class="factor-chips">
          <span v-for="factor in activeRoute.factors" :key="factor.label" class="factor-chip">
            <Icon :name="factor.icon" :size="13" />
            {{ factor.label }}
          </span>
        </div>
      </section>
    </div>
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

.forecast-banner {
  display: flex;
  align-items: flex-start;

  gap: 11px;
  padding: 15px 16px;

  margin-top: 12px;

  background: var(--color-primary-soft);
  border: 1px solid #d3e3da;
  border-radius: var(--radius-md);
}

.forecast-icon {
  flex: 0 0 auto;
  margin-top: 1px;

  color: var(--color-primary-dark);
}

.forecast-banner strong {
  display: block;

  color: var(--color-primary-dark);
  font-size: 13px;
  font-weight: 700;
}

.forecast-banner p {
  margin: 3px 0 0;

  color: var(--color-text-muted);
  font-size: 12px;
}

.forecast-disclaimer {
  color: var(--color-text-faint);
  font-size: 10.5px;
  font-style: italic;
}

.transit-row {
  display: flex;
  align-items: center;
  gap: 8px;

  margin-top: 16px;
  padding-top: 16px;

  border-top: 1px solid var(--color-border);

  color: var(--color-text-muted);
  font-size: 12.5px;
  font-weight: 600;
}

.transit-row :deep(.sl-icon) {
  color: var(--color-primary);
}

.factor-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  margin-top: 12px;
}

.factor-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;

  padding: 6px 11px;

  background: var(--color-surface-muted);
  border-radius: var(--radius-pill);

  color: var(--color-text-muted);
  font-size: 11.5px;
  font-weight: 600;
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

.map-canvas {
  position: absolute;
  inset: 0;
}

.map-error {
  position: absolute;
  inset: 0;

  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  text-align: center;

  background: var(--color-surface-muted);

  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 600;
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
  /* Desktop: the map fills the whole shell edge-to-edge and everything
     else — alerts, forecast, route summary — floats on top of it as
     docked panels, instead of stacking in a column below a small map. */
  .map-shell {
    position: relative;

    /* .page-content's own padding-top (44px) isn't enough clearance on its
       own — the top nav is an absolutely-positioned 78px-tall box anchored
       to .app-container's top edge, so it overlaps anything starting much
       closer than that to the top. */
    margin-top: 44px;
    height: clamp(520px, calc(100vh - 250px), 820px);
  }

  .map-area {
    position: absolute;
    inset: 0;

    height: 100%;
    margin-top: 0;
  }

  .map-overlays {
    position: absolute;
    z-index: 2;
    top: 20px;
    left: 20px;

    display: flex;
    flex-direction: column;
    gap: 12px;

    width: 400px;
    max-width: calc(100% - 380px);
  }

  .alert-banner,
  .forecast-banner {
    margin-top: 0;
    box-shadow: var(--shadow-md);
  }

  .route-summary {
    position: absolute;
    z-index: 2;
    top: 20px;
    right: 20px;
    bottom: 20px;

    overflow-y: auto;
    width: 340px;
    max-width: calc(100% - 420px);
    margin-top: 0;

    box-shadow: var(--shadow-md);
  }
}
</style>
