<template>
  <div class="section-page focus-section environment-section">
    <div class="section-grid two-one">
      <div class="grid-card tall"><EnvironmentPanel /></div>
      <div class="grid-card"><TempHumiChart /></div>
      <div class="grid-card"><LuxGauge /></div>
      <div class="grid-card wide"><HistoryChart /></div>
      <div class="grid-card"><CO2Chart /></div>
      <div class="grid-card"><TVOCChart /></div>
    </div>
  </div>
</template>

<script setup>
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
import TempHumiChart from '../charts/TempHumiChart.vue'
import LuxGauge from '../charts/LuxGauge.vue'
import HistoryChart from '../charts/HistoryChart.vue'
import CO2Chart from '../charts/CO2Chart.vue'
import TVOCChart from '../charts/TVOCChart.vue'
</script>

<style scoped>
.environment-section { padding: var(--gap); }
.section-grid {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(240px, 0.85fr) minmax(260px, 1fr) minmax(260px, 1fr) minmax(240px, 0.9fr);
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--gap);
}
.tall { grid-row: span 2; }
.wide { grid-column: span 2; }
</style>
