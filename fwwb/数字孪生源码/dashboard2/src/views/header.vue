<script setup lang="ts">
/**
 * 数字孪生大屏 — 顶部标题栏
 * 整合: 主标题 + 实时时钟 + 9模块切换Tab + 在线设备/告警状态 + 连接小车按钮 + 设置
 * 视觉基于 IofTV 深色科技风格
 */
import { reactive, computed } from "vue";
import dayjs from "dayjs";
import type { DateDataType } from "./index.d";
import { useSettingStore } from "@/stores/index";
import { useDeviceStore } from "@/stores/deviceStore";

const props = defineProps<{
  active: string;
  modules: Array<{ key: string; label: string; icon?: string; color?: string; badge?: string }>;
}>();
const emit = defineEmits<{
  (e: "update:active", key: string): void;
  (e: "connect"): void;
}>();

const { setSettingShow } = useSettingStore();
const store = useDeviceStore();

const dateData = reactive<DateDataType>({
  dateDay: "",
  dateYear: "",
  dateWeek: "",
  timing: null as any,
});
const weekday = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
const timeFn = () => {
  dateData.timing = setInterval(() => {
    dateData.dateDay = dayjs().format("YYYY-MM-DD HH:mm:ss");
    dateData.dateWeek = weekday[dayjs().day()];
  }, 1000);
};
timeFn();

// 在线设备数 + 最高告警等级
const onlineCount = computed(() => store.fleet?.filter((r: any) => r.status !== "offline").length ?? 0);
const totalCount = computed(() => store.fleet?.length ?? 0);
const highestAlert = computed(() => store.highestAlert || "normal");
const alertLabel = computed(() => {
  const m: Record<string, string> = { normal: "正常", watch: "关注", warning: "预警", danger: "危险", critical: "紧急" };
  return m[highestAlert.value] || "正常";
});

const switchModule = (key: string) => emit("update:active", key);
</script>

