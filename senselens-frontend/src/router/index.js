import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || { top: 0 };
  },
  routes: [
    // Lazy-loaded per route so the heavy Mapbox GL bundle (only used by
    // Map.vue) doesn't get downloaded and parsed before the app is even
    // interactive on pages that don't need a map.
    {
      path: "/",
      name: "home",
      component: () => import("../pages/Home.vue"),
      meta: { title: "SenseLens - Calm routes through the city" },
    },
    {
      path: "/routes",
      name: "routes",
      component: () => import("../pages/Routes.vue"),
      meta: { title: "Choose a route - SenseLens" },
    },
    {
      path: "/map",
      name: "map",
      component: () => import("../pages/Map.vue"),
      meta: { title: "On the way - SenseLens" },
    },
    {
      path: "/refuges",
      name: "refuges",
      component: () => import("../pages/Refuges.vue"),
      meta: { title: "Sensory refuges - SenseLens" },
    },
    {
      path: "/how-it-works",
      name: "how-it-works",
      component: () => import("../pages/HowItWorks.vue"),
      meta: { title: "How it works - SenseLens" },
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("../pages/Setting.vue"),
      meta: { title: "Preferences - SenseLens" },
    },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: () => import("../pages/NotFound.vue"),
      meta: { title: "Page not found - SenseLens" },
    },
  ],
});

router.afterEach((to) => {
  document.title = to.meta.title ?? "SenseLens";
});

export default router;
