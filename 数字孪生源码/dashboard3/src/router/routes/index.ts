import type { CustomRoute, ElegantConstRoute, ElegantRoute } from '@elegant-router/types';
import { generatedRoutes } from '../elegant/routes';
import { layouts, views } from '../elegant/imports';
import { transformElegantRoutesToVueRoutes } from '../elegant/transform';

/**
 * custom routes
 *
 * @link https://github.com/soybeanjs/elegant-router?tab=readme-ov-file#custom-route
 */
const customRoutes: CustomRoute[] = [
  {
    name: 'factory',
    path: '/factory',
    component: 'layout.base',
    meta: {
      title: 'factory',
      i18nKey: 'route.factory',
      icon: 'mdi:factory',
      order: 1,
      constant: true
    },
    children: [
      { name: 'factory_overview', path: '/factory/overview', component: 'view.factory_overview', meta: { title: '总览', i18nKey: 'route.factory_overview', icon: 'mdi:view-dashboard', order: 1 } },
      { name: 'factory_environment', path: '/factory/environment', component: 'view.factory_environment', meta: { title: '环境监测', i18nKey: 'route.factory_environment', icon: 'mdi:thermometer', order: 2 } },
      { name: 'factory_gas', path: '/factory/gas', component: 'view.factory_gas', meta: { title: '危气安全', i18nKey: 'route.factory_gas', icon: 'mdi:alert-circle', order: 3 } },
      { name: 'factory_agv', path: '/factory/agv', component: 'view.factory_agv', meta: { title: 'AGV调度', i18nKey: 'route.factory_agv', icon: 'mdi:robot', order: 4 } },
      { name: 'factory_goods', path: '/factory/goods', component: 'view.factory_goods', meta: { title: '货物计数', i18nKey: 'route.factory_goods', icon: 'mdi:package-variant-closed', order: 5 } },
      { name: 'factory_lighting', path: '/factory/lighting', component: 'view.factory_lighting', meta: { title: '智能照明', i18nKey: 'route.factory_lighting', icon: 'mdi:lightbulb', order: 6 } },
      { name: 'factory_control', path: '/factory/control', component: 'view.factory_control', meta: { title: '设备控制', i18nKey: 'route.factory_control', icon: 'mdi:gauge', order: 7 } },
      { name: 'factory_alarm', path: '/factory/alarm', component: 'view.factory_alarm', meta: { title: '告警中心', i18nKey: 'route.factory_alarm', icon: 'mdi:bell-ring', order: 8 } },
      { name: 'factory_agent', path: '/factory/agent', component: 'view.factory_agent', meta: { title: '智能体', i18nKey: 'route.factory_agent', icon: 'mdi:robot-outline', order: 9 } },
    ]
  }
];

/** create routes when the auth route mode is static */
export function createStaticRoutes() {
  const constantRoutes: ElegantRoute[] = [];

  const authRoutes: ElegantRoute[] = [];

  // customRoutes 在后以覆盖 generatedRoutes 的同名项（让手写 meta 如 constant 生效）
  // 使用 Map 按 name 去重，customRoutes 的同名项覆盖 generatedRoutes
  const merged = new Map<string, ElegantConstRoute>()
  ;[...generatedRoutes, ...customRoutes].forEach(item => {
    merged.set(item.name, item)
  })
  const dedupedRoutes = Array.from(merged.values())
  dedupedRoutes.forEach(item => {
    if (item.meta?.constant) {
      constantRoutes.push(item as ElegantRoute);
    } else {
      authRoutes.push(item as ElegantRoute);
    }
  });

  return {
    constantRoutes,
    authRoutes
  };
}

/**
 * Get auth vue routes
 *
 * @param routes Elegant routes
 */
export function getAuthVueRoutes(routes: ElegantConstRoute[]) {
  return transformElegantRoutesToVueRoutes(routes, layouts, views);
}
