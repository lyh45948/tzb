<template>
  <div class="section-page focus-section environment-section">
    <div class="section-grid two-one">
      <div class="grid-card"><EnvironmentPanel /></div>
      <div class="grid-card"><TempHumiChart /></div>
      <div class="grid-card"><FanControlPanel /></div>
      <div class="grid-card camera-wide"><CameraMonitorPanel /></div>
    </div>
  </div>
</template>

<script setup>
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
import TempHumiChart from '../charts/TempHumiChart.vue'
import FanControlPanel from '../panels/FanControlPanel.vue'
import CameraMonitorPanel from '../panels/CameraMonitorPanel.vue'
</script>

<style scoped>
.environment-section { padding: var(--gap); }
.section-grid {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(320px, 1.05fr) minmax(300px, 0.95fr);
  grid-template-rows: minmax(0, 0.95fr) minmax(0, 1.05fr);
  gap: var(--gap);
}
.camera-wide { grid-column: 1 / -1; }
</style>
