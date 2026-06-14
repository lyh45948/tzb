<template>
  <div class="section-page lighting-section">
    <SmartLightPanel />
    <LuxGauge />
    <EnvironmentPanel />
    <HistoryChart />
  </div>
</template>

<script setup>
import SmartLightPanel from '../panels/SmartLightPanel.vue'
import LuxGauge from '../charts/LuxGauge.vue'
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
import HistoryChart from '../charts/HistoryChart.vue'
</script>

<style scoped>
.lighting-section {
  display: grid;
  grid-template-columns: minmax(260px, 0.8fr) minmax(320px, 1fr) minmax(280px, 0.9fr);
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--gap);
  padding: var(--gap);
}

.lighting-section > :first-child { grid-row: span 2; }
.lighting-section > :last-child { grid-column: span 2; }
</style>
