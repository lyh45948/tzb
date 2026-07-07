<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>任务下发</div>
    <div class="panel-body dispatch-body">
      <div class="form-grid">
        <div class="form-row">
          <span class="label">任务类型</span>
          <select v-model="form.type" class="ctrl">
            <option v-for="t in taskTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div class="form-row">
          <span class="label">起点</span>
          <select v-model="form.fromId" class="ctrl">
            <option v-for="w in waypoints" :key="'f'+w.id" :value="w.id">{{ w.id }} · {{ w.name }}</option>
          </select>
        </div>
        <div class="form-row">
          <span class="label">终点</span>
          <select v-model="form.toId" class="ctrl">
            <option v-for="w in waypoints" :key="'t'+w.id" :value="w.id" :disabled="w.id === form.fromId">
              {{ w.id }} · {{ w.name }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <span class="label">指定AGV</span>
          <select v-model="form.robotId" class="ctrl">
            <option :value="null">自动分配</option>
            <option v-for="r in store.fleet" :key="r.id" :value="r.id">{{ r.name }}</option>
          </select>
        </div>
        <div class="form-row">
          <span class="label">优先级</span>
          <div class="priority-group">
            <button
              v-for="p in priorities"
              :key="p.value"
              :class="['prio-btn', { active: form.priority === p.value }]"
              :style="form.priority === p.value ? { borderColor: p.color, color: p.color } : {}"
              @click="form.priority = p.value"
            >{{ p.label }}</button>
          </div>
        </div>
      </div>

      <div class="dispatch-summary">
        <span class="path-pill" :style="{ background: fromColor + '22', color: fromColor }">{{ fromName }}</span>
        <span class="arrow">→</span>
        <span class="path-pill" :style="{ background: toColor + '22', color: toColor }">{{ toName }}</span>
        <span class="dist">约 {{ formatNumber(distance, 1) }} m</span>
      </div>

      <button class="dispatch-btn" :disabled="!canDispatch" @click="onDispatch">下发任务</button>

      <div class="hint" v-if="lastDispatched">
        已下发任务 <strong>{{ lastDispatched.id }}</strong>:{{ lastDispatched.fromName }} → {{ lastDispatched.toName }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, ref } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { FACTORY_WAYPOINTS, TASK_TYPES, TASK_PRIORITY_MAP } from '../../utils/waypoints'
import { formatNumber } from '../../utils/dataFormatter'

const store = useDeviceStore()

const waypoints = FACTORY_WAYPOINTS
const taskTypes = TASK_TYPES
const priorities = Object.entries(TASK_PRIORITY_MAP).map(([value, p]) => ({ value, ...p }))

const form = reactive({
  type: 'transport',
  fromId: 'WH-A',
  toId: 'PACK',
  robotId: null,
  priority: 'normal'
})

const lastDispatched = ref(null)

const fromWp = computed(() => waypoints.find(w => w.id === form.fromId))
const toWp = computed(() => waypoints.find(w => w.id === form.toId))
const fromName = computed(() => fromWp.value?.name || '--')
const toName = computed(() => toWp.value?.name || '--')
const fromColor = computed(() => fromWp.value?.color || '#64748b')
const toColor = computed(() => toWp.value?.color || '#64748b')
const distance = computed(() => {
  if (!fromWp.value || !toWp.value) return 0
  return Math.hypot(fromWp.value.x - toWp.value.x, fromWp.value.z - toWp.value.z)
})
const canDispatch = computed(() => form.fromId && form.toId && form.fromId !== form.toId)

function onDispatch() {
  const task = store.dispatchTask({ ...form })
  if (task) lastDispatched.value = task
}
</script>

<style scoped>
.dispatch-body { display: flex; flex-direction: column; gap: 8px; }
.form-grid { display: flex; flex-direction: column; gap: 6px; }
.form-row { display: flex; align-items: center; gap: 8px; }
.label { color: var(--text-secondary); font-size: 13px; width: 64px; flex-shrink: 0; }
.ctrl {
  flex: 1;
  height: 28px;
  background: rgba(30, 80, 180, 0.04);
  border: 1px solid var(--border-dim);
  border-radius: 3px;
  padding: 0 6px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
}
.ctrl:focus { border-color: var(--accent-blue); }

.priority-group { flex: 1; display: flex; gap: 4px; }
.prio-btn {
  flex: 1;
  height: 28px;
  border: 1px solid var(--border-dim);
  background: rgba(30, 80, 180, 0.04);
  border-radius: 3px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.18s;
}
.prio-btn:hover { background: rgba(30, 80, 180, 0.1); }
.prio-btn.active { background: rgba(30, 80, 180, 0.1); font-weight: 600; }

.dispatch-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: rgba(30, 80, 180, 0.05);
  border-radius: 3px;
  flex-wrap: wrap;
}
.path-pill { padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.arrow { color: var(--text-secondary); font-weight: 700; }
.dist { margin-left: auto; color: var(--text-secondary); font-size: 12px; }

.dispatch-btn {
  height: 32px;
  background: linear-gradient(90deg, #2563eb, #06b6d4);
  border: none;
  border-radius: 3px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  letter-spacing: 1px;
  transition: opacity 0.15s, transform 0.05s;
}
.dispatch-btn:hover:not(:disabled) { opacity: 0.92; }
.dispatch-btn:active:not(:disabled) { transform: translateY(1px); }
.dispatch-btn:disabled { background: #cbd5e1; cursor: not-allowed; }

.hint {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 4px 6px;
  background: rgba(34, 197, 94, 0.08);
  border-radius: 3px;
  border-left: 2px solid var(--accent-green);
}
.hint strong { color: var(--accent-green); }
</style>
