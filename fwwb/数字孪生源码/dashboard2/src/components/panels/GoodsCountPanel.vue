<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>货物固定点计数</div>
    <div class="panel-body goods-body">
      <div class="rule-bar">
        <span class="rule-item">上限 <strong>{{ store.GOODS_CAPACITY }}</strong> 件</span>
        <span class="rule-item">≥ <strong>{{ store.GOODS_TRIGGER }}</strong> 件自动派车</span>
      </div>

      <div class="cargo-list">
        <div
          v-for="point in store.cargoPoints"
          :key="point.id"
          :class="['cargo-card', 'status-' + point.status]"
        >
          <div class="cargo-head">
            <div class="cargo-name">
              <span class="cargo-dot" :style="{ background: statusColor(point.status) }"></span>
              {{ point.name }}
            </div>
            <div class="cargo-count">
              <span class="count-num">{{ point.count }}</span>
              <span class="count-total">/ {{ store.GOODS_CAPACITY }}</span>
            </div>
          </div>

          <div class="progress-wrap">
            <div class="progress-track">
              <div
                class="progress-fill"
                :style="{ width: progressWidth(point.count), background: statusColor(point.status) }"
              ></div>
              <div
                class="trigger-line"
                :style="{ left: (store.GOODS_TRIGGER / store.GOODS_CAPACITY * 100) + '%' }"
                title="自动派车阈值"
              ></div>
            </div>
            <span class="status-tag" :style="{ color: statusColor(point.status) }">
              {{ statusLabel(point.status) }}
            </span>
          </div>
        </div>
      </div>

      <div class="hint">货物到达 40 件自动下发运输任务至出货口，小车运走后计数清零</div>
    </div>
  </div>
</template>

<script setup>
import { useDeviceStore } from '../../stores/deviceStore'

const store = useDeviceStore()

function progressWidth(count) {
  return Math.min(100, Math.round((count / store.GOODS_CAPACITY) * 100)) + '%'
}

const STATUS_MAP = {
  normal: { label: '正常', color: '#22c55e' },
  warning: { label: '待运输', color: '#f59e0b' },
  transporting: { label: '运输中', color: '#2563eb' },
  full: { label: '已满', color: '#ef4444' }
}

function statusLabel(status) {
  return STATUS_MAP[status]?.label || status
}

function statusColor(status) {
  return STATUS_MAP[status]?.color || '#94a3b8'
}
</script>

<style scoped>
.goods-body { display: flex; flex-direction: column; gap: 10px; }

.rule-bar {
  display: flex;
  gap: 12px;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(30, 80, 180, 0.04);
  font-size: 12px;
  color: var(--text-secondary);
}
.rule-item strong { color: var(--text-primary); font-family: 'Consolas', monospace; }

.cargo-list { display: flex; flex-direction: column; gap: 8px; min-height: 0; overflow: auto; }

.cargo-card {
  padding: 10px;
  border-radius: 6px;
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s;
}
.cargo-card.status-warning { border-color: rgba(245, 158, 11, 0.4); background: rgba(245, 158, 11, 0.06); }
.cargo-card.status-transporting { border-color: rgba(37, 99, 235, 0.4); background: rgba(37, 99, 235, 0.06); }
.cargo-card.status-full { border-color: rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.06); }

.cargo-head { display: flex; align-items: center; justify-content: space-between; }
.cargo-name { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: var(--text-primary); }
.cargo-dot { width: 8px; height: 8px; border-radius: 50%; box-shadow: 0 0 6px currentColor; }
.cargo-count { display: flex; align-items: baseline; gap: 3px; }
.count-num { font-size: 22px; font-weight: 800; color: var(--text-primary); font-family: 'Consolas', monospace; }
.count-total { font-size: 12px; color: var(--text-secondary); }

.progress-wrap { display: flex; align-items: center; gap: 8px; }
.progress-track {
  flex: 1;
  height: 8px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.trigger-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(239, 68, 68, 0.6);
  transform: translateX(-50%);
}
.status-tag {
  font-size: 12px;
  font-weight: 700;
  width: 48px;
  text-align: right;
  flex-shrink: 0;
}

.hint {
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.4;
  padding: 6px 8px;
  border-radius: 4px;
  background: rgba(30, 80, 180, 0.04);
}
</style>
