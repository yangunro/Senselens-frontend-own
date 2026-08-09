import { createRouter, createWebHistory } from "vue-router";
import Home from "../pages/Home.vue";
import Routes from "../pages/Routes.vue";
import Map from "../pages/Map.vue";
import Refuges from "../pages/Refuges.vue";
import Setting from "../pages/Setting.vue";
import NotFound from "../pages/NotFound.vue";

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || { top: 0 };
  },
  routes: [
    { path: "/", name: "home", component: Home, meta: { title: "SenseLens — Calm routes through the city" } },
    { path: "/routes", name: "routes", component: Routes, meta: { title: "Choose a route — SenseLens" } },
    { path: "/map", name: "map", component: Map, meta: { title: "On the way — SenseLens" } },
    { path: "/refuges", name: "refuges", component: Refuges, meta: { title: "Sensory refuges — SenseLens" } },
    { path: "/settings", name: "settings", component: Setting, meta: { title: "Preferences — SenseLens" } },
    { path: "/:pathMatch(.*)*", name: "not-found", component: NotFound, meta: { title: "Page not found — SenseLens" } },
  ],
});

router.afterEach((to) => {
  document.title = to.meta.title ?? "SenseLens";
});

export default router;
