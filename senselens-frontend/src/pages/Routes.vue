<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import { getRouteOptions } from "../services/routes";

const route = useRoute();
const router = useRouter();

const destination = computed(() => route.query.destination || "Collins Street");

const routeOptions = ref([]);
const selectedId = ref(null);
const loading = ref(true);

async function loadRoutes() {
  loading.value = true;
  routeOptions.value = await getRouteOptions(destination.value);
  const recommended = routeOptions.value.find((r) => r.recommended);
  selectedId.value = recommended?.id ?? routeOptions.value[0]?.id ?? null;
  loading.value = false;
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
        <h1>Southern Cross Station to {{ destination }}</h1>
        <p>Choose a route that matches your comfort level</p>
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

        <div v-if="option.factors?.length" class="factor-chips">
          <span v-for="factor in option.factors" :key="factor.label" class="factor-chip">
            <Icon :name="factor.icon" :size="12" />
            {{ factor.label }}
          </span>
        </div>

        <div class="route-card-bottom">
          <span class="duration">
            <Icon name="clock" :size="14" />
            {{ option.duration }}
          </span>
          <span v-if="option.transit" class="transit-tag">
            <Icon name="train" :size="13" />
            {{ option.transit.walk }} to {{ option.transit.stop }}
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

.factor-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;

  margin-top: 11px;
}

.factor-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;

  padding: 5px 10px;

  background: var(--color-surface-muted);
  border-radius: var(--radius-pill);

  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 600;
}

.route-card-bottom {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 14px;

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

.transit-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;

  color: var(--color-primary);
  font-size: 12px;
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
