<template>
  <div class="panel-frame">
    <div class="panel-header">
      <span class="dot"></span>风扇控制
      <span class="mode-tag" :class="{ manual: !auto }">{{ auto ? '自动' : '手动' }}</span>
      <span
        v-if="overrideRemaining > 0"
        class="override-tag"
        :title="`后端联动静默 ${overrideRemaining}s 后恢复自动`"
      >覆盖 {{ overrideRemaining }}s</span>
    </div>
    <div class="panel-body fan-body">
      <!-- 上：风扇视觉 + 当前转速 -->
      <div class="fan-visual">
        <div class="fan-icon" :style="fanStyle">
          <div class="fan-blade b1"></div>
          <div class="fan-blade b2"></div>
          <div class="fan-blade b3"></div>
          <div class="fan-blade b4"></div>
          <div class="fan-hub"></div>
        </div>
        <div class="fan-meta">
          <div class="rpm-row">
            <span class="rpm-num">{{ rpm }}</span>
            <span class="rpm-unit">RPM</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">温度</span>
            <span class="meta-val" :style="{ color: tempColor }">
              {{ formatNumber(store.temperature) }}<span class="unit">℃</span>
            </span>
          </div>
          <div class="meta-row">
            <span class="meta-label">档位</span>
            <span class="meta-val">{{ levelLabel }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">硬件</span>
            <span class="meta-val" :class="hwOn ? 'on' : 'off'">
              {{ hwOn ? '运转中' : '已停止' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 中：模式切换 + 手动档位 -->
      <div class="row mode-row">
        <button
          class="mini-btn"
          :class="{ active: auto }"
          :disabled="busy"
          @click="setAuto(true)"
        >自动</button>
        <button
          class="mini-btn"
          :class="{ active: !auto }"
          :disabled="busy"
          @click="setAuto(false)"
        >手动</button>
        <div class="manual-gear" v-if="!auto">
          <button
            v-for="g in 4"
            :key="g"
            class="gear-btn"
            :class="{ active: manualGear === g - 1 }"
            :disabled="busy"
            @click="onManualGear(g - 1)"
          >{{ g - 1 }}</button>
        </div>
      </div>

      <!-- 下：阈值设置 -->
      <div class="thresh-block">
        <div class="thresh-title-row">
          <span class="thresh-title">温度阈值（℃）</span>
          <span v-if="syncStatus" class="sync-tag" :class="syncStatus.cls">{{ syncStatus.text }}</span>
        </div>
        <div class="thresh-grid">
          <label class="thresh-cell">
            <span class="t-label">低速</span>
            <input
              type="number"
              v-model.number="thr.low"
              :min="0"
              :max="60"
              :step="0.5"
              @change="onThresholdChange"
            />
          </label>
          <label class="thresh-cell">
            <span class="t-label">中速</span>
            <input
              type="number"
              v-model.number="thr.mid"
              :min="0"
              :max="60"
              :step="0.5"
              @change="onThresholdChange"
            />
          </label>
          <label class="thresh-cell">
            <span class="t-label">高速</span>
            <input
              type="number"
              v-model.number="thr.high"
              :min="0"
              :max="60"
              :step="0.5"
              @change="onThresholdChange"
            />
          </label>
        </div>
        <div class="thresh-tip">
          T &lt; {{ thr.low }} 停 ▸ {{ thr.low }}–{{ thr.mid }} 低速 ▸ {{ thr.mid }}–{{ thr.high }} 中速 ▸ ≥ {{ thr.high }} 高速
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, onUnmounted } from 'vue'
import { useDeviceStore } from '../../stores/deviceStore'
import { formatNumber } from '../../utils/dataFormatter'
import {
  fetchLinkageConfig,
  updateLinkageConfig,
  setFanManual,
  ApiError,
} from '../../services/api'

const store = useDeviceStore()

const STORAGE_KEY = 'dashboard.fanThresholds'
const DEFAULT_THR = { low: 26, mid: 30, high: 34 }
// 四档对应的转速 (RPM)：0=停 / 1=低 / 2=中 / 3=高
const RPM_TABLE = [0, 600, 1200, 1800]
const LEVEL_NAMES = ['停止', '低速', '中速', '高速']

// 阈值（持久化到 localStorage，刷新不丢；后端可用时以后端为准）
const thr = reactive({ ...DEFAULT_THR })
function loadLocal() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const obj = JSON.parse(raw)
    if (obj && typeof obj === 'object') {
      if (Number.isFinite(obj.low)) thr.low = obj.low
      if (Number.isFinite(obj.mid)) thr.mid = obj.mid
      if (Number.isFinite(obj.high)) thr.high = obj.high
    }
  } catch (_) { /* ignore */ }
}
function saveLocal() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ low: thr.low, mid: thr.mid, high: thr.high }))
  } catch (_) { /* ignore */ }
}

// 同步状态：null | { cls, text }
const syncStatus = ref(null)
function setSync(cls, text, autoClearMs = 1800) {
  syncStatus.value = { cls, text }
  if (autoClearMs > 0) {
    setTimeout(() => {
      if (syncStatus.value && syncStatus.value.text === text) syncStatus.value = null
    }, autoClearMs)
  }
}

