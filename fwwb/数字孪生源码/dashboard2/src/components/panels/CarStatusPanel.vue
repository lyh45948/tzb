<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>AGV与巡检设备状态</div>
    <div class="panel-body status-body">
      <div class="fleet-header">
        <div class="fleet-stat">
          <span class="stat-label">在线</span>
          <span class="stat-value text-green">{{ onlineCount }}</span>
        </div>
        <div class="fleet-stat">
          <span class="stat-label">运行中</span>
          <span class="stat-value text-cyan">{{ runningCount }}</span>
        </div>
        <div class="fleet-stat">
          <span class="stat-label">告警</span>
          <span class="stat-value text-red">{{ alarmCount }}</span>
        </div>
      </div>
      <div class="robot-list">
        <div
          class="robot-item"
          :class="{ active: store.selectedRobotId === robot.id }"
          v-for="robot in store.fleet"
          :key="robot.id"
          @click="store.selectedRobotId = robot.id"
        >
          <div class="robot-name">
            <span class="robot-dot" :style="{ background: statusColor(robot.status) }"></span>
            {{ robot.name }}
          </div>
          <div class="robot-info">
            <span class="robot-task">{{ taskLabel(robot.task) }}</span>
            <span class="robot-status" :style="{ color: statusColor(robot.status) }">{{ statusLabel(robot.status) }}</span>
            <span class="robot-battery">{{ Math.round(robot.battery) }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { ROBOT_STATUS_MAP, ROBOT_TASK_MAP } from '../../utils/constants'

const store = useDeviceStore()

const onlineCount = computed(() => store.fleet.filter(r => r.status !== 'offline').length)
const runningCount = computed(() => store.fleet.filter(r => !['idle', 'charging', 'offline'].includes(r.status)).length)
const alarmCount = computed(() => store.fleet.filter(r => ['warning', 'danger', 'critical'].includes(r.alertLevel) || r.status === 'warning').length + store.alarmEvents.length)

function statusLabel(s) { return ROBOT_STATUS_MAP[s]?.label || '未知' }
function statusColor(s) { return ROBOT_STATUS_MAP[s]?.color || '#94a3b8' }
function taskLabel(t) { return ROBOT_TASK_MAP[t]?.label || t || '--' }
</script>

<style scoped>
.status-body { display: flex; flex-direction: column; gap: 8px; }
.fleet-header { display: flex; gap: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(30,80,180,0.1); }
.fleet-stat { display: flex; flex-direction: column; align-items: center; flex: 1; }
.stat-label { color: var(--text-secondary); font-size: 13px; }
.stat-value { font-size: 22px; font-weight: 700; }
.robot-list { display: flex; flex-direction: column; gap: 6px; }
.robot-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 6px; background: rgba(0,0,0,0.04); border-radius: 3px; cursor: pointer; transition: background 0.2s, border-color 0.2s; border: 1px solid transparent; gap: 8px; }
.robot-item:hover { background: rgba(30,80,180,0.08); }
.robot-item.active { background: rgba(30,80,180,0.12); border-color: var(--accent-blue); }
.robot-name { display: flex; align-items: center; gap: 6px; font-size: 14px; min-width: 72px; }
.robot-dot { width: 6px; height: 6px; border-radius: 50%; }
.robot-info { display: flex; gap: 8px; font-size: 12px; align-items: center; min-width: 0; }
.robot-task { color: var(--text-secondary); white-space: nowrap; }
.robot-status { font-weight: 600; white-space: nowrap; }
.robot-battery { color: var(--text-secondary); }
</style>
