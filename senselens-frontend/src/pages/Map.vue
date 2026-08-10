<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import mapboxgl from "../services/mapbox";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import ProgressBar from "../components/ProgressBar.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import {
  getRouteDetail,
  getQuietSpaces,
  getSensoryAlert,
  getForecast,
  getPedestrianCounts,
  getPedestrianForecast,
} from "../services/map";
import { FALLBACK_ORIGIN, getRouteOptions } from "../services/routes";
import { watchCurrentLocation, getAccurateCurrentLocation } from "../services/geolocation";
import { openExternalNavigation } from "../services/externalNavigation";
import { estimateRouteProgress } from "../services/routeProgress";
import { saveRoute } from "../services/savedRoutes";
import { usePreferences, toggleValue } from "../composables/usePreferences";

const route = useRoute();
const router = useRouter();
const preferences = usePreferences();

const activeRoute = ref(null);
const liveProgress = ref(null);
const quietSpaces = ref([]);
const alert = ref(null);
const forecast = ref(null);
const pedestrianCounts = ref(null);
const pedestrianForecast = ref(null);
// "live" shows real-time sensor readings; "1"/"2"/"3" show that many hours'
// predicted crowding instead.
const sensorViewMode = ref("live");
const alertDismissed = ref(false);
const loading = ref(true);
// Heatmap on by default — a density picture of where the crowds are reads
// faster than a scatter of small dots; the dots stay available as a toggle
// for anyone who wants exact per-sensor readings.
const heatmapVisible = ref(true);

const sensorViewOptions = [
  { value: "live", label: "Now" },
  { value: "1", label: "1h" },
  { value: "2", label: "2h" },
  { value: "3", label: "3h" },
];

const LEVEL_COLOR = { low: "#2f8f6f", medium: "#a97a1f", high: "#b8563d" };

const forecastForSelectedHour = computed(() => {
  if (sensorViewMode.value === "live") return null;
  return pedestrianForecast.value?.forecasts?.find((f) => f.hoursAhead === Number(sensorViewMode.value)) ?? null;
});

const alertsForSelectedHour = computed(() => {
  if (sensorViewMode.value === "live") return [];
  return (pedestrianForecast.value?.alerts ?? []).filter((a) => a.hoursAhead === Number(sensorViewMode.value));
});

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
let currentLocationMarker = null;
let stopLocationWatch = null;

