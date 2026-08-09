<script setup>
import BottomNav from "./BottomNav.vue";
</script>

<template>
  <main class="page-shell">
    <section class="app-container">
      <div class="page-content">
        <slot />
      </div>

      <BottomNav />
    </section>
  </main>
</template>
