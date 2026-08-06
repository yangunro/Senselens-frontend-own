<script setup>
import { useRouter } from "vue-router";
import PageShell from "../components/PageShell.vue";
import Icon from "../components/Icon.vue";

const router = useRouter();
</script>

<template>
  <PageShell>
    <div class="not-found">
      <div class="icon-badge">
        <Icon name="map" :size="26" />
      </div>

      <h1>This route doesn't exist</h1>
      <p>
        We couldn't find that page. Let's get you back to somewhere calm.
      </p>

      <button class="home-button" @click="router.push('/')">
        <Icon name="home" :size="16" />
        Back to Home
      </button>
    </div>
  </PageShell>
</template>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;

  padding: 60px 20px;

  text-align: center;
}

.icon-badge {
  display: grid;
  place-items: center;

  width: 64px;
  height: 64px;

  margin-bottom: 20px;

  background: var(--color-primary-soft);
  border-radius: var(--radius-lg);

  color: var(--color-primary);
}

.not-found h1 {
  margin: 0;

  color: var(--color-text);
  font-size: 20px;
  font-weight: 700;
}

.not-found p {
  max-width: 320px;
  margin: 10px 0 0;

  color: var(--color-text-muted);
  font-size: 13.5px;
  line-height: 1.55;
}

.home-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;

  margin-top: 26px;
  padding: 13px 22px;

  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);

  color: white;
  font-size: 13.5px;
  font-weight: 700;
}

.home-button:hover {
  background: var(--color-primary-dark);
}
</style>
