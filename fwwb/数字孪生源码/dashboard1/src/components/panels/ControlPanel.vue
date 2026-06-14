<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>AGV详情与控制</div>
    <div class="panel-body control-body">
      <div class="vehicle-tabs">
        <button
          v-for="r in store.fleet"
          :key="r.id"
          :class="['vehicle-tab', { active: store.selectedRobotId === r.id }]"
          @click="store.selectedRobotId = r.id"
        >
          {{ r.name }}
        </button>
      </div>
      <div v-if="selected" class="vehicle-details">
        <div class="detail-row">
          <span class="label">状态</span>
          <span class="value" :style="{ color: statusColor }">{{ statusLabel }}</span>
        </div>
        <div class="detail-row">
          <span class="label">任务</span>
          <span class="value text-cyan">{{ taskLabel }}</span>
        </div>
        <div class="detail-row">
          <span class="label">运行模式</span>
          <span class="value text-blue">{{ modeLabel }}</span>
        </div>
        <div class="detail-row">
          <span class="label">电量</span>
          <span class="value" :style="{ color: batteryColor }">{{ Math.round(selected.battery) }}%</span>
        </div>
        <div class="detail-row">
          <span class="label">速度</span>
          <span class="value text-green">{{ selected.speed }} mm/s</span>
        </div>
        <div class="detail-row">
          <span class="label">左右轮速</span>
          <span class="value text-dim">{{ Math.round(selected.L_spd ?? 0) }} / {{ Math.round(selected.R_spd ?? 0) }} mm/s</span>
        </div>
        <div class="detail-row">
          <span class="label">安全距离</span>
          <span class="value" :style="{ color: distColor }">{{ Math.round(selected.distance) }} cm</span>
        </div>
        <div class="detail-row">
          <span class="label">位置</span>
          <span class="value text-dim">{{ formatNumber(selected.position?.x, 1) }}, {{ formatNumber(selected.position?.z, 1) }}</span>
        </div>
        <div class="detail-row" v-if="currentTask">
          <span class="label">当前任务</span>
          <span class="value text-cyan">
            {{ currentTask.id }} · {{ currentTask.fromName }}→{{ currentTask.toName }}
            <span class="task-pct">{{ Math.round((currentTask.progress || 0) * 100) }}%</span>
          </span>
        </div>

        <div class="manual-toggle">
          <span class="label">手动控制</span>
          <button
            :class="['toggle-btn', { active: isManualMode }]"
            @click="toggleManual"
          >
            {{ isManualMode ? '开启' : '关闭' }}
          </button>
        </div>

        <div v-if="isManualMode" class="dpad">
          <div class="dpad-cell dpad-empty"></div>
          <div class="dpad-cell">
            <button class="dpad-btn" @mousedown="startMove('forward')" @mouseup="stopMove" @mouseleave="stopMove">&#9650;</button>
          </div>
          <div class="dpad-cell dpad-empty"></div>
          <div class="dpad-cell">
            <button class="dpad-btn" @mousedown="startMove('left')" @mouseup="stopMove" @mouseleave="stopMove">&#9664;</button>
          </div>
          <div class="dpad-cell">
            <button class="dpad-btn dpad-stop" @mousedown="startMove('stop')" @mouseup="stopMove">&#9632;</button>
          </div>
          <div class="dpad-cell">
            <button class="dpad-btn" @mousedown="startMove('right')" @mouseup="stopMove" @mouseleave="stopMove">&#9654;</button>
          </div>
          <div class="dpad-cell dpad-empty"></div>
          <div class="dpad-cell">
            <button class="dpad-btn" @mousedown="startMove('back')" @mouseup="stopMove" @mouseleave="stopMove">&#9660;</button>
          </div>
          <div class="dpad-cell dpad-empty"></div>
        </div>
      </div>
      <div v-else class="no-data">暂无数据</div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { formatNumber, getBatteryColor } from '../../utils/dataFormatter'
import { ROBOT_STATUS_MAP, ROBOT_TASK_MAP } from '../../utils/constants'

const store = useDeviceStore()

watch(() => store.fleet, (fleet) => {
  if (fleet.length && store.selectedRobotId === null) {
    store.selectedRobotId = fleet[0].id
  }
}, { immediate: true })

