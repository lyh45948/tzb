<template>
  <div class="dashboard">
    <HeaderBar />

    <div class="dashboard-body">
      <SidebarNav
        v-model:active="activeModule"
        v-model:collapsed="sidebarCollapsed"
      />

      <div class="dashboard-content">
        <div class="module-focus" :style="{ borderColor: activeMeta.color }">
          <span class="focus-icon">{{ activeMeta.icon }}</span>
          <span class="focus-title">{{ activeMeta.label }}</span>
          <span class="focus-desc">{{ activeMeta.desc }}</span>
        </div>

        <component :is="activeSectionComponent" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { dashboardModuleMap } from '../../modules/dashboardModules'

import HeaderBar from './HeaderBar.vue'
import SidebarNav from './SidebarNav.vue'
import OverviewSection from '../sections/OverviewSection.vue'
import EnvironmentSection from '../sections/EnvironmentSection.vue'
import GasSafetySection from '../sections/GasSafetySection.vue'
import AgvSection from '../sections/AgvSection.vue'
import GoodsSection from '../sections/GoodsSection.vue'
import LightingSection from '../sections/LightingSection.vue'
import ControlSection from '../sections/ControlSection.vue'
import AlarmSection from '../sections/AlarmSection.vue'

const store = useDeviceStore()
const activeModule = ref('overview')
const sidebarCollapsed = ref(false)

const sectionComponents = {
  overview: OverviewSection,
  environment: EnvironmentSection,
  gas: GasSafetySection,
  agv: AgvSection,
  goods: GoodsSection,
  lighting: LightingSection,
  control: ControlSection,
  alarm: AlarmSection
}

const activeMeta = computed(() => dashboardModuleMap[activeModule.value] || dashboardModuleMap.overview)
const activeSectionComponent = computed(() => sectionComponents[activeModule.value] || OverviewSection)

onMounted(() => {
  store.startSimulation()
})

onUnmounted(() => {
  store.stopSimulation()
})
</script>

<style scoped>
.dashboard {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dashboard-body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.dashboard-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.module-focus {
  height: 32px;
  margin: var(--gap) var(--gap) 0;
  padding: 0 12px;
  border-left: 4px solid var(--accent-blue);
  border-radius: var(--border-radius);
  background: rgba(255,255,255,0.72);
  box-shadow: var(--shadow-panel);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.focus-icon { font-size: 15px; }
.focus-title { color: var(--text-primary); font-weight: 800; white-space: nowrap; }
.focus-desc { color: var(--text-secondary); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
