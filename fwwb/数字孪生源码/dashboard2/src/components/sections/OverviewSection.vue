<template>
  <!-- 总览大屏: IofTV 风格三栏布局 (左指标 + 中3D场景 + 右趋势 + 底状态) -->
  <div class="section-page overview-section">
    <div class="overview-grid">
      <!-- 左栏: 安全/控制/货物核心指标 -->
      <div class="col col-left">
        <ItemWrap title="安全监测">
          <SafetyPanel />
        </ItemWrap>
        <ItemWrap title="货物计数">
          <GoodsCountPanel />
        </ItemWrap>
        <ItemWrap title="智能照明">
          <SmartLightPanel />
        </ItemWrap>
      </div>

      <!-- 中栏: 3D 数字孪生场景 (主角) -->
      <div class="col col-center">
        <ItemWrap title="数字孪生工厂实景">
          <div class="scene-host">
            <CarScene />
          </div>
        </ItemWrap>
      </div>

      <!-- 右栏: 环境趋势 + 设备控制 -->
      <div class="col col-right">
        <ItemWrap title="安全数据趋势">
          <HistoryChart />
        </ItemWrap>
        <ItemWrap title="设备控制">
          <ControlPanel />
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
  width: 100%;
  height: 100%;
  display: flex;
}
.overview-grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(0, 1.8fr) minmax(360px, 1fr);
  gap: 12px;
  min-height: 0;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
/* 左右栏内 ItemWrap 按高度自适应分配 */
.col-left > *,
.col-right > * {
  flex: 1;
  min-height: 0;
}
/* 中栏 3D 场景占满 */
.col-center > * {
  flex: 1;
  min-height: 0;
}
.scene-host {
  width: 100%;
  height: 100%;
}
</style>
