<script setup>
import PageShell from "../components/PageShell.vue";
</script>

<template>
  <PageShell>
    <header class="page-header">
      <h1>Your sensory preferences</h1>
    </header>

    <div class="coming-soon">Coming soon</div>
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

.coming-soon {
  display: flex;
  align-items: center;
  justify-content: center;

  margin-top: 26px;
  padding: 70px 20px;

  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);

  color: var(--color-text-faint);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}
</style>
