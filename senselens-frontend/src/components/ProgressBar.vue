<script setup>
const props = defineProps({
  value: { type: Number, required: true }, // 0–100
  color: { type: String, default: "var(--color-primary)" },
  trackColor: { type: String, default: "var(--color-border)" },
});
</script>

<template>
  <div class="progress-track" :style="{ background: trackColor }">
    <div
      class="progress-fill"
      :style="{ width: `${Math.min(100, Math.max(0, value))}%`, background: color }"
    ></div>
  </div>
</template>

<style scoped>
.progress-track {
  overflow: hidden;

  width: 100%;
  height: 6px;

  border-radius: var(--radius-pill);
}

.progress-fill {
  height: 100%;
  border-radius: var(--radius-pill);
  transition: width 0.3s ease;
}
</style>
