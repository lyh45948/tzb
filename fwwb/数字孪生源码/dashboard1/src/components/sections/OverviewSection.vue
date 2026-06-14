<template>
  <div class="section-page overview-section">
    <main class="overview-main">
      <section class="overview-side">
        <CarStatusPanel />
        <SpeedChart />
      </section>

      <section class="overview-center">
        <CarScene />
      </section>

      <section class="overview-side">
        <BatteryGauge />
        <ControlPanel />
      </section>
    </main>

    <footer class="overview-footer">
      <EnvironmentPanel />
      <SafetyPanel />
      <SmartLightPanel />
      <GoodsCountPanel />
      <HistoryChart />
    </footer>
  </div>
</template>

<script setup>
import CarScene from '../three/CarScene.vue'
import CarStatusPanel from '../panels/CarStatusPanel.vue'
import SpeedChart from '../charts/SpeedChart.vue'
import BatteryGauge from '../charts/BatteryGauge.vue'
import ControlPanel from '../panels/ControlPanel.vue'
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
import SafetyPanel from '../panels/SafetyPanel.vue'
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
  grid-template-columns: minmax(230px, 23%) minmax(360px, 1fr) minmax(230px, 23%);
  gap: var(--gap);
}

.overview-side {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 3fr) minmax(0, 4fr);
  gap: var(--gap);
}

.overview-center {
  min-width: 0;
  min-height: 0;
}

.overview-footer {
  height: var(--footer-height);
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--gap);
}
</style>
