<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>货物感应计数</div>
    <div class="panel-body goods-body">
      <div class="counter-main">
        <div>
          <div class="counter-label">今日累计</div>
          <div class="counter-value">{{ store.goodsCount }}</div>
        </div>
        <div :class="['pulse-badge', { active: store.goodsPulse }]">
          {{ store.goodsPulse ? 'P6 脉冲' : '等待通过' }}
        </div>
      </div>

      <div class="digits-row">
        <span class="label">视觉计数</span>
        <span class="digits">{{ store.counterDigits }}</span>
      </div>

      <div class="goods-list">
        <div v-for="robot in goodsRobots" :key="robot.id" class="goods-item">
          <div class="goods-name">
            <span class="goods-dot"></span>
            {{ robot.name }}
          </div>
          <div class="goods-meta">
            <span>{{ robot.device_id }}</span>
            <strong>{{ robot.goodsCount }} 件</strong>
          </div>
        </div>
      </div>

      <div class="hint">演示数据：模拟货物感应/视觉计数，暂未接入后端</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'

const store = useDeviceStore()

const goodsRobots = computed(() => {
  return store.fleet.filter(r => r.task === 'goodsCount' || r.goodsCount != null).slice(0, 3)
})
</script>

<style scoped>
.goods-body { display: flex; flex-direction: column; gap: 7px; }
.counter-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: 6px;
  background: linear-gradient(90deg, rgba(34,197,94,0.12), rgba(6,182,212,0.08));
}
.counter-label { color: var(--text-secondary); font-size: 12px; }
.counter-value { color: #16a34a; font-size: 24px; font-weight: 800; font-family: 'Consolas', monospace; }
.pulse-badge {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(148,163,184,0.16);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
}
.pulse-badge.active {
  background: rgba(34,197,94,0.18);
  color: #16a34a;
  box-shadow: 0 0 10px rgba(34,197,94,0.35);
}
.digits-row { display: flex; justify-content: space-between; align-items: center; }
.label { color: var(--text-secondary); font-size: 13px; }
.digits { color: #2563eb; font-weight: 800; letter-spacing: 2px; font-family: 'Consolas', monospace; }
.goods-list { display: flex; flex-direction: column; gap: 4px; min-height: 0; overflow: auto; }
.goods-item { padding: 4px 6px; border-radius: 4px; background: rgba(0,0,0,0.04); }
.goods-name { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; }
.goods-dot { width: 6px; height: 6px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 6px #22c55e; }
.goods-meta { margin-top: 2px; display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 12px; }
.goods-meta strong { color: #16a34a; }
.hint { color: var(--text-secondary); font-size: 11px; line-height: 1.3; }
</style>
