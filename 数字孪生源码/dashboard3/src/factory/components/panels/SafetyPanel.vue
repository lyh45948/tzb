<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>危气与告警</div>
    <div class="panel-body">
      <div class="safety-summary">
        <div class="safety-row">
          <span class="label">CO浓度</span>
          <span class="value" :style="{ color: coColor }">{{ Math.round(store.co) }} ppm</span>
        </div>
        <div class="safety-row">
          <span class="label">TVOC</span>
          <span class="value" :style="{ color: tvocColor }">{{ Math.round(store.tvoc) }} ppb</span>
        </div>
        <div class="safety-row">
          <span class="label">气体浓度</span>
          <span class="value" :style="{ color: gasMicColor }">{{ Math.round(store.gasMic) }}</span>
        </div>
        <div class="safety-row">
          <span class="label">可燃气体</span>
          <span class="value" :class="store.gasStatus ? 'text-red' : 'text-green'">{{ store.gasStatus ? '异常' : '正常' }}</span>
        </div>
        <div class="safety-row">
          <span class="label">火焰检测</span>
          <span class="value" :class="store.flameStatus ? 'text-red' : 'text-green'">{{ store.flameStatus ? '触发' : '正常' }}</span>
        </div>
        <div class="safety-row">
          <span class="label">联动设备</span>
          <span class="value text-cyan">风扇{{ store.fan ? '开启' : '关闭' }} / 蜂鸣器{{ store.buzzer ? '开启' : '关闭' }}</span>
        </div>
        <div class="linked-reason">
          {{ store.linkedActionReason }}
        </div>
      </div>
      <div class="alarm-events">
        <div class="alarm-events-title">最近告警</div>
        <div v-if="events.length" class="alarm-event-list">
          <div v-for="e in events" :key="e.id" class="alarm-event-item">
            <span class="evt-time">{{ formatTime(e.timestamp) }}</span>
            <span class="evt-level" :style="{ color: levelColor(e.level) }">{{ levelLabel(e.level) }}</span>
            <span class="evt-message" :title="e.message">{{ e.message }}</span>
          </div>
        </div>
        <div v-else class="alarm-empty">暂无安全告警</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { ALERT_LEVEL_MAP } from '../../utils/constants'

const store = useDeviceStore()
// 仅展示与危气安全相关的告警(火焰/可燃气体/CO),
// 障碍物/温度等非危气类型不在本面板展示
const GAS_ALARM_TYPES = new Set(['flame', 'gas', 'co2'])
const events = computed(() => store.alarmEvents.filter(e => GAS_ALARM_TYPES.has(e.type)))

const coColor = computed(() => {
  if (store.co >= 50) return '#ef4444'
  if (store.co >= 35) return '#f59e0b'
  return '#22c55e'
})

const tvocColor = computed(() => {
  if (store.tvoc >= 900) return '#ef4444'
  if (store.tvoc >= 600) return '#f59e0b'
  return '#22c55e'
})

const gasMicColor = computed(() => {
  if (store.gasMic >= 500) return '#ef4444'
  if (store.gasMic >= 300) return '#f59e0b'
  return '#22c55e'
})

function levelLabel(level) {
  return ALERT_LEVEL_MAP[level]?.label || level
}

function levelColor(level) {
  return ALERT_LEVEL_MAP[level]?.color || '#94a3b8'
}

function formatTime(ts) {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
</script>

<style scoped>
.panel-body { display: flex; flex-direction: column; gap: 6px; height: 100%; overflow: hidden; }
.safety-summary { display: flex; flex-direction: column; gap: 4px; }
.safety-row { display: flex; justify-content: space-between; padding: 2px 0; gap: 8px; }
.label { color: var(--text-secondary); font-size: 14px; }
.value { font-size: 15px; font-weight: 600; text-align: right; }
.linked-reason { padding: 4px 6px; border-radius: 4px; background: rgba(245, 158, 11, 0.08); color: #92400e; font-size: 12px; line-height: 1.35; }
.alarm-events { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.alarm-events-title { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; border-top: 1px solid rgba(0,0,0,0.06); padding-top: 4px; }
.alarm-event-list { overflow-y: auto; flex: 1; min-height: 0; }
.alarm-event-item { display: grid; grid-template-columns: 48px 38px 1fr; gap: 6px; padding: 2px 0; font-size: 12px; align-items: center; }
.evt-time { color: var(--text-secondary); }
.evt-level { font-weight: 700; }
.evt-message { color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.alarm-empty { color: var(--text-secondary); font-size: 13px; text-align: center; padding: 8px 0; }
</style>