// Bakes transparency into the colour itself (rgba) rather than the element's
// `opacity` CSS property — Mapbox GL's Marker silently resets `opacity` back
// to 1 (its built-in occlusion-fade behaviour), so setting it directly never
// sticks.
function withAlpha(hex, alpha) {
  if (alpha >= 1) return hex;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function createCircleElement(size, color, { strokeColor = "#fffdf9", strokeWidth = 3, opacity = 1 } = {}) {
  const el = document.createElement("div");
  el.style.width = `${size}px`;
  el.style.height = `${size}px`;
  el.style.borderRadius = "50%";
  el.style.boxSizing = "border-box";
  el.style.background = withAlpha(color, opacity);
  el.style.border = `${strokeWidth}px solid ${withAlpha(strokeColor, opacity)}`;
  return el;
}

function initMap() {
  return new Promise((resolve) => {
    try {
      map = new mapboxgl.Map({
        container: mapEl.value,
        style: "mapbox://styles/mapbox/streets-v12",
        center: [MELBOURNE_CBD.lng, MELBOURNE_CBD.lat],
        zoom: 15,
      });
      map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");
      map.once("load", () => {
        mapReady.value = true;
        resolve();
      });
      map.once("error", (err) => {
        console.error("Mapbox failed to load", err);
        mapError.value = true;
        resolve();
      });
    } catch (err) {
      console.error("Mapbox failed to load", err);
      mapError.value = true;
      resolve();
    }
  });
}

function clearRefugeMarkers() {
  refugeMarkers.forEach((marker) => marker.remove());
  refugeMarkers = [];
}

function clearSensorMarkers() {
  sensorMarkers.forEach((marker) => marker.remove());
  sensorMarkers = [];
}

// Real-time pedestrian sensor readings, colour-coded on the same low/medium/high
// scale as everything else in the app — relative to today's busiest sensor.
// Switches to predicted crowding for the selected hour when sensorViewMode
// isn't "live", using the same marker styling either way.
function renderSensorMarkers() {
  clearSensorMarkers();
  if (!map) return;
  // The heatmap already shows crowd density — don't stack individual dots
  // on top of it too, that's redundant and busy. Dots come back when the
  // user switches to the "Points" view.
  if (heatmapVisible.value) return;

  if (sensorViewMode.value === "live") {
    if (!pedestrianCounts.value?.sensors?.length) return;
    const max = pedestrianCounts.value.maximumCount || 1;
    sensorMarkers = pedestrianCounts.value.sensors.map((sensor) => {
      const ratio = sensor.minuteCount / max;
      const color = ratio > 0.66 ? LEVEL_COLOR.high : ratio > 0.33 ? LEVEL_COLOR.medium : LEVEL_COLOR.low;
      const el = createCircleElement((6 + ratio * 6) * 2, color, { strokeColor: color, strokeWidth: 1, opacity: 0.4 });
      el.title = `${sensor.name}: ${sensor.minuteCount} pedestrians/min`;
      return new mapboxgl.Marker({ element: el }).setLngLat([sensor.lng, sensor.lat]).addTo(map);
    });
    return;
  }

  const hourData = forecastForSelectedHour.value;
  if (!hourData?.sensors?.length) return;
  const max = Math.max(...hourData.sensors.map((s) => s.predictedCountPerMinute), 1);
  sensorMarkers = hourData.sensors.map((sensor) => {
    const ratio = sensor.predictedCountPerMinute / max;
    const color = LEVEL_COLOR[sensor.level] ?? LEVEL_COLOR.low;
    const el = createCircleElement((6 + ratio * 6) * 2, color, { strokeColor: color, strokeWidth: 1, opacity: 0.4 });
    el.title = `${sensor.name}: ~${sensor.predictedCountPerMinute} pedestrians/min predicted in ${sensorViewMode.value}h`;
    return new mapboxgl.Marker({ element: el }).setLngLat([sensor.lng, sensor.lat]).addTo(map);
  });
}

// Same underlying sensor readings as renderSensorMarkers, reshaped into a
// GeoJSON point source so Mapbox's native `heatmap` layer type can do the
// density blending — far more legible than a scatter of dots once there
// are a few dozen sensors on screen at once.
function crowdHeatmapFeatures() {
  if (sensorViewMode.value === "live") {
    const sensors = pedestrianCounts.value?.sensors ?? [];
    const max = pedestrianCounts.value?.maximumCount || 1;
    return sensors.map((sensor) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [sensor.lng, sensor.lat] },
      properties: { weight: Math.min(1, sensor.minuteCount / max) },
    }));
  }

  const hourData = forecastForSelectedHour.value;
  const sensors = hourData?.sensors ?? [];
  const max = Math.max(...sensors.map((s) => s.predictedCountPerMinute), 1);
  return sensors.map((sensor) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [sensor.lng, sensor.lat] },
    properties: { weight: Math.min(1, sensor.predictedCountPerMinute / max) },
  }));
}

