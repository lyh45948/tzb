<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>红外与智能照明</div>
    <div class="panel-body">
      <div class="light-row">
        <span class="label">控制模式</span>
        <span class="value">{{ smartLight.modeName || (smartLight.mode === 1 ? '自动' : '手动') }}</span>
      </div>
      <div class="light-row">
        <span class="label">当前亮度</span>
        <span class="value text-yellow">{{ smartLight.brightness ?? 0 }}%</span>
      </div>
      <div class="light-bar">
        <div class="light-fill" :style="{ width: (smartLight.brightness || 0) + '%' }"></div>
      </div>
      <div class="light-row">
        <span class="label">目标亮度</span>
        <span class="value text-cyan">{{ smartLight.targetBrightness ?? 0 }}%</span>
      </div>
      <div class="light-row">
        <span class="label">时段策略</span>
        <span class="value text-blue">{{ smartLight.timePeriodName || '--' }}</span>
      </div>
      <div class="light-row">
        <span class="label">光照等级</span>
        <span class="value">{{ lightLevelName }}</span>
      </div>
      <div class="light-row">
        <span class="label">人体红外</span>
        <span class="value" :class="store.humanDetected ? 'text-green' : 'text-dim'">{{ store.humanDetected ? '有人' : '无人' }}</span>
      </div>
      <div class="light-row">
        <span class="label">PS / IR</span>
        <span class="value text-dim">{{ Math.round(store.ps || 0) }} / {{ store.ir ? '触发' : '未触发' }}</span>
      </div>
      <div class="light-row">
        <span class="label">LED照明</span>
        <span class="value" :class="store.led ? 'text-green' : 'text-red'">{{ store.led ? '开启' : '关闭' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'

const store = useDeviceStore()
const smartLight = computed(() => store.smartLight || {})

const lightLevelName = computed(() => {
  if (smartLight.value.lightLevelName) return smartLight.value.lightLevelName
  const level = smartLight.value.lightLevel ?? 0
  const names = ['黑暗', '昏暗', '偏暗', '正常', '明亮', '强光']
  return names[level] || '未知'
})
</script>

<style scoped>
.panel-body { display: flex; flex-direction: column; gap: 6px; }
.light-row { display: flex; justify-content: space-between; gap: 8px; }
.label { color: var(--text-secondary); font-size: 14px; }
.value { font-size: 15px; font-weight: 600; text-align: right; }
.text-dim { color: #94a3b8; }
.light-bar { height: 6px; background: rgba(0,0,0,0.06); border-radius: 3px; overflow: hidden; }
.light-fill { height: 100%; background: linear-gradient(90deg, #f59e0b, #f97316); border-radius: 3px; transition: width 0.3s; }
</style>
