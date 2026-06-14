<template>
  <div class="section-page focus-section gas-section">
    <div class="section-grid gas-grid">
      <div class="grid-card safety"><SafetyPanel /></div>
      <div class="grid-card"><CO2Chart /></div>
      <div class="grid-card"><TVOCChart /></div>
      <div class="grid-card history"><HistoryChart /></div>
      <div class="grid-card"><WindSpeedChart /></div>
    </div>
  </div>
</template>

<script setup>
import SafetyPanel from '../panels/SafetyPanel.vue'
import CO2Chart from '../charts/CO2Chart.vue'
import TVOCChart from '../charts/TVOCChart.vue'
import WindSpeedChart from '../charts/WindSpeedChart.vue'
import HistoryChart from '../charts/HistoryChart.vue'
</script>

<style scoped>
.gas-section { padding: var(--gap); }
.gas-grid {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) repeat(2, minmax(260px, 1fr));
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--gap);
}
.safety { grid-row: span 2; }
</style>
