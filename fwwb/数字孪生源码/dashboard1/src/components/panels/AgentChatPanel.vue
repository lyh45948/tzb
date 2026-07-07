<template>
  <div class="panel-frame">
    <div class="panel-header">
      <span class="dot"></span>智能体洞察流
      <div class="header-tools">
        <span class="status-pill" :class="agent.online ? 'on' : 'off'">
          <span class="led"></span>{{ agent.online ? '在线' : '离线' }}
        </span>
        <span class="agent-name">{{ agent.name }} · {{ agent.version }}</span>
        <button class="mini-btn" @click="paused = !paused">{{ paused ? '继续' : '暂停' }}</button>
      </div>
    </div>

    <div class="panel-body chat-body">
      <div class="filter-bar">
        <button
          v-for="f in filters"
          :key="f.value"
          :class="['filter-btn', { active: activeFilter === f.value }]"
          @click="activeFilter = f.value"
        >{{ f.label }}<span class="count">{{ countOf(f.value) }}</span></button>
      </div>

      <div class="insight-stream" ref="streamEl">
        <div
          v-for="ins in filtered"
          :key="ins.id"
          class="insight-item"
          :class="['lvl-' + ins.level]"
        >
          <div class="ins-row top">
            <span class="lvl-tag" :style="{ background: levelColor(ins.level) }">{{ levelLabel(ins.level) }}</span>
            <span class="kind-tag">{{ kindLabel(ins.kind) }}</span>
            <span class="ins-title">{{ ins.title }}</span>
            <span class="ins-time">{{ formatTime(ins.timestamp) }}</span>
          </div>
          <div class="ins-content">{{ ins.content }}</div>
          <div v-if="ins.evidence?.length" class="ins-evidence">
            <span v-for="(ev, i) in ins.evidence" :key="i" class="ev-pill">
              <span class="ev-label">{{ ev.label }}</span>
              <span class="ev-value">{{ ev.value }}</span>
            </span>
          </div>
          <div v-if="ins.suggestion" class="ins-suggest">
            <span class="suggest-icon">💡</span>{{ ins.suggestion }}
          </div>
          <div class="ins-foot">来源 · {{ ins.source }}</div>
        </div>
        <div v-if="!filtered.length" class="empty">暂无相关洞察</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { buildInitialInsights, rollInsight, buildAgentStatus } from '../../utils/agentMockData'

// 后端接入:
//   1. 把 buildInitialInsights() 替换为 fetch('/api/agent/insights')
//   2. 把 setInterval(rollInsight) 替换为 WebSocket('/ws/agent/insights') + 推送追加
//   3. 把 buildAgentStatus() 替换为 fetch('/api/agent/status')
const insights = ref(buildInitialInsights())
const agent = ref(buildAgentStatus())

const paused = ref(false)
const activeFilter = ref('all')
const streamEl = ref(null)

const filters = [
  { value: 'all', label: '全部' },
  { value: 'critical', label: '紧急' },
  { value: 'danger', label: '危险' },
  { value: 'warning', label: '警告' },
  { value: 'info', label: '信息' },
  { value: 'success', label: '正常' }
]

const filtered = computed(() => {
  if (activeFilter.value === 'all') return insights.value
  return insights.value.filter(i => i.level === activeFilter.value)
})

function countOf(level) {
  if (level === 'all') return insights.value.length
  return insights.value.filter(i => i.level === level).length
}

const LEVEL_MAP = {
  info: { label: '信息', color: '#06b6d4' },
  success: { label: '正常', color: '#22c55e' },
  warning: { label: '警告', color: '#f59e0b' },
  danger: { label: '危险', color: '#ef4444' },
  critical: { label: '紧急', color: '#7f1d1d' }
}
const KIND_MAP = {
  observation: '观察',
  reasoning: '推理',
  action: '联动',
  prediction: '预测'
}
function levelLabel(l) { return LEVEL_MAP[l]?.label || l }
function levelColor(l) { return LEVEL_MAP[l]?.color || '#94a3b8' }
function kindLabel(k) { return KIND_MAP[k] || k }

