<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>车间环境监测</div>
    <div class="panel-body env-body">
      <div class="env-item" v-for="item in items" :key="item.label">
        <div class="env-icon" :style="{ background: item.color }">
          {{ item.icon }}
        </div>
        <div class="env-info">
          <div class="env-label">{{ item.label }}</div>
          <div class="env-value" :style="{ color: item.color }">
            {{ item.value ?? '--' }}
            <span class="env-unit">{{ item.unit }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { formatNumber } from '../../utils/dataFormatter'
import { ALERT_LEVEL_MAP } from '../../utils/constants'

const store = useDeviceStore()

const avgBattery = computed(() => {
  if (!store.fleet.length) return '--'
  const avg = store.fleet.reduce((sum, r) => sum + (r.battery ?? 0), 0) / store.fleet.length
  return formatNumber(avg, 0)
})

const alertInfo = computed(() => ALERT_LEVEL_MAP[store.alertLevel] || ALERT_LEVEL_MAP.normal)

const items = computed(() => [
  { label: '温度', value: formatNumber(store.temperature), unit: '℃', color: '#ef4444', icon: '🌡' },
  { label: '湿度', value: formatNumber(store.humidity), unit: '%', color: '#2563eb', icon: '💧' },
  { label: '照度', value: formatNumber(store.lux, 0), unit: 'lux', color: '#f97316', icon: '💡' },
  { label: 'CO₂', value: formatNumber(store.co2, 0), unit: 'ppm', color: '#8b5cf6', icon: '☁' },
  { label: 'TVOC', value: formatNumber(store.tvoc, 0), unit: 'ppb', color: '#06b6d4', icon: '◆' },
  { label: '危气', value: store.gasStatus ? '泄漏' : '正常', unit: '', color: store.gasStatus ? '#ef4444' : '#22c55e', icon: '⚠' },
  { label: '火焰', value: store.flameStatus ? '触发' : '正常', unit: '', color: store.flameStatus ? '#ef4444' : '#22c55e', icon: '🔥' },
  { label: '平均电量', value: avgBattery.value, unit: '%', color: '#22c55e', icon: '⚡' },
  { label: '告警等级', value: alertInfo.value.label, unit: '', color: alertInfo.value.color, icon: '●' }
])
</script>

<style scoped>
.env-body { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.env-item { display: flex; align-items: center; gap: 6px; padding: 5px; background: rgba(0,0,0,0.04); border-radius: 4px; }
.env-icon { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; color: #fff; }
.env-info { flex: 1; min-width: 0; }
.env-label { font-size: 12px; color: var(--text-secondary); }
.env-value { font-size: 16px; font-weight: 700; }
.env-unit { font-size: 12px; font-weight: 400; color: var(--text-secondary); }
</style>
