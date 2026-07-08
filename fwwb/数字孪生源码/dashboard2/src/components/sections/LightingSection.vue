<template>
  <!-- 智能照明大屏: IofTV 风格 三栏 (智能照明 + 照度仪表 + 环境监测) -->
  <div class="section-page lighting-section">
    <div class="light-grid">
      <ItemWrap title="智能照明">
        <SmartLightPanel />
      </ItemWrap>
      <ItemWrap title="实时照度">
        <LuxGauge />
      </ItemWrap>
      <ItemWrap title="环境监测">
        <EnvironmentPanel />
      </ItemWrap>
    </div>
  </div>
</template>

<script setup>
import ItemWrap from '@/components/item-wrap/item-wrap.vue'
import SmartLightPanel from '../panels/SmartLightPanel.vue'
import LuxGauge from '../charts/LuxGauge.vue'
import EnvironmentPanel from '../panels/EnvironmentPanel.vue'
</script>

<style scoped>
.section-page {
  width: 100%;
  height: 100%;
}
.lighting-section {
  display: flex;
}
.light-grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
}
.light-grid > * {
  min-width: 0;
  min-height: 0;
}
</style>
