<template>
  <!-- 设备控制大屏: IofTV 风格 左控制 + 中3D场景 + 右状态/电量 -->
  <div class="section-page control-section">
    <div class="control-grid">
      <!-- 左栏: 设备控制 -->
      <div class="col col-left">
        <ItemWrap title="设备控制">
          <ControlPanel />
        </ItemWrap>
      </div>

      <!-- 中栏: 3D 场景 -->
      <div class="col col-center">
        <ItemWrap title="数字孪生控制实景">
          <div class="scene-host">
            <CarScene />
          </div>
        </ItemWrap>
      </div>

      <!-- 右栏: 车队状态 + 电量仪表 -->
      <div class="col col-right">
        <ItemWrap title="车辆状态">
          <CarStatusPanel />
        </ItemWrap>
        <ItemWrap title="电量监测">
          <BatteryGauge />
        </ItemWrap>
      </div>
    </div>
  </div>
</template>

<script setup>
import ItemWrap from '@/components/item-wrap/item-wrap.vue'
import ControlPanel from '../panels/ControlPanel.vue'
import CarScene from '../three/CarScene.vue'
import CarStatusPanel from '../panels/CarStatusPanel.vue'
import BatteryGauge from '../charts/BatteryGauge.vue'
</script>

<style scoped>
.section-page {
  width: 100%;
  height: 100%;
}
.control-section {
  display: flex;
}
.control-grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(300px, 0.9fr) minmax(0, 1.6fr) minmax(280px, 0.8fr);
  gap: 12px;
  min-height: 0;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.col-left > *,
.col-center > *,
.col-right > * {
  flex: 1;
  min-height: 0;
}
.scene-host {
  width: 100%;
  height: 100%;
}
</style>
