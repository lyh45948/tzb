<template>
  <div class="section-page overview-section">
    <main class="overview-main">
      <section class="overview-left">
        <HistoryChart />
      </section>

      <section class="overview-center">
        <CarScene />
      </section>
    </main>

    <footer class="overview-footer">
      <SafetyPanel />
      <ControlPanel />
      <SmartLightPanel />
      <GoodsCountPanel />
      <EnvironmentPanel />
    </footer>
  </div>
</template>

<script setup>
import CarScene from '../three/CarScene.vue'
import SafetyPanel from '../panels/SafetyPanel.vue'
import ControlPanel from '../panels/ControlPanel.vue'
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
import SmartLightPanel from '../panels/SmartLightPanel.vue'
import GoodsCountPanel from '../panels/GoodsCountPanel.vue'
import HistoryChart from '../charts/HistoryChart.vue'
</script>

<style scoped>
.overview-section {
  display: flex;
  flex-direction: column;
  gap: var(--gap);
  padding: var(--gap);
}

.overview-main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 50% 50%;
  gap: var(--gap);
}

.overview-left {
  min-width: 0;
  min-height: 0;
}

.overview-center {
  min-width: 0;
  min-height: 0;
}

.overview-footer {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--gap);
}
</style>
