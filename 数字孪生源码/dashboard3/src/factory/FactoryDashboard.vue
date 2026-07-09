<template>
  <!--
    数字孪生 factory 总入口
    —— 把 9 个 Section 组装起来，用顶部 Tab 切换，并启动前端模拟数据流。
     迁移自旧 dashboard3：原工程 9 个 Section 无组装入口、数据流从未启动，
     本组件补全这两个缺口。
  -->
  <div class="factory-dashboard">
    <header class="factory-header">
      <h1 class="factory-title">智慧工厂安全监测 · 数字孪生</h1>
      <div class="factory-status">
        <span class="status-dot" :class="statusDotClass"></span>
        <span class="status-text">{{ statusLabel }}</span>
      </div>
    </header>

    <nav class="factory-tabs">
      <button
        v-for="m in modules"
        :key="m.key"
        class="factory-tab"
        :class="{ active: activeKey === m.key }"
        :style="{ '--tab-color': m.color }"
        @click="activeKey = m.key"
      >
        <span class="tab-icon">{{ m.icon }}</span>
        <span class="tab-label">{{ m.label }}</span>
        <span v-if="m.badge" class="tab-badge">{{ m.badge }}</span>
      </button>

      <!-- 连接小车按钮（右上角，tab 栏同一行） -->
      <button class="connect-car-btn" @click="dialogOpen = true" title="输入小车 IP 连接">
        + 连接小车
      </button>
    </nav>

    <main class="factory-body">
      <component :is="activeSection" v-if="activeSection" />
    </main>
  </div>

  <CarConnectDialog v-if="dialogOpen" @close="dialogOpen = false" />
</template>

<script setup>
import { ref, computed, shallowRef, onMounted, onUnmounted, watch } from 'vue'
import { useDeviceStore } from './stores/deviceStore'
import { dashboardModules } from './modules/dashboardModules'
import { dashboardClient } from './services/dashboardClient'
import config from './config'
import CarConnectDialog from './components/dialogs/CarConnectDialog.vue'

// 9 个 Section 组件（懒加载引用，避免一开始全量初始化）
const sectionMap = {
  overview: () => import('./components/sections/OverviewSection.vue'),
  environment: () => import('./components/sections/EnvironmentSection.vue'),
  gas: () => import('./components/sections/GasSafetySection.vue'),
  agv: () => import('./components/sections/AgvSection.vue'),
  goods: () => import('./components/sections/GoodsSection.vue'),
  lighting: () => import('./components/sections/LightingSection.vue'),
  control: () => import('./components/sections/ControlSection.vue'),
  alarm: () => import('./components/sections/AlarmSection.vue'),
  agent: () => import('./components/sections/AgentSection.vue')
}

const modules = dashboardModules
const store = useDeviceStore()
const dialogOpen = ref(false)

const activeKey = ref('overview')
const activeSection = shallowRef(null)

// 连接状态驱动右上角指示器
const connStyle = computed(() => {
  const status = store.connectionStatus || 'idle'
  switch (status) {
    case 'live':
      return { cls: 'live', label: '实时' }
    case 'polling':
      return { cls: 'polling', label: '轮询' }
    case 'demo':
      return { cls: 'demo', label: '演示模式' }
    case 'disconnected':
      return { cls: 'offline', label: '离线' }
    default:
      return { cls: 'idle', label: '连接中…' }
  }
})

const statusDotClass = computed(() => connStyle.value.cls)
const statusLabel = computed(() => connStyle.value.label)

// 切换 Section：异步加载组件后挂载
async function loadSection(key) {
  const loader = sectionMap[key]
  if (!loader) return
  try {
    const mod = await loader()
    activeSection.value = mod.default
  } catch (e) {
    console.warn(`[factory] 加载 Section "${key}" 失败:`, e)
    activeSection.value = null
  }
}

watch(activeKey, loadSection, { immediate: true })

// 数据流启动：根据配置选择后端接入或本地模拟
onMounted(() => {
  if (config.enableLiveData && config.apiBaseUrl) {
    // 真实接入：REST 引导 + SSE 推送；失败时自动降级到 polling/demo
    dashboardClient.start(store)
  } else {
    // 强制本地模拟（VITE_ENABLE_LIVE_DATA=false 或未配置 apiBaseUrl）
    store.connectionStatus = 'demo'
    try {
      store.startSimulation && store.startSimulation()
    } catch (e) {
      console.warn('[factory] 启动模拟失败:', e)
    }
  }
})

onUnmounted(() => {
  if (config.enableLiveData && config.apiBaseUrl) {
    dashboardClient.stop()
  } else {
    try {
      store.stopSimulation && store.stopSimulation()
    } catch (_) {
      /* noop */
    }
  }
})
</script>

<style scoped>
.factory-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: var(--gap);
  padding: var(--gap);
  background: #f8fafc;
}

.factory-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 4px 4px 0;
}

.factory-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.factory-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}
.status-dot.live {
  background: var(--accent-green);
  box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.5);
  animation: pulse 2s infinite;
}
.status-dot.polling {
  background: var(--accent-yellow);
  box-shadow: 0 0 6px var(--accent-yellow);
}
.status-dot.demo {
  background: var(--accent-blue);
  box-shadow: 0 0 6px var(--accent-blue);
}
.status-dot.offline {
  background: var(--accent-red);
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.5); }
  70% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
  100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
}

.factory-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
  padding: 0 4px;
  align-items: center;
}

.factory-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--border-dim);
  border-radius: var(--radius);
  background: var(--bg-panel);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}
.factory-tab:hover {
  border-color: var(--tab-color, var(--accent-blue));
  color: var(--text-primary);
}
.factory-tab.active {
  border-color: var(--tab-color, var(--accent-blue));
  color: var(--tab-color, var(--accent-blue));
  background: color-mix(in srgb, var(--tab-color, var(--accent-blue)) 8%, var(--bg-panel));
  font-weight: 600;
}

.tab-icon {
  font-size: 16px;
  line-height: 1;
}

.tab-badge {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--accent-red);
  color: #fff;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.connect-car-btn {
  margin-left: auto;
  padding: 6px 14px;
  border: 1px solid var(--accent-blue);
  background: rgba(30, 80, 180, 0.06);
  color: var(--accent-blue);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
}
.connect-car-btn:hover {
  background: var(--accent-blue);
  color: #fff;
}

.factory-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
</style>
