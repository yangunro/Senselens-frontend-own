<script setup>
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";

// Every claim on this page describes something the app actually does right
// now, not a roadmap item — checked directly against the backend before
// writing it. Nothing here about construction/development data influencing
// scores, for example, because that data exists in the database but isn't
// actually factored into the sensory score yet.
const factors = [
  {
    icon: "users",
    title: "Live crowd level",
    body: "Pedestrian sensor counts near the route's actual walking path are compared against every other currently-reporting sensor, giving a percentile — not a guess.",
  },
  {
    icon: "trendingUp",
    title: "Historical time patterns",
    body: "A model trained on the City of Melbourne's historical pedestrian data estimates whether the next 1–3 hours are likely to be busier or quieter than usual for that spot.",
  },
  {
    icon: "map",
    title: "Sensor coverage",
    body: "Melbourne's sensor network doesn't all report at once — typically 15–20 of the 134 sensors are live at any given time. A route with no sensor nearby is marked \"insufficient data\" rather than a made-up score.",
  },
  {
    icon: "refuge",
    title: "Nearby refuges",
    body: "Real parks, libraries and cafés from the City of Melbourne's open data are matched against your actual route path, not just \"somewhere in the CBD.\"",
  },
];

const levels = [
  { key: "low", label: "LOW SENSORY", body: "Lower measured or predicted crowd exposure along this route." },
  { key: "medium", label: "MEDIUM SENSORY", body: "Some sections with moderate pedestrian activity." },
  { key: "high", label: "HIGH SENSORY", body: "Higher measured or predicted crowd exposure — an alternative may be calmer." },
];
</script>

<template>
  <PageShell>
    <header class="page-header">
      <h1>How SenseLens works</h1>
      <p>What the sensory score is actually based on, and where it comes from.</p>
    </header>

    <section class="factor-list">
      <div v-for="factor in factors" :key="factor.title" class="factor-card">
        <div class="factor-icon">
          <Icon :name="factor.icon" :size="19" />
        </div>
        <div>
          <h2>{{ factor.title }}</h2>
          <p>{{ factor.body }}</p>
        </div>
      </div>
    </section>

    <section class="levels-card">
      <h2>Understanding the sensory labels</h2>
      <p class="levels-intro">The labels support comparing routes. They are not a diagnosis, a guarantee, or medical advice.</p>

      <div v-for="level in levels" :key="level.key" class="level-row">
        <span class="sensory-badge" :class="`level-${level.key}`">{{ level.label }}</span>
        <p>{{ level.body }}</p>
      </div>
    </section>

    <section class="disclaimer-card">
      <Icon name="alert" :size="18" />
      <p>
        SenseLens gives general route guidance based on public City of Melbourne data. It is not medical,
        safety or emergency advice, and doesn't account for construction, events or road closures that
        aren't already in that public data.
      </p>
    </section>
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

.factor-list {
  display: flex;
  flex-direction: column;
  gap: 12px;

  margin-top: 20px;
}

.factor-card {
  display: flex;
  gap: 13px;

  padding: 16px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.factor-icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;

  width: 40px;
  height: 40px;

  background: var(--color-primary-soft);
  border-radius: var(--radius-sm);

  color: var(--color-primary);
}

.factor-card h2 {
  margin: 0;

  color: var(--color-text);
  font-size: 14.5px;
  font-weight: 700;
}

.factor-card p {
  margin: 6px 0 0;

  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.55;
}

.levels-card {
  margin-top: 18px;
  padding: 18px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.levels-card h2 {
  margin: 0;

  color: var(--color-text);
  font-size: 15px;
  font-weight: 700;
}

.levels-intro {
  margin: 6px 0 16px;

  color: var(--color-text-muted);
  font-size: 12.5px;
  line-height: 1.5;
}

.level-row {
  display: flex;
  align-items: baseline;
  gap: 12px;

  padding: 10px 0;
}

.level-row + .level-row {
  border-top: 1px solid var(--color-border);
}

.level-row p {
  margin: 0;

  color: var(--color-text-muted);
  font-size: 12.5px;
  line-height: 1.5;
}

.sensory-badge {
  flex: 0 0 auto;

  padding: 4px 11px;

  border-radius: var(--radius-pill);

  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
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

.disclaimer-card {
  display: flex;
  gap: 11px;

  margin-top: 18px;
  padding: 16px;

  background: var(--color-alert-bg);
  border: 1px solid var(--color-alert-border);
  border-radius: var(--radius-md);

  color: #6b4d16;
}

.disclaimer-card p {
  margin: 0;

  font-size: 12.5px;
  line-height: 1.55;
}

@media (min-width: 768px) {
  .factor-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
