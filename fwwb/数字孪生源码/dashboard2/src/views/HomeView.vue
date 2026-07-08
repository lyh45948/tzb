<script setup lang="ts">
/**
 * 工厂数字孪生安全监测监控大屏 — 主布局壳
 * 基于 IofTV-Screen-Vue3 的 scale-screen 自适应外壳
 * 整合 dashboard1 的: 数据流启动(dashboardClient) + 9模块切换 + 连接小车对话框
 */
import { ref, computed, onMounted, onUnmounted } from "vue";
import ScaleScreen from "@/components/scale-screen";
import MessageContent from "@/components/Plugins/MessageContent";
import { useSettingStore } from "@/stores/index";
import { storeToRefs } from "pinia";
import { useDeviceStore } from "@/stores/deviceStore";
import { dashboardClient } from "@/services/dashboardClient";
import { dashboardModules } from "@/modules/dashboardModules";
import FactoryHeader from "./header.vue";
import Setting from "./setting.vue";
import CarConnectDialog from "@/components/dialogs/CarConnectDialog.vue";

// 9 模块 Section 组件 (保留 dashboard1 业务组合关系)
import OverviewSection from "@/components/sections/OverviewSection.vue";
import EnvironmentSection from "@/components/sections/EnvironmentSection.vue";
import GasSafetySection from "@/components/sections/GasSafetySection.vue";
import AgvSection from "@/components/sections/AgvSection.vue";
import GoodsSection from "@/components/sections/GoodsSection.vue";
import LightingSection from "@/components/sections/LightingSection.vue";
import ControlSection from "@/components/sections/ControlSection.vue";
import AlarmSection from "@/components/sections/AlarmSection.vue";
import AgentSection from "@/components/sections/AgentSection.vue";

const settingStore = useSettingStore();
const { isScale } = storeToRefs(settingStore);
const store = useDeviceStore();

// 当前激活模块 (默认总览大屏)
const activeModule = ref("overview");
// 连接小车对话框
const connectDialogOpen = ref(false);

// 模块 → Section 组件映射
const sectionMap: Record<string, any> = {
  overview: OverviewSection,
  environment: EnvironmentSection,
  gas: GasSafetySection,
  agv: AgvSection,
  goods: GoodsSection,
  lighting: LightingSection,
  control: ControlSection,
  alarm: AlarmSection,
  agent: AgentSection,
};
const activeSection = computed(() => sectionMap[activeModule.value] || OverviewSection);

// === 数据流启动: live(SSE) → polling → demo(模拟) 状态机 ===
onMounted(() => {
  // enableLiveData 为 true 时尝试真实后端, 失败自动降级到模拟
  dashboardClient.start(store).catch((e) => console.warn("[dashboard] 数据流启动失败, 使用模拟:", e));
});
onUnmounted(() => {
  dashboardClient.stop();
});
</script>

<template>
  <scale-screen
    width="1920"
    height="1080"
    :delay="500"
    :fullScreen="false"
    :boxStyle="{ background: '#03050C', overflow: isScale ? 'hidden' : 'auto' }"
    :autoScale="isScale"
  >
    <div class="content_wrap">
      <!-- 顶部标题栏 + 9模块切换Tab + 连接小车入口 -->
      <FactoryHeader
        v-model:active="activeModule"
        :modules="dashboardModules"
        @connect="connectDialogOpen = true"
      />
      <!-- 当前模块内容区 -->
      <div class="module-stage">
        <component :is="activeSection" />
      </div>
      <MessageContent />
    </div>
    <!-- 连接小车对话框 (Teleport to body) -->
    <CarConnectDialog v-if="connectDialogOpen" @close="connectDialogOpen = false" />
  </scale-screen>
  <Setting />
</template>

<style lang="scss" scoped>
.content_wrap {
  width: 100%;
  height: 100%;
  padding: 10px 14px 14px;
  box-sizing: border-box;
  background-image: url("@/assets/img/pageBg.png");
  background-size: cover;
  background-position: center center;
  display: flex;
  flex-direction: column;
}
.module-stage {
  flex: 1;
  min-height: 0;
  margin-top: 8px;
  overflow: hidden;
}
</style>
