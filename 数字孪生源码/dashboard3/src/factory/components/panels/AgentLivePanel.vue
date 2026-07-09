<template>
  <div class="panel-frame agent-live">
    <div class="panel-header">
      <span class="dot"></span>智能体实时洞察
      <div class="header-tools">
        <span class="status-pill" :class="statusInfo.cls">
          <span class="led"></span>{{ statusInfo.label }}
        </span>
        <span class="agent-name">{{ deviceLabel }} · {{ aiBackendLabel }}</span>
        <button class="mini-btn" :disabled="triggering" @click="triggerAnalysis">
          {{ triggering ? '分析中…' : '立即分析' }}
        </button>
      </div>
    </div>

    <div class="panel-body live-body">
      <!-- 最近一条 AI 文本 / 紧急指导 -->
      <div class="latest-card" :class="alertClass">
        <div class="latest-head">
          <span class="latest-tag" :style="{ background: alertColor }">
            {{ alertLabel }}
          </span>
          <span class="latest-time">{{ formatTime(latestTimestamp) }}</span>
        </div>
        <div class="latest-text">{{ latestMessage }}</div>
        <div v-if="latestAlert?.actionTaken" class="latest-actions">
          <span class="action-tag">已执行</span>
          <span
            v-for="(sent, key) in latestAlert.actionTaken.sent"
            :key="key"
            class="action-pill"
            :class="{ ok: sent, fail: !sent }"
          >
            {{ formatActionKey(key) }}={{ formatActionValue(key) }} · {{ sent ? '✓' : '✗' }}
          </span>
        </div>
        <div
          v-if="latestAlert?.recommendations?.length"
          class="latest-suggest"
        >
          <span class="suggest-icon">💡</span>{{ latestAlert.recommendations.join('；') }}
        </div>
      </div>

      <!-- 趋势预测 -->
      <div class="section-title">趋势预测</div>
      <div v-if="!predictions.length" class="empty-tip">暂无预测，等待样本累计…</div>
      <div v-else class="pred-list">
        <div
          v-for="p in predictions"
          :key="p.id"
          class="pred-row"
          :class="['risk-' + (p.riskLevel || 'normal')]"
        >
          <div class="pred-field">{{ fieldLabel(p.field) }}</div>
          <div class="pred-trend">
            {{ formatNum(p.currentValue) }}
            <span class="arrow" :class="p.trend">{{ trendArrow(p.trend) }}</span>
            {{ formatNum(p.nextPrediction) }}
          </div>
          <div class="pred-msg">{{ p.message }}</div>
        </div>
      </div>

      <!-- 报告摘要 -->
      <div class="section-title">最近报告</div>
      <div class="reports-row">
        <div class="report-card" :class="{ empty: !daily }">
          <div class="report-cap">日报 · {{ daily?.date || '尚无' }}</div>
          <div class="report-text">{{ daily?.summary || '今日尚未生成日报' }}</div>
        </div>
        <div class="report-card" :class="{ empty: !weekly }">
          <div class="report-cap">周报 · {{ weekly?.date || '尚无' }}</div>
          <div class="report-text">{{ weekly?.summary || '本周尚未生成周报' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { triggerAgent } from '../../services/api'

const store = useDeviceStore()
const triggering = ref(false)

// store.aiAgent 由 dashboardAdapter.applySnapshot 写入；首屏可能为空
const agent = computed(() => store.aiAgent || {})
const latestAlert = computed(() => agent.value.latestAlert || null)
const latestAnalysis = computed(() => agent.value.latestAnalysis || null)
const predictions = computed(() => Array.isArray(agent.value.predictions) ? agent.value.predictions : [])
const daily = computed(() => agent.value.reports?.daily || null)
const weekly = computed(() => agent.value.reports?.weekly || null)

const deviceLabel = computed(() => agent.value.device_id || 'agent')
const aiBackendLabel = computed(() =>
  agent.value.aiBackend === 'ollama' ? 'AI · ollama' : 'AI · 模板'
)

const statusInfo = computed(() => {
  const status = agent.value.status || 'idle'
  if (!agent.value.enabled) return { cls: 'off', label: '未启用' }
  if (status === 'critical') return { cls: 'critical', label: '紧急' }
  if (status === 'alert') return { cls: 'alert', label: '告警' }
  if (status === 'normal' || status === 'running') return { cls: 'on', label: '在线' }
  return { cls: 'idle', label: status }
})

// 优先展示告警内容；告警没有时退到分析摘要
const latestMessage = computed(() => {
  if (latestAlert.value) return latestAlert.value.message
  if (latestAnalysis.value) return latestAnalysis.value.text
  return '智能体启动中，待传感器数据足够后开始分析。'
})

const latestTimestamp = computed(() => {
  return latestAlert.value?.timestamp
    || latestAnalysis.value?.timestamp
    || agent.value.updatedAt
})

const alertClass = computed(() => {
  const lvl = latestAlert.value?.level
  if (lvl === 'critical') return 'critical'
  if (lvl === 'warning') return 'warning'
  return 'normal'
})

const alertLabel = computed(() => {
  const lvl = latestAlert.value?.level
  if (lvl === 'critical') return '紧急'
  if (lvl === 'warning') return '注意'
  return '正常'
})

const alertColor = computed(() => {
  const lvl = latestAlert.value?.level
  if (lvl === 'critical') return '#ef4444'
  if (lvl === 'warning') return '#f59e0b'
  return '#22c55e'
})

function formatTime(ts) {
  if (!ts) return '--:--:--'
  const d = typeof ts === 'string' ? new Date(ts) : new Date(Number(ts))
  if (Number.isNaN(d.getTime())) return '--:--:--'
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}

function formatNum(v) {
  if (v == null) return '--'
  const n = Number(v)
  return Number.isFinite(n) ? (Math.abs(n) >= 100 ? n.toFixed(0) : n.toFixed(1)) : '--'
}

const FIELD_LABELS = { co: 'CO', temp: '温度', humi: '湿度', tvoc: 'TVOC' }
function fieldLabel(field) {
  return FIELD_LABELS[field] || field || '--'
}

function trendArrow(trend) {
  if (trend === 'up') return '↗'
  if (trend === 'down') return '↘'
  return '→'
}

function formatActionKey(key) {
  if (key === 'fan') return '风扇'
  if (key === 'buzzer') return '蜂鸣器'
  if (key === 'carStatus') return '车辆'
  return key
}

function formatActionValue(key) {
  const cmds = latestAlert.value?.actionTaken?.commands || {}
  if (key === 'carStatus') return cmds[key] || ''
  return cmds[key] === 1 ? '开' : cmds[key] === 0 ? '关' : (cmds[key] ?? '')
}

async function triggerAnalysis() {
  if (triggering.value) return
  triggering.value = true
  try {
    await triggerAgent('analysis')
  } catch (e) {
    console.warn('[AgentLivePanel] 触发分析失败', e)
  } finally {
    // SSE 下一帧会刷新 store.aiAgent，无需手动 fetch
    setTimeout(() => { triggering.value = false }, 800)
  }
}
</script>

<style scoped>
.agent-live { display: flex; flex-direction: column; min-height: 0; }
.live-body { display: flex; flex-direction: column; gap: 8px; overflow: auto; padding-right: 4px; }

.header-tools { display: flex; align-items: center; gap: 8px; margin-left: auto; }
.status-pill {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 999px;
  font-size: 11px; font-weight: 600;
}
.status-pill .led {
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 6px currentColor;
}
.status-pill.on { color: #16a34a; background: rgba(34,197,94,0.12); }
.status-pill.alert { color: #d97706; background: rgba(245,158,11,0.15); }
.status-pill.critical { color: #dc2626; background: rgba(239,68,68,0.18); animation: blink 1s infinite; }
.status-pill.off, .status-pill.idle { color: #6b7280; background: rgba(107,114,128,0.12); }
@keyframes blink { 50% { opacity: 0.55; } }

.agent-name { font-size: 11px; color: var(--text-secondary); font-family: 'Consolas', monospace; }
.mini-btn {
  padding: 2px 8px; font-size: 11px; border-radius: 6px; cursor: pointer;
  border: 1px solid rgba(124,58,237,0.4); background: rgba(124,58,237,0.08); color: #6d28d9;
}
.mini-btn:disabled { opacity: 0.55; cursor: progress; }

.latest-card {
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 8px; padding: 8px 10px;
  background: rgba(255,255,255,0.6);
  display: flex; flex-direction: column; gap: 6px;
}
.latest-card.warning { border-color: rgba(245,158,11,0.45); background: rgba(254,243,199,0.55); }
.latest-card.critical { border-color: rgba(239,68,68,0.6); background: rgba(254,226,226,0.6); }

.latest-head { display: flex; align-items: center; gap: 6px; }
.latest-tag {
  color: #fff; font-size: 11px; font-weight: 700;
  padding: 1px 8px; border-radius: 999px;
}
.latest-time { font-size: 11px; color: var(--text-secondary); margin-left: auto; font-family: 'Consolas', monospace; }
.latest-text { font-size: 13px; color: var(--text-primary); line-height: 1.45; }
.latest-suggest {
  font-size: 12px; color: var(--text-secondary);
  display: flex; gap: 4px; align-items: flex-start;
}
.suggest-icon { flex-shrink: 0; }

.latest-actions { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
.action-tag {
  font-size: 10px; padding: 1px 6px; border-radius: 4px;
  background: rgba(124,58,237,0.12); color: #6d28d9; font-weight: 700;
}
.action-pill {
  font-size: 11px; padding: 1px 6px; border-radius: 4px;
  font-family: 'Consolas', monospace;
}
.action-pill.ok { background: rgba(34,197,94,0.12); color: #16a34a; }
.action-pill.fail { background: rgba(239,68,68,0.12); color: #dc2626; }

.section-title {
  font-size: 12px; color: var(--text-secondary); font-weight: 700;
  margin-top: 4px; padding-left: 2px;
  letter-spacing: 0.5px;
}

.empty-tip { font-size: 12px; color: var(--text-secondary); padding: 4px 6px; }

.pred-list { display: flex; flex-direction: column; gap: 4px; }
.pred-row {
  display: grid;
  grid-template-columns: 56px 110px 1fr;
  gap: 6px; align-items: center;
  padding: 5px 8px; border-radius: 6px;
  background: rgba(0,0,0,0.04);
  font-size: 12px;
}
.pred-row.risk-warning { background: rgba(245,158,11,0.12); }
.pred-row.risk-critical { background: rgba(239,68,68,0.15); }
.pred-field { font-weight: 700; color: var(--text-primary); }
.pred-trend { font-family: 'Consolas', monospace; font-size: 13px; color: var(--text-primary); }
.pred-trend .arrow { margin: 0 4px; font-weight: 700; }
.pred-trend .arrow.up { color: #ef4444; }
.pred-trend .arrow.down { color: #22c55e; }
.pred-msg { color: var(--text-secondary); font-size: 11px; }

.reports-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.report-card {
  border: 1px solid rgba(0,0,0,0.06); border-radius: 6px;
  padding: 6px 8px; background: rgba(255,255,255,0.55);
  display: flex; flex-direction: column; gap: 2px;
}
.report-card.empty { opacity: 0.55; }
.report-cap { font-size: 11px; font-weight: 700; color: #6d28d9; }
.report-text { font-size: 11px; color: var(--text-secondary); line-height: 1.4; }
</style>
