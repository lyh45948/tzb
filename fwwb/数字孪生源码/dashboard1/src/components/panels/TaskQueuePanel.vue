<template>
  <div class="panel-frame">
    <div class="panel-header">
      <span class="dot"></span>任务队列
      <div class="header-actions">
        <span class="counter">
          <span class="badge bg-blue">运行 {{ runningCount }}</span>
          <span class="badge bg-gray">待执行 {{ pendingCount }}</span>
          <span class="badge bg-green">完成 {{ completedCount }}</span>
        </span>
        <button class="clear-btn" @click="store.clearCompletedTasks" :disabled="!completedCount">清理完成</button>
      </div>
    </div>
    <div class="panel-body queue-body">
      <div class="tabs">
        <button
          v-for="t in tabs"
          :key="t.value"
          :class="['tab', { active: activeTab === t.value }]"
          @click="activeTab = t.value"
        >{{ t.label }}<span class="tab-count">{{ countOf(t.value) }}</span></button>
      </div>

      <div v-if="filteredTasks.length" class="task-list">
        <div
          v-for="task in filteredTasks"
          :key="task.id"
          :class="['task-item', `is-${task.status}`]"
        >
          <div class="task-line top">
            <span class="task-id">{{ task.id }}</span>
            <span class="task-type" :style="{ color: typeColor(task.type) }">{{ typeLabel(task.type) }}</span>
            <span class="task-status" :style="{ color: statusColor(task.status) }">
              <span class="status-dot" :style="{ background: statusColor(task.status) }"></span>
              {{ statusLabel(task.status) }}
            </span>
            <span v-if="task.priority === 'high'" class="prio-tag">紧急</span>
            <span class="task-actions">
              <button v-if="canCancel(task)" class="mini-btn" @click="store.cancelTask(task.id)">取消</button>
            </span>
          </div>
          <div class="task-line mid">
            <span class="route">
              <span class="rt-from">{{ task.fromName }}</span>
              <span class="rt-arrow">→</span>
              <span class="rt-to">{{ task.toName }}</span>
            </span>
            <span class="robot">{{ robotName(task.robotId) || '待分配' }}</span>
          </div>
          <div class="task-line bar">
            <div class="progress">
              <div
                class="progress-fill"
                :style="{
                  width: progressPct(task) + '%',
                  background: statusColor(task.status)
                }"
              ></div>
            </div>
            <span class="progress-text">{{ progressPct(task) }}%</span>
          </div>
          <div class="task-line foot">
            <span>下发 {{ formatTime(task.createdAt) }}</span>
            <span v-if="task.startedAt">· 开始 {{ formatTime(task.startedAt) }}</span>
            <span v-if="task.completedAt">· {{ task.status === 'completed' ? '完成' : '结束' }} {{ formatTime(task.completedAt) }}</span>
            <span v-if="task.startedAt" class="dur">耗时 {{ formatDuration(task) }}</span>
          </div>
        </div>
      </div>
      <div v-else class="empty">暂无{{ activeTabLabel }}任务</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { TASK_STATUS_MAP, TASK_TYPES } from '../../utils/waypoints'

const store = useDeviceStore()

const tabs = [
  { value: 'all',       label: '全部' },
  { value: 'pending',   label: '待执行' },
  { value: 'running',   label: '执行中' },
  { value: 'completed', label: '已完成' }
]
const activeTab = ref('all')

const tasks = computed(() => store.tasks)

const runningCount = computed(() => tasks.value.filter(t => t.status === 'running').length)
const pendingCount = computed(() => tasks.value.filter(t => t.status === 'pending').length)
const completedCount = computed(() => tasks.value.filter(t => t.status === 'completed').length)

function countOf(val) {
  if (val === 'all') return tasks.value.length
  return tasks.value.filter(t => t.status === val).length
}

const filteredTasks = computed(() => {
  if (activeTab.value === 'all') {
    // 排序: running > pending > completed/cancelled,组内按时间倒序
    const order = { running: 0, pending: 1, completed: 2, cancelled: 3, failed: 2 }
    return [...tasks.value].sort((a, b) => {
      const oa = order[a.status] ?? 9
      const ob = order[b.status] ?? 9
      if (oa !== ob) return oa - ob
      return b.createdAt - a.createdAt
    })
  }
  return tasks.value.filter(t => t.status === activeTab.value)
})

