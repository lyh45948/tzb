<template>
  <div class="panel-frame">
    <div class="panel-header">
      <span class="dot"></span>智能体日报 / 周报
      <div class="header-tools">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          :class="['tab-btn', { active: activeTab === tab.value }]"
          @click="onSwitchTab(tab.value)"
        >{{ tab.label }}</button>
        <button class="mini-btn" @click="regenerate">↻ 重新评判</button>
      </div>
    </div>

    <div class="panel-body report-body" v-if="report">
      <!-- 评分卡 -->
      <div class="score-card">
        <div class="score-left">
          <div class="grade-badge" :style="{ background: gradeColor(report.grade) }">{{ report.grade }}</div>
          <div class="score-num-block">
            <div class="score-num">{{ report.score }}</div>
            <div class="score-base">/100</div>
          </div>
        </div>
        <div class="score-right">
          <div class="score-period">{{ report.period }}</div>
          <div class="score-headline">{{ report.headline }}</div>
          <div class="score-trend">
            <span class="trend-label">趋势</span>
            <span class="spark">
              <span
                v-for="(v, i) in report.trend.values"
                :key="i"
                class="spark-bar"
                :style="{
                  height: (8 + (v - 70) * 0.8) + 'px',
                  background: v >= 90 ? '#22c55e' : v >= 80 ? '#f59e0b' : '#ef4444'
                }"
                :title="report.trend.labels[i] + ' · ' + v"
              ></span>
            </span>
          </div>
        </div>
      </div>

      <!-- 维度评分 -->
      <div class="section">
        <div class="sec-title">维度评分</div>
        <div class="dim-grid">
          <div v-for="d in report.dimensions" :key="d.name" class="dim-cell">
            <div class="dim-row1">
              <span class="dim-name">{{ d.name }}</span>
              <span class="dim-score">{{ d.score }}</span>
              <span class="dim-delta" :class="d.delta > 0 ? 'up' : d.delta < 0 ? 'down' : 'flat'">
                {{ d.delta > 0 ? '+' : '' }}{{ d.delta }}
              </span>
            </div>
            <div class="dim-bar">
              <div class="dim-fill" :style="{ width: d.score + '%', background: scoreColor(d.score) }"></div>
            </div>
            <div class="dim-note">{{ d.note }}</div>
          </div>
        </div>
      </div>

      <!-- 亮点 -->
      <div v-if="report.highlights?.length" class="section">
        <div class="sec-title good">✓ 表现亮点</div>
        <div v-for="h in report.highlights" :key="h.title" class="entry good">
          <div class="entry-title">{{ h.title }}</div>
          <div class="entry-detail">{{ h.detail }}</div>
        </div>
      </div>

      <!-- 待改进 -->
      <div v-if="report.concerns?.length" class="section">
        <div class="sec-title warn">⚠ 待改进</div>
        <div v-for="c in report.concerns" :key="c.title" class="entry warn">
          <div class="entry-title">{{ c.title }}</div>
          <div class="entry-detail">{{ c.detail }}</div>
        </div>
      </div>

      <!-- 建议 -->
      <div class="section">
        <div class="sec-title accent">→ 智能体建议</div>
        <ol class="rec-list">
          <li v-for="(r, i) in report.recommendations" :key="i">{{ r }}</li>
        </ol>
      </div>

      <!-- 操作 -->
      <div class="report-actions">
        <button class="rep-btn primary">采纳并下发</button>
        <button class="rep-btn">导出 PDF</button>
        <button class="rep-btn">推送至值班群</button>
        <span class="footer-meta">由 {{ status.name }} {{ status.version }} 生成</span>
      </div>
    </div>

    <div v-else class="panel-body empty-body">
      <div class="loading-text">智能体正在生成报告 …</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { buildLatestReport, buildAgentStatus } from '../../utils/agentMockData'

// 后端接入:
//   GET /api/agent/report?type=daily|weekly → AgentReport
//   POST /api/agent/report/regenerate?type=...
const tabs = [
  { value: 'daily', label: '日报' },
  { value: 'weekly', label: '周报' }
]
const activeTab = ref('daily')
const report = ref(null)
const status = ref(buildAgentStatus())

function loadReport(type) {
  // 假装请求中
  report.value = null
  setTimeout(() => {
    report.value = buildLatestReport(type)
  }, 250)
}

function onSwitchTab(type) {
  if (activeTab.value === type) return
  activeTab.value = type
  loadReport(type)
}

function regenerate() {
  loadReport(activeTab.value)
}

onMounted(() => {
  loadReport('daily')
})

const GRADE_COLORS = {
  S: 'linear-gradient(135deg, #fbbf24, #f59e0b)',
  A: 'linear-gradient(135deg, #22c55e, #16a34a)',
  B: 'linear-gradient(135deg, #06b6d4, #0891b2)',
  C: 'linear-gradient(135deg, #f59e0b, #d97706)',
  D: 'linear-gradient(135deg, #ef4444, #b91c1c)'
}
function gradeColor(g) { return GRADE_COLORS[g] || '#94a3b8' }
function scoreColor(s) {
  if (s >= 90) return '#22c55e'
  if (s >= 80) return '#06b6d4'
  if (s >= 70) return '#f59e0b'
  return '#ef4444'
}
</script>

