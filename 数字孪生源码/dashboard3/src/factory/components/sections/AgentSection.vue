<template>
  <div class="section-page agent-section">
    <div class="agent-banner">
      <div class="banner-left">
        <span class="ai-icon">🤖</span>
        <div class="banner-meta">
          <div class="banner-title">智能体工作台 · {{ status.name }}</div>
          <div class="banner-sub">订阅多模态数据 · 自动触发告警 · 预测风险 · 生成评判报告</div>
        </div>
      </div>
      <div class="banner-stats">
        <div class="stat">
          <div class="stat-value text-cyan">{{ status.samplesPerMin }}</div>
          <div class="stat-label">采样/分钟</div>
        </div>
        <div class="stat">
          <div class="stat-value text-purple">{{ status.rulesActive }}</div>
          <div class="stat-label">活跃规则</div>
        </div>
        <div class="stat">
          <div class="stat-value text-yellow">{{ status.pendingPredictions }}</div>
          <div class="stat-label">待跟踪风险</div>
        </div>
        <div class="stat">
          <div class="stat-value text-green">{{ uptimeText }}</div>
          <div class="stat-label">连续运行</div>
        </div>
      </div>
    </div>

    <div class="agent-chat"><AgentLivePanel /></div>
    <div class="agent-risk"><AgentRiskPanel /></div>
    <div class="agent-rules"><AgentTriggersPanel /></div>
    <div class="agent-report"><AgentReportPanel /></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AgentLivePanel from '../panels/AgentLivePanel.vue'
import AgentRiskPanel from '../panels/AgentRiskPanel.vue'
import AgentTriggersPanel from '../panels/AgentTriggersPanel.vue'
import AgentReportPanel from '../panels/AgentReportPanel.vue'
import { buildAgentStatus } from '../../utils/agentMockData'

// 后端接入: GET /api/agent/status (轮询或 WS 推送)
const status = ref(buildAgentStatus())
let timer = null

const uptimeText = computed(() => {
  const sec = status.value.uptimeSec || 0
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  if (h) return `${h}h ${m}m`
  return `${m}m`
})

onMounted(() => {
  timer = setInterval(() => { status.value.uptimeSec += 1 }, 1000)
})
onUnmounted(() => { clearInterval(timer) })
</script>

<style scoped>
.agent-section {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  grid-template-rows: 64px minmax(0, 1.1fr) minmax(0, 1fr);
  gap: var(--gap);
  padding: var(--gap);
}

.agent-banner {
  grid-column: span 2;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 16px;
  border-radius: var(--border-radius);
  background:
    linear-gradient(120deg, rgba(124, 58, 237, 0.14), rgba(6, 182, 212, 0.08)),
    var(--bg-panel);
  border: 1px solid rgba(124, 58, 237, 0.25);
  box-shadow: var(--shadow-panel);
}
.banner-left { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.ai-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: linear-gradient(135deg, #7c3aed, #06b6d4);
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 16px rgba(124, 58, 237, 0.3);
}
.banner-meta { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.banner-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: 0.5px;
}
.banner-sub { font-size: 12px; color: var(--text-secondary); }

.banner-stats { display: flex; gap: 24px; flex-shrink: 0; }
.stat { text-align: right; }
.stat-value {
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
  font-family: 'Consolas', monospace;
}
.stat-label { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }
.text-cyan { color: var(--accent-cyan); }
.text-purple { color: #7c3aed; }
.text-yellow { color: var(--accent-yellow); }
.text-green { color: var(--accent-green); }

.agent-chat { grid-row: 2 / 3; grid-column: 1 / 2; }
.agent-risk { grid-row: 2 / 3; grid-column: 2 / 3; }
.agent-rules { grid-row: 3 / 4; grid-column: 1 / 2; }
.agent-report { grid-row: 3 / 4; grid-column: 2 / 3; }

.agent-chat,
.agent-risk,
.agent-rules,
.agent-report {
  min-width: 0;
  min-height: 0;
}
</style>
