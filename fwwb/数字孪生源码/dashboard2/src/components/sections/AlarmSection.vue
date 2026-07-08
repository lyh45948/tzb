<template>
  <!-- 告警中心大屏: IofTV 风格 左安全/车队 + 右趋势/环境 -->
  <div class="section-page alarm-section">
    <div class="alarm-grid">
      <!-- 左栏: 安全监测 + 车队状态 -->
      <div class="col col-left">
        <ItemWrap title="安全告警监测">
          <SafetyPanel />
        </ItemWrap>
        <ItemWrap title="车队状态">
          <CarStatusPanel />
        </ItemWrap>
      </div>

      <!-- 右栏: 告警趋势 + 环境数据 -->
      <div class="col col-right">
        <ItemWrap title="告警数据趋势">
          <HistoryChart />
        </ItemWrap>
        <ItemWrap title="环境监测">
          <EnvironmentPanel />
        </ItemWrap>
      </div>
    </div>
  </div>
</template>

<script setup>
import ItemWrap from '@/components/item-wrap/item-wrap.vue'
import SafetyPanel from '../panels/SafetyPanel.vue'
import HistoryChart from '../charts/HistoryChart.vue'
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
import CarStatusPanel from '../panels/CarStatusPanel.vue'
</script>

<style scoped>
.section-page {
  width: 100%;
  height: 100%;
}
.alarm-section {
  display: flex;
}
.alarm-grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
  gap: 12px;
  min-height: 0;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.col > * {
  flex: 1;
  min-height: 0;
}
</style>