const activeTabLabel = computed(() => tabs.find(t => t.value === activeTab.value)?.label || '')

function statusLabel(s) { return TASK_STATUS_MAP[s]?.label || s }
function statusColor(s) { return TASK_STATUS_MAP[s]?.color || '#94a3b8' }
function typeLabel(t) { return TASK_TYPES.find(x => x.value === t)?.label || t }
function typeColor(t) { return TASK_TYPES.find(x => x.value === t)?.color || '#64748b' }

function robotName(id) {
  if (!id) return ''
  return store.fleet.find(r => r.id === id)?.name || id
}

function canCancel(task) {
  return task.status === 'pending' || task.status === 'running'
}

function progressPct(task) {
  if (task.status === 'completed') return 100
  if (task.status === 'pending' || task.status === 'cancelled') return 0
  return Math.round((task.progress || 0) * 100)
}

function formatTime(ts) {
  if (!ts) return '--'
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

function formatDuration(task) {
  const end = task.completedAt || Date.now()
  const sec = Math.max(0, Math.round((end - task.startedAt) / 1000))
  if (sec < 60) return `${sec}s`
  return `${Math.floor(sec / 60)}m${sec % 60}s`
}
</script>

<style scoped>
.queue-body { display: flex; flex-direction: column; gap: 6px; height: 100%; min-height: 0; }
.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.counter { display: flex; gap: 4px; }
.badge {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 999px;
  letter-spacing: 0;
  color: #fff;
}
.bg-blue { background: var(--accent-blue); }
.bg-gray { background: #94a3b8; }
.bg-green { background: var(--accent-green); }

.clear-btn {
  background: transparent;
  border: 1px solid var(--border-dim);
  color: var(--text-secondary);
  padding: 1px 8px;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.clear-btn:hover:not(:disabled) { background: rgba(239, 68, 68, 0.1); color: var(--accent-red); border-color: rgba(239, 68, 68, 0.3); }
.clear-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.tabs { display: flex; gap: 3px; flex-shrink: 0; }
.tab {
  flex: 1;
  height: 26px;
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  border-radius: 3px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  transition: all 0.18s;
}
.tab:hover { background: rgba(30, 80, 180, 0.1); }
.tab.active {
  background: rgba(30, 80, 180, 0.12);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
  font-weight: 600;
}
.tab-count {
  font-size: 11px;
  background: rgba(0, 0, 0, 0.06);
  padding: 0 4px;
  border-radius: 6px;
  min-width: 14px;
}

.task-list { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.task-item {
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
.task-item:hover { background: rgba(30, 80, 180, 0.08); }
.task-item.is-running { border-left-color: var(--accent-blue); background: rgba(30, 80, 180, 0.06); }
.task-item.is-completed { border-left-color: var(--accent-green); opacity: 0.85; }
.task-item.is-cancelled,
.task-item.is-failed { border-left-color: var(--accent-red); opacity: 0.6; }

.task-line { display: flex; align-items: center; gap: 8px; }
.task-line.top { font-size: 13px; }
.task-id { font-weight: 700; color: var(--text-primary); font-family: 'Consolas', monospace; }
.task-type { font-weight: 600; }
.task-status { display: flex; align-items: center; gap: 4px; font-weight: 600; font-size: 12px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.prio-tag {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.task-actions { margin-left: auto; }
.mini-btn {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: var(--accent-red);
  padding: 1px 8px;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.mini-btn:hover { background: rgba(239, 68, 68, 0.1); }

.task-line.mid { font-size: 13px; }
.route { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.rt-from, .rt-to { color: var(--text-primary); font-weight: 600; overflow: hidden; text-overflow: ellipsis; }
.rt-arrow { color: var(--text-secondary); font-weight: 700; }
.robot { font-size: 12px; color: var(--accent-cyan); font-weight: 600; }

.task-line.bar { gap: 6px; }
.progress {
  flex: 1;
  height: 6px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 3px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.progress-text { font-size: 11px; color: var(--text-secondary); width: 36px; text-align: right; font-family: 'Consolas', monospace; }

.task-line.foot { font-size: 11px; color: var(--text-secondary); flex-wrap: wrap; gap: 4px; }
.task-line.foot .dur { margin-left: auto; color: var(--accent-blue); font-weight: 600; }

.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
