<template>
  <div class="panel-frame">
    <div class="panel-header">
      <span class="dot"></span>告警触发规则
      <span class="header-sub">{{ activeCount }} / {{ rules.length }} 启用</span>
    </div>
    <div class="panel-body trig-body">
      <div class="rule-list">
        <div
          v-for="r in rules"
          :key="r.id"
          :class="['rule-item', 'lvl-' + r.level, { off: !r.enabled }]"
        >
          <div class="rule-row1">
            <span class="lvl-tag" :style="{ background: levelColor(r.level) }">{{ levelLabel(r.level) }}</span>
            <span class="rule-name">{{ r.name }}</span>
            <label class="switch">
              <input type="checkbox" v-model="r.enabled" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="rule-desc">{{ r.description }}</div>
          <div class="rule-row2">
            <span class="meta">
              <span class="meta-label">指标</span>
              <span class="meta-value">{{ r.metric }}</span>
            </span>
            <span class="meta">
              <span class="meta-label">条件</span>
              <span class="meta-value cond">{{ r.condition }}</span>
            </span>
            <span class="meta">
              <span class="meta-label">24h</span>
              <span class="meta-value" :style="{ color: r.hits ? levelColor(r.level) : '#94a3b8' }">{{ r.hits }} 次</span>
            </span>
            <span class="meta">
              <span class="meta-label">最近</span>
              <span class="meta-value dim">{{ formatTime(r.lastFiredAt) }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { buildTriggerRules } from '../../utils/agentMockData'

// 后端接入:
//   GET  /api/agent/rules   → AgentTriggerRule[]
//   PATCH /api/agent/rules/{id}  body: { enabled }
const rules = ref([])

onMounted(() => {
  rules.value = buildTriggerRules()
})

const activeCount = computed(() => rules.value.filter(r => r.enabled).length)

const LEVEL_MAP = {
  warning: { label: '警告', color: '#f59e0b' },
  danger: { label: '危险', color: '#ef4444' },
  critical: { label: '紧急', color: '#7f1d1d' }
}
function levelLabel(l) { return LEVEL_MAP[l]?.label || l }
function levelColor(l) { return LEVEL_MAP[l]?.color || '#94a3b8' }

function formatTime(ts) {
  if (!ts) return '从未'
  const diffMin = Math.floor((Date.now() - ts) / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  if (diffMin < 60 * 24) return `${Math.floor(diffMin / 60)} 小时前`
  return `${Math.floor(diffMin / (60 * 24))} 天前`
}
</script>

<style scoped>
.trig-body { display: flex; flex-direction: column; gap: 6px; height: 100%; min-height: 0; }
.header-sub { margin-left: auto; font-size: 12px; color: var(--text-secondary); font-weight: 400; letter-spacing: 0; }

.rule-list { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }

.rule-item {
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  border-left: 3px solid #94a3b8;
  border-radius: 3px;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: background 0.15s, opacity 0.15s;
}
.rule-item.lvl-warning { border-left-color: var(--accent-yellow); }
.rule-item.lvl-danger { border-left-color: var(--accent-red); }
.rule-item.lvl-critical { border-left-color: #7f1d1d; }
.rule-item.off { opacity: 0.5; }
.rule-item:hover { background: rgba(30, 80, 180, 0.07); }

.rule-row1 { display: flex; align-items: center; gap: 8px; }
.lvl-tag {
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 999px;
  flex-shrink: 0;
}
.rule-name { flex: 1; font-size: 13px; font-weight: 700; color: var(--text-primary); }

/* iOS 风格开关 */
.switch { position: relative; display: inline-block; width: 32px; height: 18px; flex-shrink: 0; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: #cbd5e1;
  border-radius: 999px;
  transition: 0.2s;
}
.slider::before {
  content: '';
  position: absolute;
  height: 14px;
  width: 14px;
  left: 2px;
  top: 2px;
  background: #fff;
  border-radius: 50%;
  transition: 0.2s;
}
.switch input:checked + .slider { background: #7c3aed; }
.switch input:checked + .slider::before { transform: translateX(14px); }

.rule-desc { font-size: 12px; color: var(--text-secondary); line-height: 1.5; }
.rule-row2 { display: flex; flex-wrap: wrap; gap: 10px; padding-top: 2px; }
.meta { display: inline-flex; align-items: baseline; gap: 4px; font-size: 11px; }
.meta-label { color: var(--text-secondary); }
.meta-value { font-weight: 700; color: var(--text-primary); font-family: 'Consolas', monospace; }
.meta-value.cond { color: #7c3aed; }
.meta-value.dim { font-weight: 500; color: var(--text-secondary); }
</style>
