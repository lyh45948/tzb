<template>
  <!-- 智能体AI大屏: IofTV 风格 顶部状态条 + 三栏 (左实时 + 中风险/触发 + 右报告) -->
  <div class="section-page agent-section">
    <!-- 顶部智能体状态条 -->
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

    <div class="agent-grid">
      <!-- 左栏: 实时对话 (满高) -->
      <div class="col col-left">
        <ItemWrap title="智能体实时交互">
          <AgentLivePanel />
        </ItemWrap>
      </div>

      <!-- 中栏: 风险预测 + 触发规则 -->
      <div class="col col-center">
        <ItemWrap title="风险预测">
          <AgentRiskPanel />
        </ItemWrap>
        <ItemWrap title="触发规则">
          <AgentTriggersPanel />
        </ItemWrap>
      </div>

      <!-- 右栏: 评判报告 (满高) -->
      <div class="col col-right">
        <ItemWrap title="智能体评判报告">
          <AgentReportPanel />
        </ItemWrap>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import ItemWrap from '@/components/item-wrap/item-wrap.vue'
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
.section-page {
  width: 100%;
  height: 100%;
}
.agent-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 顶部状态条 (深色科技风) */
.agent-banner {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px;
  border-radius: 6px;
  background:
    linear-gradient(120deg, rgba(124, 58, 237, 0.18), rgba(6, 182, 212, 0.10)),
    rgba(7, 18, 40, 0.6);
  border: 1px solid rgba(49, 171, 227, 0.3);
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
  box-shadow: 0 4px 16px rgba(124, 58, 237, 0.4);
}
.banner-meta { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.banner-title {
  font-size: 16px;
  font-weight: 800;
  color: #e6f4ff;
  letter-spacing: 0.5px;
}
.banner-sub { font-size: 12px; color: #7fa6c8; }

.banner-stats { display: flex; gap: 24px; flex-shrink: 0; }
.stat { text-align: right; }
.stat-value {
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
  font-family: 'Consolas', monospace;
}
.stat-label { font-size: 11px; color: #7fa6c8; margin-top: 2px; }
.text-cyan { color: #06b6d4; }
.text-purple { color: #a78bfa; }
.text-yellow { color: #fbbf24; }
.text-green { color: #34d399; }

/* 三栏业务区 */
.agent-grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(0, 1fr) minmax(320px, 1fr);
  gap: 12px;
  min-height: 0;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.col > * {
  flex: 1;
  min-height: 0;
}
</style>