<style scoped>
.report-body { display: flex; flex-direction: column; gap: 10px; }
.empty-body { display: flex; align-items: center; justify-content: center; }
.loading-text {
  color: var(--text-secondary);
  font-size: 14px;
  padding: 40px;
  letter-spacing: 1px;
}

.header-tools { margin-left: auto; display: flex; align-items: center; gap: 4px; }
.tab-btn {
  height: 24px;
  padding: 0 12px;
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  color: var(--text-secondary);
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.tab-btn.active {
  background: rgba(124, 58, 237, 0.12);
  border-color: #7c3aed;
  color: #7c3aed;
  font-weight: 600;
}
.mini-btn {
  margin-left: 6px;
  height: 24px;
  padding: 0 10px;
  background: rgba(124, 58, 237, 0.08);
  border: 1px solid rgba(124, 58, 237, 0.25);
  color: #7c3aed;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
}
.mini-btn:hover { background: rgba(124, 58, 237, 0.18); }

/* 评分卡 */
.score-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
  padding: 12px 14px;
  border-radius: 6px;
  background: linear-gradient(120deg, rgba(124, 58, 237, 0.08), rgba(6, 182, 212, 0.05));
  border: 1px solid rgba(124, 58, 237, 0.2);
}
.score-left { display: flex; align-items: center; gap: 12px; }
.grade-badge {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 1px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
.score-num-block { display: flex; align-items: baseline; gap: 2px; }
.score-num { font-size: 36px; font-weight: 800; color: var(--text-primary); line-height: 1; }
.score-base { font-size: 14px; color: var(--text-secondary); }

.score-right { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.score-period { font-size: 12px; color: var(--text-secondary); font-weight: 600; }
.score-headline { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.score-trend { display: flex; align-items: flex-end; gap: 6px; margin-top: 4px; }
.trend-label { font-size: 11px; color: var(--text-secondary); }
.spark { display: inline-flex; align-items: flex-end; gap: 2px; height: 28px; }
.spark-bar { width: 8px; border-radius: 1px; transition: height 0.3s; }

/* 段落 */
.section { display: flex; flex-direction: column; gap: 6px; }
.sec-title { font-size: 12px; font-weight: 700; color: var(--text-secondary); letter-spacing: 0.5px; }
.sec-title.good { color: var(--accent-green); }
.sec-title.warn { color: var(--accent-yellow); }
.sec-title.accent { color: #7c3aed; }

/* 维度评分 */
.dim-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 6px;
}
.dim-cell {
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  border-radius: 3px;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dim-row1 { display: flex; align-items: baseline; gap: 6px; }
.dim-name { flex: 1; font-size: 12px; font-weight: 600; color: var(--text-primary); }
.dim-score { font-size: 16px; font-weight: 800; color: var(--text-primary); font-family: 'Consolas', monospace; }
.dim-delta { font-size: 11px; font-weight: 700; }
.dim-delta.up { color: var(--accent-green); }
.dim-delta.down { color: var(--accent-red); }
.dim-delta.flat { color: var(--text-secondary); }
.dim-bar { height: 4px; background: rgba(0,0,0,0.06); border-radius: 2px; overflow: hidden; }
.dim-fill { height: 100%; transition: width 0.4s; }
.dim-note { font-size: 11px; color: var(--text-secondary); }

/* 亮点 / 待改进 */
.entry {
  border-left: 3px solid;
  padding: 4px 8px;
  border-radius: 0 3px 3px 0;
  background: rgba(30, 80, 180, 0.03);
}
.entry.good { border-color: var(--accent-green); background: rgba(34, 197, 94, 0.06); }
.entry.warn { border-color: var(--accent-yellow); background: rgba(245, 158, 11, 0.06); }
.entry-title { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.entry-detail { font-size: 12px; color: var(--text-secondary); margin-top: 2px; line-height: 1.5; }

.rec-list { padding-left: 22px; margin: 0; }
.rec-list li { font-size: 12px; color: var(--text-primary); line-height: 1.7; }

/* 操作 */
.report-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-top: 6px;
  border-top: 1px dashed var(--border-dim);
}
.rep-btn {
  height: 28px;
  padding: 0 12px;
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  color: var(--text-secondary);
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.rep-btn:hover { background: rgba(30, 80, 180, 0.1); }
.rep-btn.primary {
  background: linear-gradient(90deg, #7c3aed, #06b6d4);
  border-color: transparent;
  color: #fff;
  font-weight: 600;
}
.rep-btn.primary:hover { opacity: 0.92; }
.footer-meta {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-secondary);
}
</style>