// The heatmap source/layer is created once (empty) the moment the map style
// loads, right before anything else — Mapbox stacks new layers on top of
// existing ones, so adding it first guarantees the route line and markers
// always render above the heat, never underneath it.
function ensureHeatmapLayer() {
  if (!map || map.getSource("crowd-heat")) return;
  map.addSource("crowd-heat", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addLayer({
    id: "crowd-heatmap",
    type: "heatmap",
    source: "crowd-heat",
    paint: {
      "heatmap-weight": ["interpolate", ["linear"], ["get", "weight"], 0, 0, 1, 1],
      "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 12, 0.8, 17, 2.4],
      // Same low/medium/high palette as everything else in the app (sage
      // green through amber to terracotta), fading in from transparent so
      // sparse areas don't get a hard-edged blob.
      "heatmap-color": [
        "interpolate",
        ["linear"],
        ["heatmap-density"],
        0, "rgba(47, 143, 111, 0)",
        0.25, "rgba(47, 143, 111, 0.55)",
        0.5, "rgba(169, 122, 31, 0.65)",
        0.75, "rgba(184, 86, 61, 0.75)",
        1, "rgba(184, 86, 61, 0.9)",
      ],
      "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 12, 16, 17, 36],
      "heatmap-opacity": 0.8,
    },
  });
}

function renderCrowdHeatmap() {
  if (!map || !mapReady.value) return;
  ensureHeatmapLayer();
  map.getSource("crowd-heat")?.setData({ type: "FeatureCollection", features: crowdHeatmapFeatures() });
  map.setLayoutProperty("crowd-heatmap", "visibility", heatmapVisible.value ? "visible" : "none");
}

function toggleHeatmap() {
  heatmapVisible.value = !heatmapVisible.value;
  renderSensorMarkers();
  renderCrowdHeatmap();
}

// Classic "blue dot" — distinct from the green route-start marker so it
// reads as "you, right now" rather than "where this route begins".
function renderCurrentLocationMarker(position) {
  if (activeRoute.value) {
    liveProgress.value = estimateRouteProgress(position, activeRoute.value);
  }

  if (!map) return;
  currentLocationMarker?.remove();
  const el = createCircleElement(14, "#4285f4");
  el.title = `Your location (±${Math.round(position.accuracy)} m)`;
  currentLocationMarker = new mapboxgl.Marker({ element: el }).setLngLat([position.lng, position.lat]).addTo(map);
}

// Route path is drawn as a GeoJSON line layer rather than a Marker-style
// polyline object — Mapbox GL has no Polyline class, sources/layers are how
// any line gets drawn, and both need the map's style to be loaded first.
function setRouteLine(path) {
  if (!map || !mapReady.value) return;
  const geojson = {
    type: "Feature",
    geometry: { type: "LineString", coordinates: path.map((point) => [point.lng, point.lat]) },
  };
  if (map.getSource("route")) {
    map.getSource("route").setData(geojson);
  } else if (path.length) {
    map.addSource("route", { type: "geojson", data: geojson });
    map.addLayer({
      id: "route-line",
      type: "line",
      source: "route",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": "#2f6f5f", "line-width": 5, "line-opacity": 0.85 },
    });
  }
}

function renderMapLayer() {
  if (!map || !activeRoute.value) return;

  const path = activeRoute.value.path ?? [];

  setRouteLine(path);

  startMarker?.remove();
  if (path.length) {
    const el = createCircleElement(16, "#2f6f5f");
    el.title = "Start";
    startMarker = new mapboxgl.Marker({ element: el }).setLngLat([path[0].lng, path[0].lat]).addTo(map);
  }

  clearRefugeMarkers();
  if (showRefuges.value) {
    refugeMarkers = quietSpaces.value.map((space) => {
      const el = document.createElement("div");
      el.style.width = "34px";
      el.style.height = "34px";
      el.style.backgroundImage = `url("${REFUGE_ICON_URL}")`;
      el.style.backgroundSize = "contain";
      el.title = space.label;
      return new mapboxgl.Marker({ element: el }).setLngLat([space.lng, space.lat]).addTo(map);
    });
  }

  const bounds = new mapboxgl.LngLatBounds();
  path.forEach((point) => bounds.extend([point.lng, point.lat]));
  if (showRefuges.value) {
    quietSpaces.value.forEach((space) => bounds.extend([space.lng, space.lat]));
  }
  if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 48 });
}

// "Always show refuge spaces" preference — when off, quiet-space markers stay off the map.
const showRefuges = computed(() => toggleValue(preferences, "refuges", true));
const avoidConstruction = computed(() => toggleValue(preferences, "construction", false));

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

const constructionExceeded = computed(
  () => !!activeRoute.value?.hasActiveConstruction && avoidConstruction.value
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
  if (constructionExceeded.value) {
    return {
      title: "This route passes active construction",
      message: "Your avoid-construction-zones preference suggests a clearer path is available.",
    };
  }
  if (alert.value) return alert.value;
  return null;
});

