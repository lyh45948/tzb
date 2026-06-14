<template>
  <header class="header-bar">
    <div class="header-left">
      <h1 class="header-title">智慧工厂安全数字孪生平台</h1>
    </div>
    <div class="header-center">
      <StatusIndicator :connected="store.isOnline" />
      <span class="fleet-count">
        <span class="fleet-dot"></span>
        在线设备: {{ store.fleet.length }}
      </span>
      <span class="alert-pill" :style="{ borderColor: alertInfo.color, color: alertInfo.color }">
        最高告警: {{ alertInfo.label }}
      </span>
    </div>
    <div class="header-right">
      <span class="header-time">{{ currentTime }}</span>
      <button class="connect-car-btn" @click="dialogOpen = true" title="输入小车 IP 连接">
        连接小车
      </button>
      <span class="conn-badge" :class="`conn-${connStyle.cls}`" :title="connStyle.title">
        <span class="conn-dot"></span>{{ connStyle.label }}
      </span>
    </div>
  </header>
  <CarConnectDialog v-if="dialogOpen" @close="dialogOpen = false" />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { ALERT_LEVEL_MAP } from '../../utils/constants'
import StatusIndicator from '../common/StatusIndicator.vue'
import CarConnectDialog from '../dialogs/CarConnectDialog.vue'

const store = useDeviceStore()
const currentTime = ref('')
const dialogOpen = ref(false)
let timer = null

const alertInfo = computed(() => {
  return ALERT_LEVEL_MAP[store.highestAlert || store.alertLevel || 'normal'] || ALERT_LEVEL_MAP.normal
})

const connStyle = computed(() => {
  const status = store.connectionStatus || 'idle'
  switch (status) {
    case 'live':
      return { cls: 'live', label: '实时', title: 'SSE 实时推送中' }
    case 'polling':
      return { cls: 'polling', label: '轮询', title: 'SSE 中断，REST 轮询中' }
    case 'demo':
      return { cls: 'demo', label: '演示模式', title: '后端不可用，本地模拟' }
    case 'disconnected':
      return { cls: 'offline', label: '离线', title: '与后端连接已断开' }
    default:
      return { cls: 'idle', label: '连接中', title: '尚未建立连接' }
  }
})

function updateTime() {
  const now = new Date()
  currentTime.value = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')} ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.header-bar {
  height: var(--header-height);
  background: linear-gradient(180deg, rgba(30,80,180,0.08) 0%, transparent 100%);
  border-bottom: 1px solid var(--border-dim);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.header-title {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(90deg, #1d4ed8, #2563eb);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}
.header-center {
  display: flex;
  align-items: center;
  gap: 16px;
}
.fleet-count {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--text-secondary);
}
.fleet-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-blue);
  box-shadow: 0 0 6px var(--accent-blue);
}
.alert-pill {
  padding: 3px 10px;
  border: 1px solid currentColor;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.65);
  font-size: 13px;
  font-weight: 700;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.header-time {
  color: var(--text-secondary);
  font-size: 16px;
  font-family: 'Consolas', monospace;
}
.demo-badge {
  padding: 3px 10px;
  background: rgba(30,80,180,0.1);
  border: 1px solid var(--accent-blue);
  color: var(--accent-blue);
  border-radius: 3px;
  font-size: 13px;
}
.connect-car-btn {
  padding: 4px 12px;
  border: 1px solid var(--accent-blue, #2563eb);
  background: rgba(30,80,180,0.08);
  color: var(--accent-blue, #2563eb);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.connect-car-btn:hover {
  background: var(--accent-blue, #2563eb);
  color: #fff;
}
.conn-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid currentColor;
  font-size: 13px;
  font-weight: 700;
}
.conn-badge .conn-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 6px currentColor;
}
.conn-badge.conn-live { color: #16a34a; }
.conn-badge.conn-polling { color: #d97706; }
.conn-badge.conn-demo { color: #2563eb; }
.conn-badge.conn-offline { color: #dc2626; }
.conn-badge.conn-idle { color: var(--text-secondary); }
.conn-badge.conn-live .conn-dot {
  animation: conn-pulse 1.6s infinite;
}
@keyframes conn-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
