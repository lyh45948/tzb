<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>联动控制状态</div>
    <div class="panel-body">
      <div class="link-row">
        <span class="label">告警等级</span>
        <span class="value" :class="alertLevelClass">{{ alertLevelText }}</span>
      </div>
      <div class="link-row">
        <span class="label">联动原因</span>
        <span class="value text-dim small">{{ linkedActionReason || '系统运行正常，无联动动作' }}</span>
      </div>

      <div class="divider"></div>

      <div class="link-row">
        <span class="label">PIR 人体红外</span>
        <span class="value" :class="store.humanDetected ? 'text-green' : 'text-dim'">
          {{ store.humanDetected ? '有人' : '无人' }}
        </span>
      </div>
      <div class="link-row sub">
        <span class="label">PS / IR</span>
        <span class="value text-dim">{{ Math.round(store.ps || 0) }} / {{ Math.round(store.ir || 0) }}</span>
      </div>
      <div class="link-row">
        <span class="label">LED 自动照明</span>
        <span class="value" :class="ledOn ? 'text-green' : 'text-red'">
          {{ ledOn ? '开启' : '关闭' }}
          <span v-if="ledOverride > 0" class="badge">手动覆盖 {{ ledOverride }}s</span>
        </span>
      </div>

      <div class="divider"></div>

      <div class="link-row">
        <span class="label">温度 / 湿度</span>
        <span class="value text-cyan">
          {{ store.temperature?.toFixed?.(1) ?? store.temperature ?? '--' }}°C /
          {{ store.humidity?.toFixed?.(1) ?? store.humidity ?? '--' }}%
        </span>
      </div>
      <div class="link-row">
        <span class="label">风扇自动启停</span>
        <span class="value" :class="fanOn ? 'text-green' : 'text-red'">
          {{ fanOn ? '开启' : '关闭' }}
          <span v-if="fanOverride > 0" class="badge">手动覆盖 {{ fanOverride }}s</span>
        </span>
      </div>

      <div class="divider"></div>

      <div class="link-row">
        <span class="label">RGB 危气告警</span>
        <span class="value">
          <span class="rgb-swatch" :style="{ background: rgbHex }"></span>
          <span class="text-dim small">{{ rgbDescription }}</span>
          <span v-if="rgbOverride > 0" class="badge">手动覆盖 {{ rgbOverride }}s</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'

const store = useDeviceStore()

const linkage = computed(() => store.linkage || {})
const linkedActionReason = computed(() => store.linkedActionReason)

const alertLevelText = computed(() => {
  return {
    critical: '严重',
    danger: '危险',
    warning: '警告',
    normal: '正常'
  }[store.alertLevel] || '正常'
})

const alertLevelClass = computed(() => ({
  'text-red': store.alertLevel === 'critical' || store.alertLevel === 'danger',
  'text-yellow': store.alertLevel === 'warning',
  'text-green': !store.alertLevel || store.alertLevel === 'normal'
}))

const ledOn = computed(() => {
  const v = linkage.value.led
  return v == null ? !!store.led : !!v
})
const fanOn = computed(() => {
  const v = linkage.value.fan
  return v == null ? !!store.fan : !!v
})

const rgb = computed(() => linkage.value.rgb || { r: 0, g: 0, b: 0 })
const rgbHex = computed(() => `rgb(${rgb.value.r || 0}, ${rgb.value.g || 0}, ${rgb.value.b || 0})`)
const rgbDescription = computed(() => {
  const { r = 0, g = 0, b = 0 } = rgb.value
  if (r === 0 && g === 0 && b === 0) return '熄灭（正常）'
  if (r === 255 && g === 255 && b === 0) return '黄色（warning）'
  if (r === 255 && g === 0 && b === 0) return '红色（danger / critical 闪烁）'
  return `R${r} G${g} B${b}`
})

const overrides = computed(() => linkage.value.manualOverrideRemaining || {})
const fanOverride = computed(() => overrides.value.fan || 0)
const ledOverride = computed(() => overrides.value.led || 0)
const rgbOverride = computed(() => overrides.value.rgb || 0)
</script>

<style scoped>
.panel-body { display: flex; flex-direction: column; gap: 6px; }
.link-row { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.link-row.sub { font-size: 13px; opacity: 0.85; }
.label { color: var(--text-secondary); font-size: 14px; }
.value { font-size: 15px; font-weight: 600; text-align: right; display: inline-flex; align-items: center; gap: 6px; }
.value.small, .small { font-size: 13px; font-weight: 500; }
.text-dim { color: #94a3b8; }
.text-red { color: #ef4444; }
.text-yellow { color: #f59e0b; }
.text-green { color: #10b981; }
.text-cyan { color: #06b6d4; }
.divider { height: 1px; background: rgba(148, 163, 184, 0.25); margin: 4px 0; }
.rgb-swatch {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(148, 163, 184, 0.4);
}
.badge {
  display: inline-block;
  padding: 1px 6px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(245, 158, 11, 0.18);
  color: #f59e0b;
  border-radius: 3px;
}
</style>