watch(() => store.selectedRobotId, () => {
  store.moveRobot(null)
})

const selected = computed(() => store.fleet.find(r => r.id === store.selectedRobotId) || null)
const isManualMode = computed(() => !!(store.selectedRobotId && store.manualOverrides[store.selectedRobotId]))

function toggleManual() {
  if (!store.selectedRobotId) return
  store.setManualMode(store.selectedRobotId, !isManualMode.value)
}

function startMove(direction) {
  store.moveRobot(direction)
}

function stopMove() {
  store.moveRobot('stop')
}

const statusLabel = computed(() => ROBOT_STATUS_MAP[selected.value?.status]?.label || selected.value?.status || '--')
const statusColor = computed(() => ROBOT_STATUS_MAP[selected.value?.status]?.color || '#94a3b8')
const taskLabel = computed(() => ROBOT_TASK_MAP[selected.value?.task]?.label || selected.value?.task || '--')
const batteryColor = computed(() => getBatteryColor(selected.value?.battery ?? 0))

const modeLabel = computed(() => {
  const map = { manual: '手动', avoid: '避障', line: '巡线', path: '路径' }
  return map[selected.value?.carMode || selected.value?.mode] || '--'
})

const distColor = computed(() => {
  const d = selected.value?.distance ?? 999
  if (d <= 15) return '#ef4444'
  if (d <= 30) return '#f59e0b'
  return '#22c55e'
})

const currentTask = computed(() => {
  if (!selected.value) return null
  return store.tasks.find(t => t.status === 'running' && t.robotId === selected.value.id) || null
})
</script>

<style scoped>
.control-body { display: flex; flex-direction: column; gap: 8px; }
.vehicle-tabs { display: flex; gap: 3px; flex-wrap: wrap; }
.vehicle-tab {
  background: rgba(30,80,180,0.06);
  border: 1px solid var(--border-dim);
  color: var(--text-secondary);
  padding: 3px 8px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.vehicle-tab.active {
  background: rgba(30,80,180,0.15);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}
.vehicle-tab:hover { background: rgba(30,80,180,0.12); }
.vehicle-details { display: flex; flex-direction: column; gap: 4px; }
.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
  border-bottom: 1px solid rgba(30,80,180,0.06);
}
.label { color: var(--text-secondary); font-size: 13px; }
.value { font-size: 14px; font-weight: 600; }
.text-cyan { color: #06b6d4; }
.text-green { color: #22c55e; }
.text-dim { color: #94a3b8; }
.task-pct { margin-left: 4px; font-size: 12px; color: var(--accent-blue); font-weight: 700; }
.no-data { color: var(--text-secondary); font-size: 14px; text-align: center; padding: 10px; }

.manual-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 6px;
  margin-top: 4px;
  border-top: 1px solid rgba(30,80,180,0.12);
}
.toggle-btn {
  background: rgba(30,80,180,0.06);
  border: 1px solid var(--border-dim);
  color: var(--text-secondary);
  padding: 3px 12px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.toggle-btn.active {
  background: rgba(30,80,180,0.15);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}
.toggle-btn:hover { background: rgba(30,80,180,0.12); }

.dpad {
  display: grid;
  grid-template-columns: repeat(3, 42px);
  grid-template-rows: repeat(3, 42px);
  gap: 2px;
  justify-content: center;
  margin-top: 6px;
}
.dpad-cell {
  display: flex;
  align-items: center;
  justify-content: center;
}
.dpad-btn {
  width: 42px;
  height: 42px;
  background: rgba(30,80,180,0.08);
  border: 1px solid rgba(30,80,180,0.2);
  color: var(--accent-blue);
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  user-select: none;
}
.dpad-btn:hover { background: rgba(30,80,180,0.18); }
.dpad-btn:active {
  background: rgba(30,80,180,0.3);
  border-color: var(--accent-blue);
}
.dpad-stop {
  font-size: 13px;
  color: #ef4444;
  border-color: rgba(239,68,68,0.3);
}
.dpad-stop:hover { background: rgba(239,68,68,0.15); }
</style>
