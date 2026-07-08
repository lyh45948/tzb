import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from "vue-router"

// 工厂数字孪生大屏: 单页应用, HomeView 内部用 9 模块切换 (非路由)
const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]
const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to, from, next) => {
  next();
})

export default router
