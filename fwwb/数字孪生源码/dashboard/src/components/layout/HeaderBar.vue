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
      <span class="demo-badge">演示模式</span>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { ALERT_LEVEL_MAP } from '../../utils/constants'
import StatusIndicator from '../common/StatusIndicator.vue'

const store = useDeviceStore()
const currentTime = ref('')
let timer = null

const alertInfo = computed(() => {
  return ALERT_LEVEL_MAP[store.highestAlert || store.alertLevel || 'normal'] || ALERT_LEVEL_MAP.normal
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
</style>
