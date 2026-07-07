<template>
  <div class="panel-frame">
    <div class="panel-header">
      <span class="dot"></span>风险预测
      <span class="header-sub">基于多维度数据推演 · 自动刷新</span>
    </div>
    <div class="panel-body risk-body">
      <div class="risk-summary">
        <div class="sum-cell">
          <div class="sum-num text-red">{{ countSeverity('high') + countSeverity('critical') }}</div>
          <div class="sum-label">高/紧急风险</div>
        </div>
        <div class="sum-cell">
          <div class="sum-num text-yellow">{{ countSeverity('medium') }}</div>
          <div class="sum-label">中等风险</div>
        </div>
        <div class="sum-cell">
          <div class="sum-num text-green">{{ countSeverity('low') }}</div>
          <div class="sum-label">低风险</div>
        </div>
        <div class="sum-cell">
          <div class="sum-num text-cyan">{{ avgProbability }}%</div>
          <div class="sum-label">综合置信度</div>
        </div>
      </div>

      <div class="risk-list">
        <div
          v-for="r in risks"
          :key="r.id"
          :class="['risk-item', 'sev-' + r.severity, { active: expandedId === r.id }]"
        >
          <div class="risk-head" @click="expandedId = expandedId === r.id ? null : r.id">
            <span class="cat-icon" :style="{ background: categoryColor(r.category) }">{{ categoryIcon(r.category) }}</span>
            <div class="risk-meta">
              <div class="risk-title">{{ r.title }}</div>
              <div class="risk-window">{{ r.window }}</div>
            </div>
            <div class="prob-block">
              <div class="prob-bar">
                <div class="prob-fill" :style="{ width: r.probability + '%', background: severityColor(r.severity) }"></div>
              </div>
              <div class="prob-text" :style="{ color: severityColor(r.severity) }">{{ r.probability }}%</div>
            </div>
            <span class="sev-tag" :style="{ background: severityColor(r.severity) }">{{ severityLabel(r.severity) }}</span>
            <span class="expand-arrow">{{ expandedId === r.id ? '▲' : '▼' }}</span>
          </div>

          <div v-if="expandedId === r.id" class="risk-detail">
            <div class="detail-section">
              <div class="section-title">推理路径</div>
              <div class="section-text">{{ r.reasoning }}</div>
            </div>
            <div class="detail-grid">
              <div class="detail-section">
                <div class="section-title">关键诱因</div>
                <ul class="bullet-list">
                  <li v-for="(f, i) in r.factors" :key="i">{{ f }}</li>
                </ul>
              </div>
              <div class="detail-section">
                <div class="section-title">缓解建议</div>
                <ul class="bullet-list">
                  <li v-for="(m, i) in r.mitigations" :key="i">{{ m }}</li>
                </ul>
              </div>
            </div>
            <div class="detail-actions">
              <button class="action-btn primary">下发建议</button>
              <button class="action-btn">忽略</button>
              <button class="action-btn">导出 PDF</button>
            </div>
          </div>
        </div>
        <div v-if="!risks.length" class="empty">智能体未识别到显著风险</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { buildRisks } from '../../utils/agentMockData'

// 后端接入: GET /api/agent/risks → AgentRisk[]
const risks = ref([])
const expandedId = ref(null)

onMounted(() => {
  risks.value = buildRisks()
})

function countSeverity(sev) { return risks.value.filter(r => r.severity === sev).length }
const avgProbability = computed(() => {
  if (!risks.value.length) return 0
  return Math.round(risks.value.reduce((s, r) => s + r.probability, 0) / risks.value.length)
})

const SEVERITY_MAP = {
  low: { label: '低', color: '#22c55e' },
  medium: { label: '中', color: '#f59e0b' },
  high: { label: '高', color: '#ef4444' },
  critical: { label: '紧急', color: '#7f1d1d' }
}
function severityLabel(s) { return SEVERITY_MAP[s]?.label || s }
function severityColor(s) { return SEVERITY_MAP[s]?.color || '#94a3b8' }

const CATEGORY_MAP = {
  gas: { icon: '☁', color: '#ef4444' },
  fire: { icon: '🔥', color: '#f97316' },
  collision: { icon: '◆', color: '#06b6d4' },
  environment: { icon: '🌡', color: '#2563eb' },
  battery: { icon: '⚡', color: '#f59e0b' },
  overload: { icon: '⚙', color: '#8b5cf6' }
}
function categoryIcon(c) { return CATEGORY_MAP[c]?.icon || '?' }
function categoryColor(c) { return CATEGORY_MAP[c]?.color || '#94a3b8' }
</script>

<style scoped>
.risk-body { display: flex; flex-direction: column; gap: 8px; height: 100%; min-height: 0; }
.header-sub { margin-left: auto; font-size: 12px; color: var(--text-secondary); font-weight: 400; letter-spacing: 0; }

.risk-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  flex-shrink: 0;
}
.sum-cell {
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  border-radius: 3px;
  padding: 6px;
  text-align: center;
}
.sum-num { font-size: 22px; font-weight: 800; line-height: 1.1; }
.sum-label { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }
.text-red { color: var(--accent-red); }
.text-yellow { color: var(--accent-yellow); }
.text-green { color: var(--accent-green); }
.text-cyan { color: var(--accent-cyan); }

.risk-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.risk-item {
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  border-radius: 3px;
  transition: background 0.15s;
}
.risk-item.sev-high,
.risk-item.sev-critical { border-color: rgba(239, 68, 68, 0.3); }

.risk-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  cursor: pointer;
  user-select: none;
}
.risk-head:hover { background: rgba(30, 80, 180, 0.06); }
.cat-icon {
  width: 26px;
  height: 26px;
  border-radius: 4px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}
.risk-meta { flex: 1; min-width: 0; }
.risk-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.risk-window { font-size: 11px; color: var(--text-secondary); margin-top: 1px; }

.prob-block { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.prob-bar {
  width: 80px;
  height: 6px;
  background: rgba(0,0,0,0.06);
  border-radius: 3px;
  overflow: hidden;
}
.prob-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.prob-text { font-size: 13px; font-weight: 700; font-family: 'Consolas', monospace; min-width: 40px; text-align: right; }

.sev-tag {
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 999px;
  flex-shrink: 0;
}
.expand-arrow { color: var(--text-secondary); font-size: 10px; flex-shrink: 0; }

.risk-detail {
  border-top: 1px dashed var(--border-dim);
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(255, 255, 255, 0.5);
}
.detail-section { display: flex; flex-direction: column; gap: 4px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.section-title {
  font-size: 11px;
  font-weight: 700;
  color: #7c3aed;
  letter-spacing: 0.5px;
}
.section-text { font-size: 12px; color: var(--text-primary); line-height: 1.5; }
.bullet-list { padding-left: 18px; margin: 0; }
.bullet-list li { font-size: 12px; color: var(--text-secondary); line-height: 1.6; }

.detail-actions { display: flex; gap: 6px; }
.action-btn {
  height: 26px;
  padding: 0 12px;
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  color: var(--text-secondary);
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.action-btn:hover { background: rgba(30, 80, 180, 0.1); }
.action-btn.primary {
  background: linear-gradient(90deg, #7c3aed, #06b6d4);
  border-color: transparent;
  color: #fff;
  font-weight: 600;
}
.action-btn.primary:hover { opacity: 0.92; }

.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
