<script setup>
import { watchEffect } from "vue";
import { usePreferences, toggleValue } from "./composables/usePreferences";

const preferences = usePreferences();

watchEffect(() => {
  document.documentElement.dataset.contrast = toggleValue(preferences, "contrast", false);
});
</script>

<template>
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>