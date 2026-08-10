<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import { getSavedRoutes, deleteSavedRoute } from "../services/savedRoutes";

const router = useRouter();
const savedRoutes = ref([]);
const loading = ref(true);
const deletingId = ref(null);

function formatDistance(metres) {
  if (metres == null) return null;
  return metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`;
}

// The polyline/turn-by-turn behind a saved route only lives in the backend's
// in-memory cache and doesn't survive a restart — re-generating a fresh
// route to the same destination is both simpler and more honest than trying
// to replay a possibly-stale one, since crowd conditions change anyway.
function openRoute(saved) {
  router.push({
    path: "/map",
    query: {
      destination: saved.label,
      destLat: saved.destination.lat,
      destLng: saved.destination.lng,
    },
  });
}

async function removeSaved(saved, event) {
  event.stopPropagation();
  deletingId.value = saved.savedRouteId;
  try {
    await deleteSavedRoute(saved.savedRouteId);
    savedRoutes.value = savedRoutes.value.filter((r) => r.savedRouteId !== saved.savedRouteId);
  } catch (err) {
    console.warn("Deleting saved route failed:", err);
  } finally {
    deletingId.value = null;
  }
}

onMounted(async () => {
  savedRoutes.value = await getSavedRoutes();
  loading.value = false;
});
</script>

<template>
  <PageShell>
    <header class="page-header">
      <h1>Saved routes</h1>
      <p>Routes you've saved for quick access later.</p>
    </header>

    <div v-if="loading" class="saved-list">
      <div v-for="n in 3" :key="n" class="saved-card">
        <div class="saved-icon">
          <SkeletonBlock width="44px" height="44px" radius="12px" />
        </div>
        <div class="saved-body skeleton-lines">
          <SkeletonBlock width="60%" height="13px" />
          <SkeletonBlock width="40%" height="9px" />
        </div>
      </div>
    </div>

    <div v-else-if="savedRoutes.length" class="saved-list">
      <button
        v-for="saved in savedRoutes"
        :key="saved.savedRouteId"
        type="button"
        class="saved-card"
        @click="openRoute(saved)"
      >
        <div class="saved-icon">
          <Icon name="bookmark" :size="20" />
        </div>

        <div class="saved-body">
          <h2>{{ saved.label || "Saved route" }}</h2>
          <span class="saved-meta">
            <template v-if="saved.durationMin != null">{{ saved.durationMin }} min</template>
            <template v-if="saved.durationMin != null && saved.distanceM != null"> · </template>
            <template v-if="saved.distanceM != null">{{ formatDistance(saved.distanceM) }}</template>
          </span>
        </div>

        <button
          type="button"
          class="delete-button"
          aria-label="Delete saved route"
          :disabled="deletingId === saved.savedRouteId"
          @click="removeSaved(saved, $event)"
        >
          <Icon name="close" :size="15" />
        </button>
      </button>
    </div>

    <p v-else class="empty-state">
      No saved routes yet — tap "Save route" on any active route to keep it here.
    </p>
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

.saved-list {
  display: flex;
  flex-direction: column;
  gap: 12px;

  margin-top: 20px;
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

.saved-card {
  display: flex;
  align-items: center;
  gap: 13px;

  width: 100%;
  padding: 16px;
  text-align: left;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s ease;
}

.saved-card:hover {
  border-color: #cfe3da;
}

.saved-icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;

  width: 44px;
  height: 44px;

  background: var(--color-primary-soft);
  border-radius: var(--radius-sm);

  color: var(--color-primary);
}

.saved-body {
  flex: 1 1 auto;
  min-width: 0;
}

.saved-body.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.saved-body h2 {
  margin: 0;

  overflow: hidden;

  color: var(--color-text);
  font-size: 14.5px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.saved-meta {
  display: block;

  margin-top: 5px;

  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 600;
}

.delete-button {
  display: grid;
  flex: 0 0 auto;
  place-items: center;

  width: 34px;
  height: 34px;

  border-radius: var(--radius-sm);

  color: var(--color-text-faint);
}

.delete-button:hover {
  background: var(--color-surface-muted);
  color: var(--color-high);
}

@media (min-width: 768px) {
  .saved-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
