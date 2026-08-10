<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import { getRefuges } from "../services/refuges";
import { getQuietSpaces } from "../services/map";
import { getAccurateCurrentLocation } from "../services/geolocation";
import { FALLBACK_ORIGIN } from "../services/routes";
import { openExternalNavigation } from "../services/externalNavigation";

const router = useRouter();
const refuges = ref([]);
const loading = ref(true);
const filter = ref("all");

const EARTH_RADIUS_M = 6_371_000;

function distanceMetres(a, b) {
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const lat1 = (a.lat * Math.PI) / 180;
  const lat2 = (b.lat * Math.PI) / 180;
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

function formatDistance(metres) {
  if (metres == null) return null;
  return metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`;
}

// Refuges already have real coordinates — send the user straight to the map
// with a route generated live from their current location, instead of
// making them re-pick from the Routes page (they already know where
// they're going, they just clicked it).
function navigateTo(refuge) {
  router.push({
    path: "/map",
    query: { destination: refuge.name, destLat: refuge.lat, destLng: refuge.lng },
  });
}

const filterOptions = [
  { value: "all", label: "All" },
  { value: "Cafe", label: "Cafes" },
  { value: "Library", label: "Libraries" },
  { value: "Park", label: "Parks" },
];

const filteredRefuges = computed(() => {
  const list =
    filter.value === "all" ? refuges.value : refuges.value.filter((r) => r.type === filter.value);

  // Refuges actually on the current route come first (nearest along the
  // route first); everything else follows, nearest to the user first.
  // Refuges with no distance info yet (location still resolving) sink to
  // the end rather than jumping around once it arrives.
  return [...list].sort((a, b) => {
    if (a.onRoute !== b.onRoute) return a.onRoute ? -1 : 1;
    if (a.onRoute && b.onRoute) return a.distanceFromRouteM - b.distanceFromRouteM;
    if (a.distanceM == null) return 1;
    if (b.distanceM == null) return -1;
    return a.distanceM - b.distanceM;
  });
});

onMounted(async () => {
  refuges.value = await getRefuges();
  loading.value = false;

  // Distance from the user is a nice-to-have, not worth blocking the list
  // on — fill it in once location resolves (or falls back) without making
  // anyone wait for it.
  (async () => {
    let origin;
    try {
      origin = await getAccurateCurrentLocation();
    } catch {
      origin = FALLBACK_ORIGIN;
    }
    refuges.value = refuges.value.map((refuge) => ({
      ...refuge,
      distanceM: distanceMetres(origin, refuge),
    }));
  })();

  // If a route is currently active (the user just planned one, or is on
  // their way somewhere), flag whichever refuges actually sit along it —
  // "on the way" is far more useful here than just "nearby".
  let lastRouteId;
  try {
    lastRouteId = sessionStorage.getItem("lastRouteId");
  } catch {
    lastRouteId = null;
  }

  if (lastRouteId) {
    try {
      const onRoute = await getQuietSpaces(lastRouteId);
      const onRouteById = new Map(onRoute.map((space) => [String(space.id), space]));

      refuges.value = refuges.value.map((refuge) => {
        const match = onRouteById.get(String(refuge.id));
        return match
          ? { ...refuge, onRoute: true, distanceFromRouteM: match.distanceFromRouteM }
          : refuge;
      });
    } catch {
      // No active route, or it's since expired/been cleared — refuges just
      // show without the "on the way" flag, not worth surfacing an error for.
    }
  }
});
// Every refuge card jumps straight to /map — pre-download its chunk (which
// includes the ~1.8MB Mapbox GL bundle) now instead of making the user wait
// for it after they tap a card.
import("../pages/Map.vue");
</script>

<template>
  <PageShell>
    <header class="page-header">
      <h1>Sensory refuges near you</h1>
      <p>Parks, libraries and quiet public spaces to take a break.</p>
    </header>

    <SegmentedTabs v-model="filter" :options="filterOptions" class="filter-tabs" />

    <div v-if="loading" class="refuge-list">
      <div v-for="n in 4" :key="n" class="refuge-card">
        <SkeletonBlock width="44px" height="44px" radius="12px" />

        <div class="refuge-body skeleton-lines">
          <SkeletonBlock width="60%" height="13px" />
          <SkeletonBlock width="40%" height="9px" />
          <SkeletonBlock width="90%" height="11px" />
        </div>
      </div>
    </div>

    <div v-else-if="filteredRefuges.length" class="refuge-list">
      <div v-for="refuge in filteredRefuges" :key="refuge.id" class="refuge-card">
        <button type="button" class="refuge-main" @click="navigateTo(refuge)">
          <div class="refuge-icon">
            <Icon :name="refuge.icon" :size="20" />
          </div>

          <div class="refuge-body">
            <div class="refuge-top">
              <h2>{{ refuge.name }}</h2>
              <span v-if="refuge.onRoute" class="distance on-route">
                On the way · {{ formatDistance(refuge.distanceFromRouteM) }}
              </span>
              <span v-else-if="refuge.distanceM != null" class="distance">
                {{ formatDistance(refuge.distanceM) }}
              </span>
            </div>

            <span class="refuge-type">{{ refuge.type }}</span>
            <p v-if="refuge.note">{{ refuge.note }}</p>
          </div>
        </button>

        <button
          type="button"
          class="directions-button"
          aria-label="Get walking directions"
          @click.stop="openExternalNavigation(refuge)"
        >
          <Icon name="navigation" :size="15" />
          Directions
        </button>
      </div>
    </div>

    <p v-else class="empty-state">No refuges in this category yet.</p>
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

  color: var(--color-text-muted);
  font-size: 13.5px;
}

.filter-tabs {
  margin-top: 20px;
}

.refuge-list {
  display: flex;
  flex-direction: column;
  gap: 12px;

  margin-top: 18px;
}

.empty-state {
  margin: 18px 0 0;
  padding: 30px;

  background: var(--color-surface-muted);
  border-radius: var(--radius-md);

  color: var(--color-text-muted);
  font-size: 13px;
  text-align: center;
}

.refuge-card {
  display: flex;
  flex-direction: column;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s ease;
}

.refuge-card:hover {
  border-color: #cfe3da;
}

.refuge-main {
  display: flex;
  gap: 13px;

  padding: 16px;
  text-align: left;
}

.directions-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;

  padding: 11px 16px;

  border-top: 1px solid var(--color-border);

  color: var(--color-primary);
  font-size: 12.5px;
  font-weight: 700;
}

.directions-button:hover {
  background: var(--color-surface-muted);
}

.refuge-icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;

  width: 44px;
  height: 44px;

  background: var(--color-primary-soft);
  border-radius: var(--radius-sm);

  color: var(--color-primary);
}

.refuge-body {
  flex: 1 1 auto;
  min-width: 0;
}

.refuge-body.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: 8px;

  padding-top: 2px;
}

.refuge-top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;

  gap: 8px;
}

.refuge-top h2 {
  margin: 0;

  color: var(--color-text);
  font-size: 14.5px;
  font-weight: 700;
}

.distance {
  flex: 0 0 auto;

  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.distance.on-route {
  padding: 3px 9px;

  background: var(--color-primary-soft);
  border-radius: var(--radius-pill);

  color: var(--color-primary);
}

.refuge-type {
  display: inline-block;

  margin-top: 5px;

  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}

.refuge-body p {
  margin: 7px 0 0;

  color: var(--color-text-muted);
  font-size: 12.5px;
  line-height: 1.55;
}

@media (min-width: 768px) {
  .refuge-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
