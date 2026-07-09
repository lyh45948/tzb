<template>
  <span class="status-indicator">
    <span :class="['indicator-dot', connected ? 'online' : 'offline']"></span>
    <span class="indicator-text">{{ connected ? '在线' : '离线' }}</span>
  </span>
</template>

<script setup>
defineProps({
  connected: { type: Boolean, default: false }
})
</script>

<style scoped>
.status-indicator { display: inline-flex; align-items: center; gap: 5px; }
.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.indicator-dot.online {
  background: #22c55e;
  box-shadow: 0 0 6px #22c55e;
}
.indicator-dot.offline {
  background: #94a3b8;
}
.indicator-text { font-size: 14px; font-weight: 600; }
.indicator-dot.online + .indicator-text { color: #22c55e; }
.indicator-dot.offline + .indicator-text { color: #94a3b8; }
</style>
