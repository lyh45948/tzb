<template>
  <div class="section-page lighting-section">
    <SmartLightPanel />
    <LuxGauge />
    <EnvironmentPanel />
  </div>
</template>

<script setup>
import SmartLightPanel from '../panels/SmartLightPanel.vue'
import LuxGauge from '../charts/LuxGauge.vue'
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
</script>

<style scoped>
.lighting-section {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(320px, 1fr) minmax(300px, 0.95fr);
  grid-template-rows: minmax(0, 1fr);
  gap: var(--gap);
  padding: var(--gap);
}
</style>
