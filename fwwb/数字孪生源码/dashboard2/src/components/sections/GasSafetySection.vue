<template>
  <!-- 危气安全大屏: IofTV 风格 左侧安全指标 + 右侧 2x2 趋势图表 -->
  <div class="section-page gas-section">
    <div class="gas-grid">
      <!-- 左栏: 安全指标 (满高) -->
      <div class="col col-left">
        <ItemWrap title="危气安全监测">
          <SafetyPanel />
        </ItemWrap>
      </div>

      <!-- 右栏: 四个图表 2x2 -->
      <div class="charts-2x2">
        <ItemWrap title="CO₂ 浓度">
          <CO2Chart />
        </ItemWrap>
        <ItemWrap title="TVOC 浓度">
          <TVOCChart />
        </ItemWrap>
        <ItemWrap title="风速监测">
          <WindSpeedChart />
        </ItemWrap>
        <ItemWrap title="安全数据趋势">
          <HistoryChart />
        </ItemWrap>
      </div>
    </div>
  </div>
</template>

<script setup>
import ItemWrap from '@/components/item-wrap/item-wrap.vue'
import SafetyPanel from '../panels/SafetyPanel.vue'
import CO2Chart from '../charts/CO2Chart.vue'
import TVOCChart from '../charts/TVOCChart.vue'
import WindSpeedChart from '../charts/WindSpeedChart.vue'
import HistoryChart from '../charts/HistoryChart.vue'
</script>

<style scoped>
.section-page {
  width: 100%;
  height: 100%;
}
.gas-section {
  display: flex;
}
.gas-grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(300px, 0.9fr) minmax(0, 1.6fr);
  gap: 12px;
  min-height: 0;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.col-left > * {
  flex: 1;
  min-height: 0;
}
.charts-2x2 {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
}
.charts-2x2 > * {
  min-width: 0;
  min-height: 0;
}
</style>