// 模式：true=自动按温度调速；false=手动指定档位
const auto = ref(true)
const manualGear = ref(0)
const busy = ref(false)

function clampThresholds() {
  if (!Number.isFinite(thr.low)) thr.low = DEFAULT_THR.low
  if (!Number.isFinite(thr.mid)) thr.mid = DEFAULT_THR.mid
  if (!Number.isFinite(thr.high)) thr.high = DEFAULT_THR.high
  if (thr.mid <= thr.low) thr.mid = thr.low + 1
  if (thr.high <= thr.mid) thr.high = thr.mid + 1
}

// 从后端拉一次现行阈值，覆盖本地。后端字段 fanTempOn/fanTempOff（带回滞），
// 这里用 fanTempOn 作为「中速」起点；低速 = fanTempOn - 4，高速 = fanTempOn + 4 作为可视化分档。
// 用户改动会回写 fanTempOn = mid，fanTempOff = mid - 2 保持回滞。
async function pullFromBackend() {
  try {
    const data = await fetchLinkageConfig()
    if (data && Number.isFinite(data.fanTempOn)) {
      const on = Number(data.fanTempOn)
      thr.mid = on
      // low/high 优先用 localStorage 里的值，没冲突就保留；否则按 ±4 默认
      const local = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
      thr.low = (local && Number.isFinite(local.low) && local.low < on) ? local.low : Math.max(0, on - 4)
      thr.high = (local && Number.isFinite(local.high) && local.high > on) ? local.high : on + 4
      clampThresholds()
      saveLocal()
      setSync('ok', '已同步')
    }
  } catch (e) {
    // 后端未就绪 / 503 — 静默使用本地值，标个离线
    if (e instanceof ApiError && e.status === 503) {
      setSync('warn', '后端未启用')
    } else {
      // 其他错误也不打断 UI
      console.warn('[FanPanel] 拉取阈值失败：', e)
    }
  }
}

// 推送阈值到后端（debounce）。中速→fanTempOn；fanTempOff = max(0, fanTempOn - 2) 保持回滞。
let pushTimer = null
function schedulePush() {
  clearTimeout(pushTimer)
  pushTimer = setTimeout(async () => {
    const fanTempOn = Number(thr.mid)
    if (!Number.isFinite(fanTempOn)) return
    const fanTempOff = Math.max(0, fanTempOn - 2)
    try {
      busy.value = true
      await updateLinkageConfig({ fanTempOn, fanTempOff })
      setSync('ok', '已保存')
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        setSync('warn', '后端未启用', 2400)
      } else {
        setSync('err', '保存失败', 2400)
      }
    } finally {
      busy.value = false
    }
  }, 350)
}

function onThresholdChange() {
  clampThresholds()
  saveLocal()
  schedulePush()
}

async function setAuto(v) {
  if (busy.value) return
  const target = !!v
  if (target === auto.value) return
  auto.value = target
  if (target) {
    // 切回自动 = 手动覆盖 ttl 设为 0 让后端立即恢复联动
    try {
      busy.value = true
      // 用现状重新对齐：让后端不再被手动锁住 → 把 ttl 改 1，等于近似立刻失效
      await setFanManual({ fan: store.fan ? 1 : 0, ttl: 1 })
      setSync('ok', '恢复自动')
    } catch (_) {
      setSync('warn', '后端未启用', 2400)
    } finally {
      busy.value = false
    }
  }
}

async function onManualGear(g) {
  if (busy.value) return
  manualGear.value = g
  // 0 → fan=0；>=1 → fan=1（硬件单 bit，档位仅前端可视化）
  try {
    busy.value = true
    await setFanManual({ gear: g, ttl: 60 })
    setSync('ok', `已下发 档位${g}`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 503) {
      setSync('warn', '后端未启用', 2400)
    } else {
      setSync('err', '下发失败', 2400)
    }
  } finally {
    busy.value = false
  }
}

// 自动档位：根据温度落在阈值区间
const autoGear = computed(() => {
  const t = Number(store.temperature)
  if (!Number.isFinite(t)) return 0
  if (t >= thr.high) return 3
  if (t >= thr.mid) return 2
  if (t >= thr.low) return 1
  return 0
})

const gear = computed(() => (auto.value ? autoGear.value : manualGear.value))
const rpm = computed(() => RPM_TABLE[gear.value] || 0)
const levelLabel = computed(() => LEVEL_NAMES[gear.value] || '停止')

// 硬件实际状态来自 SSE snapshot：linkage.fan 优先，回退顶层 store.fan
const hwOn = computed(() => {
  const lf = store.linkage?.fan
  if (lf != null) return !!lf
  return !!store.fan
})

// 后端「手动覆盖剩余秒」也由 SSE snapshot 推送，自动倒计时
const overrideRemaining = computed(() => {
  const v = store.linkage?.manualOverrideRemaining?.fan
  return Number.isFinite(v) ? v : 0
})