function clearRouteView() {
  loading.value = false;
  activeRoute.value = null;
  liveProgress.value = null;
  quietSpaces.value = [];
  alert.value = null;
  forecast.value = null;
  showSaveForm.value = false;
  saved.value = false;
  clearRefugeMarkers();
  setRouteLine([]);
  startMarker?.remove();
  startMarker = null;
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
    // Live location isn't available (denied, unsupported, too inaccurate) —
    // fall back to a fixed starting point rather than giving up on a route
    // entirely, matching Routes.vue's same fallback for the Home search path.
    let origin;
    try {
      origin = await getAccurateCurrentLocation();
    } catch (err) {
      console.warn("Live location unavailable, using approximate starting point:", err);
      origin = FALLBACK_ORIGIN;
    }
    try {
      const options = await getRouteOptions(route.query.destination, { lat: destLat, lng: destLng }, origin, {
        avoidConstruction: avoidConstruction.value,
      });
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
  liveProgress.value = null;
  quietSpaces.value = spaces;
  alert.value = sensoryAlert;
  forecast.value = sensoryForecast;
  showSaveForm.value = false;
  saved.value = false;
  loading.value = false;
  renderMapLayer();

  // Lets the Refuges page know which route is currently active, so it can
  // flag refuges that are actually on the way instead of just nearby.
  try {
    sessionStorage.setItem("lastRouteId", routeId);
  } catch {
    // Storage unavailable (private browsing etc) — refuges just won't get
    // the "on the way" flag this session, not worth failing the route over.
  }
}

async function loadPedestrianCounts() {
  pedestrianCounts.value = await getPedestrianCounts();
  renderSensorMarkers();
  if (sensorViewMode.value === "live") renderCrowdHeatmap();
}

async function loadPedestrianForecast() {
  // Always fetched at the full 3-hour horizon — the 1h/2h/3h toggle just
  // switches which already-loaded hour's data is shown, no re-fetching.
  pedestrianForecast.value = await getPedestrianForecast();
  if (sensorViewMode.value !== "live") {
    renderSensorMarkers();
    renderCrowdHeatmap();
  }
}

onMounted(() => {
  // The route summary panel is pure data (backend calls) and doesn't need
  // the map to be ready — don't make it wait on Mapbox's tile/style load,
  // which is the slower of the two. Once the map does finish, re-render
  // whatever route/sensor data already arrived while it was loading.
  initMap().then(() => {
    renderMapLayer();
    renderSensorMarkers();
    renderCrowdHeatmap();
  });
  loadMap();
  loadPedestrianCounts();
  loadPedestrianForecast();
  stopLocationWatch = watchCurrentLocation(
    renderCurrentLocationMarker,
    (err) => console.warn("Live location update failed:", err)
  );
});
watch(() => route.query.route, loadMap);
watch(showRefuges, renderMapLayer);
watch(sensorViewMode, () => {
  renderSensorMarkers();
  renderCrowdHeatmap();
});

onBeforeUnmount(() => {
  clearRefugeMarkers();
  clearSensorMarkers();
  startMarker?.remove();
  currentLocationMarker?.remove();
  stopLocationWatch?.();
  map?.remove();
});

function reroute() {
  if (activeRoute.value?.alternativeId) {
    router.push({ path: "/map", query: { route: activeRoute.value.alternativeId } });
  } else {
    alertDismissed.value = true;
  }
}

const showSaveForm = ref(false);
const saveLabel = ref("");
const saving = ref(false);
const saved = ref(false);
const saveError = ref("");

function openSaveForm() {
  // Best-effort default — the place name is only known when we arrived via
  // search or a refuge card; picking a route straight off the Routes list
  // has no name to fall back on, so an empty field beats a wrong guess.
  saveLabel.value = route.query.destination || "";
  saveError.value = "";
  showSaveForm.value = true;
}

async function confirmSave() {
  if (!activeRoute.value) return;
  saving.value = true;
  saveError.value = "";
  try {
    await saveRoute({
      label: saveLabel.value.trim() || "Saved route",
      origin: activeRoute.value.origin,
      destination: activeRoute.value.destination,
      level: activeRoute.value.level,
      distanceM: activeRoute.value.distanceMeters,
      durationMin: activeRoute.value.durationMinutes,
    });
    saved.value = true;
    showSaveForm.value = false;
  } catch (err) {
    console.warn("Saving route failed:", err);
    saveError.value = "Couldn't save this route. Try again.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <PageShell>
    <div class="map-shell">
      <div class="map-overlays">
        <div class="sensor-view-toggle">
          <SegmentedTabs v-model="sensorViewMode" :options="sensorViewOptions" />
        </div>

        <div v-if="alertsForSelectedHour.length" class="forecast-alerts">
          <Icon class="forecast-icon" name="alert" :size="16" />

          <div>
            <strong>{{ alertsForSelectedHour.length }} area{{ alertsForSelectedHour.length > 1 ? "s" : "" }} may get busy</strong>
            <p v-for="(item, index) in alertsForSelectedHour.slice(0, 3)" :key="index">{{ item.message }}</p>
          </div>
        </div>

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
            <p class="forecast-disclaimer">Estimate based on available pedestrian data. Actual conditions may vary.</p>
          </div>
        </div>
      </div>

      <div class="map-area">
        <div ref="mapEl" class="map-canvas"></div>

        <button
          v-if="mapReady"
          type="button"
          class="heatmap-toggle"
          :class="{ active: heatmapVisible }"
          @click="toggleHeatmap"
        >
          <Icon name="trendingUp" :size="14" />
          {{ heatmapVisible ? "Heatmap" : "Points" }}
        </button>

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
          <ProgressBar :value="liveProgress?.progress ?? activeRoute.progress" />
          <span class="progress-label">
            <Icon name="check" :size="13" />
            {{ liveProgress?.progress ?? activeRoute.progress }}% of the way there
          </span>
        </div>

        <div v-if="liveProgress?.currentStep?.instruction" class="next-step-row">
          <Icon name="navigation" :size="15" />
          <span>
            {{ liveProgress.currentStep.instruction }}
            <template v-if="liveProgress.currentStep.remainingInStepM">
              · in {{ liveProgress.currentStep.remainingInStepM }} m
            </template>
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

        <button
          type="button"
          class="navigate-button"
          @click="openExternalNavigation(activeRoute.destination)"
        >
          <Icon name="navigation" :size="15" />
          Navigate with my maps app
        </button>

        <div v-if="showSaveForm" class="save-form">
          <input
            v-model="saveLabel"
            type="text"
            placeholder="Name this route (e.g. Home to work)"
            maxlength="80"
            @keyup.enter="confirmSave"
          />
          <div class="save-form-actions">
            <button type="button" class="save-form-cancel" @click="showSaveForm = false">Cancel</button>
            <button type="button" class="save-form-confirm" :disabled="saving" @click="confirmSave">
              {{ saving ? "Saving…" : "Save" }}
            </button>
          </div>
          <p v-if="saveError" class="save-error">{{ saveError }}</p>
        </div>
        <button v-else-if="saved" type="button" class="save-button saved" disabled>
          <Icon name="check" :size="15" />
          Saved
        </button>
        <button v-else type="button" class="save-button" @click="openSaveForm">
          <Icon name="bookmark" :size="15" />
          Save route
        </button>
      </section>
    </div>
  </PageShell>
</template>

<style scoped>
.sensor-view-toggle {
  align-self: flex-start;
}

.sensor-view-toggle :deep(.segmented-tabs) {
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.forecast-alerts {
  display: flex;
  align-items: flex-start;

  gap: 11px;
  padding: 15px 16px;

  margin-top: 12px;

  background: var(--color-alert-bg);
  border: 1px solid var(--color-alert-border);
  border-radius: var(--radius-md);
}

.forecast-alerts strong {
  display: block;

  color: #6b4d16;
  font-size: 13px;
  font-weight: 700;
}

.forecast-alerts p {
  margin: 4px 0 0;

  color: #8a6a2a;
  font-size: 12px;
  line-height: 1.5;
}

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

.next-step-row {
  display: flex;
  align-items: center;
  gap: 9px;

  margin-top: 14px;
  padding: 11px 14px;

  background: var(--color-primary-soft);
  border-radius: var(--radius-sm);

  color: var(--color-primary-dark);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
}

.next-step-row :deep(.sl-icon) {
  flex-shrink: 0;
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

.navigate-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  width: 100%;
  margin-top: 16px;
  padding: 13px 16px;

  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);

  color: white;
  font-size: 13.5px;
  font-weight: 700;
  transition: background 0.15s ease;
}

.navigate-button:hover {
  background: var(--color-primary-dark);
}

.save-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  width: 100%;
  margin-top: 10px;
  padding: 13px 16px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);

  color: var(--color-primary-dark);
  font-size: 13.5px;
  font-weight: 700;
}

.save-button:hover {
  background: var(--color-surface-muted);
}

.save-button.saved {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.save-form {
  margin-top: 10px;
  padding: 13px;

  background: var(--color-surface-muted);
  border-radius: var(--radius-md);
}

.save-form input {
  width: 100%;
  padding: 10px 12px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);

  font-size: 13px;
}

.save-form-actions {
  display: flex;
  gap: 8px;

  margin-top: 9px;
}

.save-form-cancel,
.save-form-confirm {
  flex: 1 1 auto;

  padding: 10px 12px;

  border-radius: var(--radius-sm);

  font-size: 12.5px;
  font-weight: 700;
}

.save-form-cancel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);

  color: var(--color-text-muted);
}

.save-form-confirm {
  background: var(--color-primary);
  border: none;

  color: white;
}

.save-form-confirm:disabled {
  background: var(--color-text-faint);
}

.save-error {
  margin: 8px 0 0;

  color: var(--color-high);
  font-size: 12px;
}

.map-area {
  position: relative;
  overflow: hidden;

  height: 480px;

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

.heatmap-toggle {
  position: absolute;
  z-index: 1;
  bottom: 12px;
  left: 12px;

  display: flex;
  align-items: center;
  gap: 6px;

  padding: 9px 13px;

  background: var(--color-surface);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-sm);

  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.heatmap-toggle.active {
  color: var(--color-primary-dark);
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
    height: 560px;
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
