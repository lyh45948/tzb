<template>
  <div class="section-page control-section">
    <div class="notice-card">
      <strong>本地演示控制</strong>
      <span>当前页面只修改 Pinia 模拟状态，不连接后端、不下发 UDP/TCP 控制命令。</span>
    </div>
    <div class="control-main"><ControlPanel /></div>
    <div class="control-scene"><CarScene /></div>
    <div class="control-status"><CarStatusPanel /></div>
    <div class="control-battery"><BatteryGauge /></div>
  </div>
</template>

<script setup>
import ControlPanel from '../panels/ControlPanel.vue'
import CarScene from '../three/CarScene.vue'
import CarStatusPanel from '../panels/CarStatusPanel.vue'
import BatteryGauge from '../charts/BatteryGauge.vue'
</script>

<style scoped>
.control-section {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.5fr) minmax(260px, 0.8fr);
  grid-template-rows: 38px minmax(0, 1fr) minmax(0, 0.9fr);
  gap: var(--gap);
  padding: var(--gap);
}

.notice-card {
  grid-column: span 3;
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: var(--border-radius);
  background: rgba(245, 158, 11, 0.08);
  color: #92400e;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  font-size: 13px;
}

.control-main { grid-row: span 2; }
.control-scene { grid-row: span 2; }
.control-main,
.control-scene,
.control-status,
.control-battery {
  min-width: 0;
  min-height: 0;
}
</style>
