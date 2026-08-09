<script setup>
defineProps({
  options: { type: Array, required: true }, // [{ value, label }]
  modelValue: { type: String, required: true },
});
defineEmits(["update:modelValue"]);
</script>

<template>
  <div class="segmented-tabs" role="tablist">
    <button
      v-for="option in options"
      :key="option.value"
      class="tab"
      role="tab"
      :class="{ active: modelValue === option.value }"
      :aria-selected="modelValue === option.value"
      @click="$emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented-tabs {
  display: inline-flex;
  gap: 4px;

  padding: 4px;

  background: var(--color-surface-muted);
  border-radius: var(--radius-pill);
}

.tab {
  padding: 9px 16px;

  background: transparent;
  border: none;
  border-radius: var(--radius-pill);

  color: var(--color-text-muted);
  font-size: 12.5px;
  font-weight: 700;
  white-space: nowrap;
  transition: background 0.15s ease, color 0.15s ease;
}

.tab.active {
  background: var(--color-text);
  color: var(--color-surface);
}
</style>
