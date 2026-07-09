/**
 * 数字孪生数据初始化 composable（引用计数单例）
 *
 * 9 个 Section 各自挂载/卸载，但数据流（SSE / polling / demo）只需启动一次。
 * 此 composable 保证：
 *   - 第一个进入 factory 子路由的组件启动数据流
 *   - 所有 factory 子路由卸载后才停止数据流（300ms 防抖避免路由切换闪烁）
 *
 * 用法：在 factory_xxx/index.vue 的 setup 中调用 useFactoryInit()
 */
import { onUnmounted } from 'vue'
import { useDeviceStore } from '../stores/deviceStore'
import { dashboardClient } from '../services/dashboardClient'
import config from '../config'

let initCount = 0
let stopTimer = null

export function useFactoryInit() {
  const store = useDeviceStore()

  // 首次挂载：启动数据流
  if (initCount === 0) {
    if (config.enableLiveData && config.apiBaseUrl) {
      dashboardClient.start(store)
    } else {
      store.connectionStatus = 'demo'
      try {
        store.startSimulation?.()
      } catch (e) {
        console.warn('[useFactoryInit] 启动模拟失败:', e)
      }
    }
  }
  initCount++

  onUnmounted(() => {
    initCount--
    // 所有 factory 页面已卸载：延迟停止数据流，防止路由快速切换时重复启停
    if (initCount <= 0) {
      initCount = 0
      if (stopTimer) clearTimeout(stopTimer)
      stopTimer = setTimeout(() => {
        if (initCount <= 0) {
          if (config.enableLiveData && config.apiBaseUrl) {
            dashboardClient.stop()
          } else {
            try { store.stopSimulation?.() } catch (_) { /* noop */ }
          }
        }
      }, 300)
    }
  })

  return store
}
