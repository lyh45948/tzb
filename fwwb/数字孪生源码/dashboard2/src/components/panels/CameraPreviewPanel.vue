<template>
  <div class="panel-frame">
    <div class="panel-header">
      <span class="dot"></span>OpenMV 实时画面
      <span class="meta">{{ statusText }}</span>
    </div>
    <div class="panel-body cam-body">
      <div class="cam-stage">
        <!-- 后端 /v1/vision/frame.jpg 由 OpenMV GUI 推送，无帧时返回 204 -->
        <img v-if="frameUrl" :src="frameUrl" alt="OpenMV 实时画面" @load="onLoad" @error="onError" />
        <div v-if="!hasFrame" class="placeholder">
          {{ placeholderText }}
        </div>
      </div>

      <div class="cam-actions">
        <button
          class="btn start"
          :class="{ active: counterEnabled }"
          :disabled="busy || counterEnabled"
          @click="onStart"
        >▶ 开始计数</button>
        <button
          class="btn stop"
          :class="{ active: !counterEnabled }"
          :disabled="busy || !counterEnabled"
          @click="onStop"
        >⏹ 停止计数</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  getVisionFrameUrl,
  fetchCounterControl,
  setCounterControl,
} from '../../services/api'

// ─── 实时画面：用 <img> 轮询拉取 ───
// frame.jpg 加 ?t= 时间戳避免浏览器缓存；后端也返回了 no-store
const baseUrl = getVisionFrameUrl()
const frameUrl = ref('')
const hasFrame = ref(false)
const errorTick = ref(0)
let frameTimer = null

function refreshFrame() {
  // 8Hz 拉一次。OpenMV GUI 的预览是 ~20Hz，识别是 ~5Hz，8Hz 对前端足够流畅
  frameUrl.value = `${baseUrl}?t=${Date.now()}`
}

function onLoad() {
  hasFrame.value = true
  errorTick.value = 0
}
function onError() {
  // 204 / 503 时 <img> 会触发 error，连续失败认为没画面
  errorTick.value += 1
  if (errorTick.value >= 3) {
    hasFrame.value = false
  }
}

const placeholderText = computed(() => {
  if (counterEnabled.value) return '等待 OpenMV 推送画面...'
  return '点击「开始计数」启动 OpenMV 识别和画面推流'
})

// ─── 计数器识别开关：和后端 /v1/vision/counter/control 同步 ───
const counterEnabled = ref(false)
const busy = ref(false)
let pollTimer = null

const statusText = computed(() => (counterEnabled.value ? '识别中' : '已停止'))

async function pullStatus() {
  try {
    const data = await fetchCounterControl()
    counterEnabled.value = !!(data && data.enabled)
  } catch (_) {
    // 后端不通时按钮保持本地态
  }
}

async function onStart() {
  if (busy.value) return
  busy.value = true
  try {
    const data = await setCounterControl(true)
    counterEnabled.value = !!(data && data.enabled)
  } catch (e) {
    console.warn('[CameraPreviewPanel] 开始计数失败', e)
  } finally {
    busy.value = false
  }
}

async function onStop() {
  if (busy.value) return
  busy.value = true
  try {
    const data = await setCounterControl(false)
    counterEnabled.value = !!(data && data.enabled)
  } catch (e) {
    console.warn('[CameraPreviewPanel] 停止计数失败', e)
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  refreshFrame()
  frameTimer = setInterval(refreshFrame, 125)   // 8Hz
  pullStatus()
  pollTimer = setInterval(pullStatus, 2000)     // 0.5Hz 兜底，按钮态由 setCounterControl 即时更新
})

onUnmounted(() => {
  if (frameTimer) clearInterval(frameTimer)
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.panel-header .meta {
  margin-left: auto;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}
.cam-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}
.cam-stage {
  position: relative;
  flex: 1 1 auto;
  min-height: 160px;
  background: #0f172a;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cam-stage img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
.placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
  padding: 0 12px;
  pointer-events: none;
}
.cam-actions {
  display: flex;
  gap: 8px;
}
.btn {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.08);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn:hover:not(:disabled) {
  background: rgba(148, 163, 184, 0.18);
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn.start.active {
  background: rgba(34, 197, 94, 0.18);
  color: #16a34a;
  border-color: #22c55e;
}
.btn.stop.active {
  background: rgba(239, 68, 68, 0.14);
  color: #dc2626;
  border-color: #ef4444;
}
</style>
