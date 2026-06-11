<template>
  <div class="section-page goods-section">
    <div class="goods-main"><GoodsCountPanel /></div>
    <div class="goods-scene"><CarScene /></div>
    <div class="goods-fleet"><CarStatusPanel /></div>
    <div class="goods-chart"><HistoryChart /></div>
  </div>
</template>

<script setup>
import GoodsCountPanel from '../panels/GoodsCountPanel.vue'
import CarScene from '../three/CarScene.vue'
import CarStatusPanel from '../panels/CarStatusPanel.vue'
import HistoryChart from '../charts/HistoryChart.vue'
</script>

<style scoped>
.goods-section {
  display: grid;
  grid-template-columns: minmax(260px, 0.8fr) minmax(0, 1.45fr) minmax(260px, 0.85fr);
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--gap);
  padding: var(--gap);
}

.goods-main,
.goods-chart,
.goods-fleet,
.goods-scene {
  min-width: 0;
  min-height: 0;
}

.goods-main { grid-row: 1 / 3; grid-column: 1; }
.goods-scene { grid-row: 1 / 3; grid-column: 2; }
.goods-fleet { grid-row: 1; grid-column: 3; }
.goods-chart { grid-row: 2; grid-column: 3; }
</style>
