<template>
  <div class="section-page alarm-section">
    <div class="alarm-safety"><SafetyPanel /></div>
    <div class="alarm-history"><HistoryChart /></div>
    <div class="alarm-env"><EnvironmentPanel /></div>
    <div class="alarm-fleet"><CarStatusPanel /></div>
  </div>
</template>

<script setup>
import SafetyPanel from '../panels/SafetyPanel.vue'
import HistoryChart from '../charts/HistoryChart.vue'
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
import CarStatusPanel from '../panels/CarStatusPanel.vue'
</script>

<style scoped>
.alarm-section {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.4fr) minmax(280px, 0.9fr);
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--gap);
  padding: var(--gap);
}

.alarm-safety { grid-row: span 2; }
.alarm-history { grid-column: span 2; }
.alarm-safety,
.alarm-history,
.alarm-env,
.alarm-fleet {
  min-width: 0;
  min-height: 0;
}
</style>
