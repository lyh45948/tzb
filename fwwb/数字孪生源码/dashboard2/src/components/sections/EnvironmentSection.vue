<template>
  <!-- 环境监测大屏: IofTV 风格左右两栏布局 -->
  <div class="section-page environment-section">
    <div class="env-grid">
      <!-- 左栏: 环境指标 + 风机控制 -->
      <div class="col col-left">
        <ItemWrap title="环境监测">
          <EnvironmentPanel />
        </ItemWrap>
        <ItemWrap title="风机控制">
          <FanControlPanel />
        </ItemWrap>
      </div>

      <!-- 右栏: 温湿度趋势 + 视频监控 -->
      <div class="col col-right">
        <ItemWrap title="温湿度趋势">
          <TempHumiChart />
        </ItemWrap>
        <ItemWrap title="视频监控">
          <CameraMonitorPanel />
        </ItemWrap>
      </div>
    </div>
  </div>
</template>

<script setup>
import ItemWrap from '@/components/item-wrap/item-wrap.vue'
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
import TempHumiChart from '../charts/TempHumiChart.vue'
import FanControlPanel from '../panels/FanControlPanel.vue'
import CameraMonitorPanel from '../panels/CameraMonitorPanel.vue'
</script>

<style scoped>
.section-page {
  width: 100%;
  height: 100%;
}
.environment-section {
  display: flex;
}
.env-grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
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
