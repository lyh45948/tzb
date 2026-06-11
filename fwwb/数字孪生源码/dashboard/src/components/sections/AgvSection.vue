<template>
  <div class="section-page agv-section">
    <div class="agv-scene"><CarScene /></div>
    <div class="agv-side">
      <CarStatusPanel />
      <ControlPanel />
    </div>
    <div class="agv-bottom">
      <SpeedChart />
      <BatteryGauge />
      <DistanceGauge />
    </div>
  </div>
</template>

<script setup>
import CarScene from '../three/CarScene.vue'
import CarStatusPanel from '../panels/CarStatusPanel.vue'
import ControlPanel from '../panels/ControlPanel.vue'
import SpeedChart from '../charts/SpeedChart.vue'
import BatteryGauge from '../charts/BatteryGauge.vue'
import DistanceGauge from '../charts/DistanceGauge.vue'
</script>

<style scoped>
.agv-section {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 28%);
  grid-template-rows: minmax(0, 1fr) minmax(190px, 30%);
  gap: var(--gap);
  padding: var(--gap);
}

.agv-scene,
.agv-side,
.agv-bottom {
  min-width: 0;
  min-height: 0;
}

.agv-side {
  display: grid;
  grid-template-rows: minmax(0, 1fr) minmax(0, 1.2fr);
  gap: var(--gap);
}

.agv-bottom {
  grid-column: span 2;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--gap);
}
</style>