<template>
  <div class="title_wrap">
    <div class="zuojuxing"></div>
    <div class="youjuxing"></div>
    <div class="guang"></div>

    <!-- 左侧: 在线设备 + 告警状态 -->
    <div class="header-left">
      <div class="status-pill">
        <span class="dot online"></span>
        <span class="label">在线设备</span>
        <span class="num">{{ onlineCount }}/{{ totalCount }}</span>
      </div>
      <div class="status-pill" :class="highestAlert">
        <span class="dot"></span>
        <span class="label">告警</span>
        <span class="num">{{ alertLabel }}</span>
      </div>
    </div>

    <!-- 中央主标题 -->
    <div class="title-center">
      <div class="title">
        <span class="title-text">工厂数字孪生安全监测监控平台</span>
      </div>
    </div>

    <!-- 右侧: 时钟 + 连接小车 + 设置 -->
    <div class="header-right">
      <button class="btn-connect" @click="emit('connect')">
        <span class="btn-dot" :class="{ on: store.connectionStatus === 'live' }"></span>
        连接小车
      </button>
      <div class="timers">
        <div class="time-line">{{ dateData.dateDay }}</div>
        <div class="time-sub">{{ dateData.dateWeek }}</div>
      </div>
      <div class="setting_icon" @click="setSettingShow(true)">
        <img src="@/assets/img/headers/setting.png" alt="设置" />
      </div>
    </div>

    <!-- 9模块切换Tab条 -->
    <div class="module-tabs">
      <div
        v-for="m in modules"
        :key="m.key"
        class="tab-item"
        :class="{ active: m.key === active }"
        :style="m.key === active ? { '--tab-color': m.color } : {}"
        @click="switchModule(m.key)"
      >
        <span class="tab-icon">{{ m.icon }}</span>
        <span class="tab-label">{{ m.label }}</span>
        <span v-if="m.badge" class="tab-badge">{{ m.badge }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.title_wrap {
  height: 90px;
  background-image: url("@/assets/img/top.png");
  background-size: cover;
  background-position: center center;
  position: relative;
  margin-bottom: 4px;

  .guang {
    position: absolute;
    bottom: -26px;
    background-image: url("../assets/img/guang.png");
    background-position: 80px center;
    width: 100%;
    height: 56px;
    pointer-events: none;
  }
  .zuojuxing,
  .youjuxing {
    position: absolute;
    top: -2px;
    width: 140px;
    height: 6px;
    background-image: url("@/assets/img/headers/juxing1.png");
  }
  .zuojuxing { left: 11%; }
  .youjuxing { right: 11%; transform: rotate(180deg); }
}

/* 左侧状态药丸 */
.header-left {
  position: absolute;
  left: 24px;
  top: 28px;
  display: flex;
  gap: 12px;
}
.status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border: 1px solid rgba(49, 171, 227, 0.4);
  border-radius: 999px;
  background: rgba(3, 5, 12, 0.5);
  backdrop-filter: blur(4px);
  font-size: 14px;
  color: rgba(224, 247, 255, 0.85);
  .label { opacity: 0.7; }
  .num { font-weight: 700; color: #00eaff; }
  .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #64748b;
    &.online { background: #07f7a8; box-shadow: 0 0 6px #07f7a8; }
  }
  &.warning .dot { background: #e3b337; box-shadow: 0 0 6px #e3b337; }
  &.warning .num { color: #e3b337; }
  &.danger .dot { background: #fc1a1a; box-shadow: 0 0 8px #fc1a1a; }
  &.danger .num { color: #fc1a1a; }
  &.critical .dot { background: #ff0040; box-shadow: 0 0 10px #ff0040; animation: blink 1s infinite; }
  &.critical .num { color: #ff0040; }
}
@keyframes blink { 50% { opacity: 0.3; } }

/* 中央标题 */
.title-center {
  display: flex; justify-content: center; align-items: flex-start; padding-top: 8px;
}
.title {
  text-align: center; height: 60px; line-height: 46px;
  .title-text {
    font-size: 36px; font-weight: 900; letter-spacing: 6px;
    background: linear-gradient(92deg, #0072ff 0%, #00eaff 48.85%, #01aaff 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
}

/* 右侧时钟+按钮 */
.header-right {
  position: absolute; right: 24px; top: 24px;
  display: flex; align-items: center; gap: 14px;
}
.btn-connect {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 16px; cursor: pointer;
  border: 1px solid rgba(0, 234, 255, 0.5);
  border-radius: 6px; background: rgba(0, 114, 255, 0.15);
  color: #00eaff; font-size: 14px; font-weight: 600;
  transition: all 0.2s;
  &:hover { background: rgba(0, 114, 255, 0.3); box-shadow: 0 0 10px rgba(0, 234, 255, 0.4); }
  .btn-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #64748b;
    &.on { background: #07f7a8; box-shadow: 0 0 8px #07f7a8; }
  }
}
.timers {
  font-family: "Consolas", "Microsoft YaHei", monospace;
  text-align: right; color: rgba(224, 247, 255, 0.85);
  .time-line { font-size: 18px; letter-spacing: 1px; }
  .time-sub { font-size: 12px; opacity: 0.7; }
}
.setting_icon {
  width: 20px; height: 20px; cursor: pointer;
  img { width: 100%; height: 100%; }
}

/* 9模块切换Tab */
.module-tabs {
  position: absolute; left: 50%; transform: translateX(-50%);
  bottom: -2px; display: flex; gap: 4px;
  background: rgba(3, 5, 12, 0.6); padding: 0 8px; border-radius: 8px 8px 0 0;
  border-top: 1px solid rgba(49, 171, 227, 0.3);
}
.tab-item {
  display: flex; align-items: center; gap: 5px;
  padding: 6px 14px; cursor: pointer; font-size: 13px;
  color: rgba(224, 247, 255, 0.6); border-radius: 4px;
  transition: all 0.2s; position: relative;
  border-bottom: 2px solid transparent;
  &:hover { color: #00eaff; background: rgba(0, 114, 255, 0.1); }
  &.active {
    color: #00eaff; background: rgba(0, 114, 255, 0.2);
    border-bottom-color: var(--tab-color, #00eaff);
  }
  .tab-icon { font-size: 14px; }
  .tab-badge {
    font-size: 9px; padding: 1px 5px; border-radius: 3px;
    background: #ff0040; color: #fff; font-weight: 700; letter-spacing: 0.5px;
  }
}
</style>
