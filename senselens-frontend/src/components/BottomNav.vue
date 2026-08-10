<script setup>
import Icon from "./Icon.vue";

// Settings is intentionally not linked here — page still exists at
// /settings, just not reachable from navigation.
const navItems = [
  { to: "/", label: "Home", icon: "home" },
  { to: "/map", label: "Map", icon: "map" },
  { to: "/refuges", label: "Refuges", icon: "refuge" },
  { to: "/saved-routes", label: "Saved", icon: "bookmark" },
  { to: "/how-it-works", label: "How it works", icon: "info" },
];
</script>

<template>
  <nav class="bottom-nav">
    <router-link
      v-for="item in navItems"
      :key="item.to"
      :to="item.to"
      class="nav-item"
      active-class="active"
      exact-active-class="active"
    >
      <span class="nav-icon">
        <Icon :name="item.icon" :size="21" />
      </span>
      <span class="nav-label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.bottom-nav {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;

  display: grid;
  grid-template-columns: repeat(5, 1fr);

  height: 80px;
  padding: 10px 14px 14px;

  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  gap: 5px;

  padding: 6px 4px;
  border-radius: var(--radius-sm);

  background: transparent;
  border: none;

  color: var(--color-text-faint);
  font-size: 11px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.15s ease;
}

.nav-icon {
  display: grid;
  place-items: center;

  width: 34px;
  height: 34px;

  border-radius: var(--radius-pill);

  transition: background 0.15s ease, color 0.15s ease;
}

.nav-item.active {
  color: var(--color-primary-dark);
}

.nav-item.active .nav-icon {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

/* 电脑端：底部导航变成顶部导航 */
@media (min-width: 1024px) {
  .bottom-nav {
    position: absolute;
    top: 0;
    right: 0;
    bottom: auto;
    left: auto;

    display: flex;
    align-items: center;
    gap: 6px;

    width: auto;
    height: 78px;
    padding: 0 40px;

    background: transparent;
    border-top: none;
  }

  .nav-item {
    flex-direction: row;
    gap: 8px;

    padding: 8px 14px;

    font-size: 13px;
  }

  .nav-icon {
    width: 28px;
    height: 28px;
  }
}
</style>
