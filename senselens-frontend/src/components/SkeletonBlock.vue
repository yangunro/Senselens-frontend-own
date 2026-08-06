<script setup>
defineProps({
  width: { type: String, default: "100%" },
  height: { type: String, default: "14px" },
  radius: { type: String, default: "" },
});
</script>

<template>
  <span
    class="skeleton"
    :style="{ width, height, borderRadius: radius || undefined }"
  ></span>
</template>

<style scoped>
.skeleton {
  display: block;
}
</style>