const tempColor = computed(() => {
  const t = Number(store.temperature)
  if (!Number.isFinite(t)) return '#94a3b8'
  if (t >= thr.high) return '#ef4444'
  if (t >= thr.mid) return '#f97316'
  if (t >= thr.low) return '#3b82f6'
  return '#22c55e'
})

const fanStyle = computed(() => {
  // 动画速度看「档位」，而硬件未运转时强制停转（避免后端 fan=0 但前端转着）
  if (!hwOn.value && auto.value) {
    return { animation: 'none', '--blade-color': '#94a3b8' }
  }
  const r = rpm.value
  if (!r) return { animation: 'none', '--blade-color': '#94a3b8' }
  const dur = Math.max(0.18, 60 / r)
  const colors = ['#94a3b8', '#22c55e', '#f97316', '#ef4444']
  return {
    animation: `fan-spin ${dur.toFixed(2)}s linear infinite`,
    '--blade-color': colors[gear.value] || '#22c55e',
  }
})

onMounted(async () => {
  loadLocal()
  await pullFromBackend()
})

onUnmounted(() => {
  clearTimeout(pushTimer)
})
</script>

<style scoped>
.fan-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 100%;
  min-height: 0;
}

.mode-tag {
  margin-left: auto;
  padding: 1px 7px;
  font-size: 11px;
  border-radius: 3px;
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}
.mode-tag.manual { background: rgba(245, 158, 11, 0.18); color: #f59e0b; }
.override-tag {
  margin-left: 6px;
  padding: 1px 7px;
  font-size: 11px;
  border-radius: 3px;
  background: rgba(245, 158, 11, 0.18);
  color: #f59e0b;
}

.fan-visual {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 4px;
  background: rgba(0,0,0,0.04);
  border-radius: 6px;
}
.fan-icon {
  position: relative;
  width: 76px;
  height: 76px;
  flex-shrink: 0;
  border-radius: 50%;
  background: radial-gradient(circle at center, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0.05) 70%);
  border: 1px solid rgba(148, 163, 184, 0.4);
  --blade-color: #94a3b8;
}
.fan-blade {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 32px;
  margin-left: -6px;
  margin-top: -32px;
  background: var(--blade-color);
  border-radius: 6px 6px 12px 12px;
  transform-origin: bottom center;
  opacity: 0.85;
}
.fan-blade.b1 { transform: rotate(0deg); }
.fan-blade.b2 { transform: rotate(90deg); }
.fan-blade.b3 { transform: rotate(180deg); }
.fan-blade.b4 { transform: rotate(270deg); }
.fan-hub {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 14px;
  height: 14px;
  margin-left: -7px;
  margin-top: -7px;
  background: #475569;
  border-radius: 50%;
  z-index: 1;
}
@keyframes fan-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.fan-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.rpm-row { display: flex; align-items: baseline; gap: 4px; }
.rpm-num { font-size: 26px; font-weight: 700; color: #0ea5e9; line-height: 1; }
.rpm-unit { font-size: 12px; color: var(--text-secondary); }
.meta-row { display: flex; justify-content: space-between; font-size: 12px; }
.meta-label { color: var(--text-secondary); }
.meta-val { font-weight: 600; }
.meta-val .unit { font-size: 11px; color: var(--text-secondary); margin-left: 2px; }
.meta-val.on { color: #22c55e; }
.meta-val.off { color: #94a3b8; }

.row { display: flex; gap: 6px; align-items: center; }
.mini-btn {
  flex: 0 0 auto;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 4px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.mini-btn:hover:not(:disabled) { background: rgba(14, 165, 233, 0.08); }
.mini-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.mini-btn.active {
  background: #0ea5e9;
  border-color: #0ea5e9;
  color: #fff;
}
.manual-gear { display: flex; gap: 4px; margin-left: 8px; }
.gear-btn {
  width: 28px;
  height: 24px;
  font-size: 12px;
  border-radius: 4px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}
.gear-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.gear-btn.active {
  background: #f97316;
  border-color: #f97316;
  color: #fff;
}

.thresh-block { display: flex; flex-direction: column; gap: 4px; }
.thresh-title-row { display: flex; justify-content: space-between; align-items: center; }
.thresh-title { font-size: 12px; color: var(--text-secondary); }
.sync-tag {
  padding: 1px 6px;
  font-size: 10px;
  border-radius: 3px;
  font-weight: 500;
}
.sync-tag.ok   { background: rgba(34, 197, 94, 0.18); color: #22c55e; }
.sync-tag.warn { background: rgba(245, 158, 11, 0.18); color: #f59e0b; }
.sync-tag.err  { background: rgba(239, 68, 68, 0.18); color: #ef4444; }
.thresh-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 6px;
}
.thresh-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.t-label { font-size: 11px; color: var(--text-secondary); }
.thresh-cell input {
  width: 100%;
  padding: 4px 6px;
  font-size: 13px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 4px;
  background: rgba(255,255,255,0.04);
  color: var(--text-primary, #1e293b);
}
.thresh-cell input:focus {
  outline: none;
  border-color: #0ea5e9;
  background: rgba(14, 165, 233, 0.05);
}
.thresh-tip { font-size: 11px; color: var(--text-secondary); line-height: 1.4; }
</style>
