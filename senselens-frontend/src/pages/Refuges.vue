<script setup>
import { ref, computed, onMounted } from "vue";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";
import SkeletonBlock from "../components/SkeletonBlock.vue";
import SegmentedTabs from "../components/SegmentedTabs.vue";
import { getRefuges } from "../services/refuges";

const refuges = ref([]);
const loading = ref(true);
const filter = ref("all");

const filterOptions = [
  { value: "all", label: "All" },
  { value: "Cafe", label: "Cafes" },
  { value: "Library", label: "Libraries" },
  { value: "Park", label: "Parks" },
];

const filteredRefuges = computed(() =>
  filter.value === "all" ? refuges.value : refuges.value.filter((r) => r.type === filter.value)
);

onMounted(async () => {
  refuges.value = await getRefuges();
  loading.value = false;
});
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
      <article v-for="refuge in filteredRefuges" :key="refuge.id" class="refuge-card">
        <div class="refuge-icon">
          <Icon :name="refuge.icon" :size="20" />
        </div>

        <div class="refuge-body">
          <div class="refuge-top">
            <h2>{{ refuge.name }}</h2>
            <span v-if="refuge.distance" class="distance">{{ refuge.distance }}</span>
          </div>

          <span class="refuge-type">{{ refuge.type }}</span>
          <p v-if="refuge.note">{{ refuge.note }}</p>
        </div>
      </article>
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
  gap: 13px;

  padding: 16px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s ease;
}

.refuge-card:hover {
  border-color: #cfe3da;
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

  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
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
