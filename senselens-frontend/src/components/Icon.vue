<script setup>
const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 20 },
});

const paths = {
  home: '<path d="M4 11.5 12 4l8 7.5"/><path d="M6 10v9a1 1 0 0 0 1 1h4v-5h2v5h4a1 1 0 0 0 1-1v-9"/>',
  map: '<path d="M12 21s7-6.5 7-11.5A7 7 0 0 0 5 9.5C5 14.5 12 21 12 21Z"/><circle cx="12" cy="9.5" r="2.3"/>',
  refuge: '<path d="M12 3l7 3v5c0 5-3.2 8.4-7 10-3.8-1.6-7-5-7-10V6l7-3Z"/>',
  settings: '<line x1="4" y1="7" x2="20" y2="7"/><circle cx="9" cy="7" r="2"/><line x1="4" y1="12" x2="20" y2="12"/><circle cx="15" cy="12" r="2"/><line x1="4" y1="17" x2="20" y2="17"/><circle cx="11" cy="17" r="2"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><line x1="15.3" y1="15.3" x2="20" y2="20"/>',
  heart: '<path d="M12 20s-7-4.35-9.5-8.5C.7 8 2.3 4.5 6 4.5c2 0 3.5 1.2 4 2.6.5-1.4 2-2.6 4-2.6 3.7 0 5.3 3.5 3.5 7C19 15.65 12 20 12 20Z"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  chevronLeft: '<path d="M14.5 5 8 12l6.5 7"/>',
  alert: '<path d="M12 4 21 19H3L12 4Z"/><line x1="12" y1="10" x2="12" y2="14.5"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>',
  check: '<path d="M4.5 12.5 9.5 17.5 19.5 6.5"/>',
  leaf: '<path d="M5 19c8 0 14-6 14-14-8 0-14 6-14 14Z"/><path d="M5 19c3-3 5-6 6-10"/>',
  sun: '<circle cx="12" cy="12" r="4"/><line x1="12" y1="2.5" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="21.5"/><line x1="2.5" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="21.5" y2="12"/><line x1="5.3" y1="5.3" x2="7" y2="7"/><line x1="17" y1="17" x2="18.7" y2="18.7"/><line x1="5.3" y1="18.7" x2="7" y2="17"/><line x1="17" y1="7" x2="18.7" y2="5.3"/>',
  book: '<path d="M4 5.5C4 4.7 4.7 4 5.5 4H12v16H5.5A1.5 1.5 0 0 1 4 18.5v-13Z"/><path d="M20 5.5c0-.8-.7-1.5-1.5-1.5H12v16h6.5c.8 0 1.5-.7 1.5-1.5v-13Z"/>',
  tree: '<circle cx="12" cy="9" r="5.5"/><line x1="12" y1="14.5" x2="12" y2="20"/>',
  user: '<circle cx="12" cy="8.5" r="3.5"/><path d="M4.5 20c1-4 4-6 7.5-6s6.5 2 7.5 6"/>',
  refresh: '<path d="M4 12a8 8 0 0 1 13.5-5.8"/><path d="M17 4v3.5h-3.5"/><path d="M20 12a8 8 0 0 1-13.5 5.8"/><path d="M7 20v-3.5h3.5"/>',
  tent: '<path d="M12 4 4 20h16L12 4Z"/><line x1="9" y1="20" x2="12" y2="12"/><line x1="15" y1="20" x2="12" y2="12"/>',
  users: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9.5" r="2.3"/><path d="M15.3 14.2c2.6.5 4.7 2.7 4.7 5.8"/>',
  tool: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2-2 2.6-2.6Z"/>',
  megaphone: '<path d="M3 10v4a1 1 0 0 0 1 1h2l7 4V5L6 9H4a1 1 0 0 0-1 1Z"/><path d="M16.5 9a4 4 0 0 1 0 6"/><path d="M19 6.5a8 8 0 0 1 0 11"/>',
  train: '<rect x="5" y="4" width="14" height="12" rx="3"/><line x1="5" y1="11" x2="19" y2="11"/><circle cx="9" cy="19" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="19" r="1" fill="currentColor" stroke="none"/>',
  trendingUp: '<path d="M3 17 9 11 13 15 21 6"/><path d="M15 6h6v6"/>',
  coffee: '<path d="M5 9h11v6a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4V9Z"/><path d="M16 10.5h1.5a2.5 2.5 0 0 1 0 5H16"/><line x1="8" y1="4" x2="8" y2="6.5"/><line x1="11" y1="4" x2="11" y2="6.5"/>',
  navigation: '<path d="M12 2 4.5 19.5 12 15.5 19.5 19.5 12 2Z"/>',
  info: '<circle cx="12" cy="12" r="9"/><line x1="12" y1="11" x2="12" y2="16.5"/><circle cx="12" cy="7.5" r="0.6" fill="currentColor" stroke="none"/>',
};
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="sl-icon"
    aria-hidden="true"
  >
    <g v-html="paths[name] ?? ''"></g>
  </svg>
</template>

<style scoped>
.sl-icon {
  display: block;
  flex-shrink: 0;
}
</style>