function formatTime(ts) {
  const d = new Date(ts)
  const now = Date.now()
  const diffMin = Math.floor((now - ts) / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

let timer = null
let uptimeTimer = null
onMounted(() => {
  // 演示用:每 5s 滚动一条新洞察。后端接入时移除。
  timer = setInterval(() => {
    if (!paused.value) {
      insights.value = rollInsight(insights.value)
      nextTick(() => {
        if (streamEl.value) streamEl.value.scrollTop = 0
      })
    }
  }, 5000)
  uptimeTimer = setInterval(() => {
    agent.value.uptimeSec += 1
  }, 1000)
})
onUnmounted(() => {
  clearInterval(timer)
  clearInterval(uptimeTimer)
})
</script>

<style scoped>
.chat-body { display: flex; flex-direction: column; gap: 8px; height: 100%; min-height: 0; padding-top: 0; }

.header-tools {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}
.status-pill.on { background: rgba(34, 197, 94, 0.15); color: var(--accent-green); }
.status-pill.off { background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }
.status-pill .led {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 6px currentColor;
}
.agent-name { font-size: 12px; color: var(--text-secondary); font-weight: 600; }

.mini-btn {
  background: rgba(124, 58, 237, 0.1);
  border: 1px solid rgba(124, 58, 237, 0.25);
  color: #7c3aed;
  padding: 1px 8px;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.mini-btn:hover { background: rgba(124, 58, 237, 0.18); }

.filter-bar {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.filter-btn {
  height: 24px;
  padding: 0 8px;
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  border-radius: 3px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.18s;
}
.filter-btn:hover { background: rgba(30, 80, 180, 0.1); }
.filter-btn.active {
  background: rgba(124, 58, 237, 0.12);
  border-color: #7c3aed;
  color: #7c3aed;
  font-weight: 600;
}
.filter-btn .count {
  font-size: 10px;
  background: rgba(0,0,0,0.06);
  padding: 0 4px;
  border-radius: 6px;
  min-width: 14px;
  text-align: center;
}

.insight-stream {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.insight-item {
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  border-left: 3px solid #94a3b8;
  border-radius: 3px;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: background 0.15s;
}
.insight-item:hover { background: rgba(30, 80, 180, 0.07); }
.insight-item.lvl-warning { border-left-color: var(--accent-yellow); }
.insight-item.lvl-danger { border-left-color: var(--accent-red); }
.insight-item.lvl-critical { border-left-color: #7f1d1d; background: rgba(239, 68, 68, 0.05); }
.insight-item.lvl-success { border-left-color: var(--accent-green); }
.insight-item.lvl-info { border-left-color: var(--accent-cyan); }

.ins-row.top { display: flex; align-items: center; gap: 6px; }
.lvl-tag {
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 999px;
  letter-spacing: 0.4px;
}
.kind-tag {
  font-size: 11px;
  background: rgba(124, 58, 237, 0.12);
  color: #7c3aed;
  padding: 1px 6px;
  border-radius: 999px;
  font-weight: 600;
}
.ins-title { flex: 1; font-size: 13px; font-weight: 700; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ins-time { font-size: 11px; color: var(--text-secondary); flex-shrink: 0; }
.ins-content { font-size: 12px; color: var(--text-secondary); line-height: 1.5; }
.ins-evidence { display: flex; flex-wrap: wrap; gap: 4px; }
.ev-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(30, 80, 180, 0.06);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
}
.ev-label { color: var(--text-secondary); }
.ev-value { font-weight: 700; color: var(--text-primary); font-family: 'Consolas', monospace; }

.ins-suggest {
  font-size: 12px;
  background: rgba(245, 158, 11, 0.08);
  border-left: 2px solid var(--accent-yellow);
  padding: 4px 6px;
  border-radius: 2px;
  color: #78350f;
  display: flex;
  align-items: flex-start;
  gap: 4px;
}
.suggest-icon { flex-shrink: 0; }

.ins-foot { font-size: 11px; color: var(--text-secondary); }

.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
