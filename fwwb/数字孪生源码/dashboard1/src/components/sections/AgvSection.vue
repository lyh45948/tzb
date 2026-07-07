<template>
  <div class="section-page agv-section" ref="rootEl">
    <div class="agv-left" :style="{ width: leftWidth + 'px' }">
      <div class="agv-dispatch"><TaskDispatchPanel /></div>
      <div class="agv-queue"><TaskQueuePanel /></div>
    </div>

    <div
      class="resizer left-resizer"
      :class="{ active: dragging === 'left' }"
      @mousedown="startDrag('left', $event)"
      title="拖动调整宽度"
    ></div>

    <div class="agv-scene"><CarScene /></div>

    <div
      class="resizer right-resizer"
      :class="{ active: dragging === 'right' }"
      @mousedown="startDrag('right', $event)"
      title="拖动调整宽度"
    ></div>

    <div class="agv-right" :style="{ width: rightWidth + 'px' }">
      <div class="agv-status"><CarStatusPanel /></div>
      <div class="agv-control"><ControlPanel /></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import CarScene from '../three/CarScene.vue'
import CarStatusPanel from '../panels/CarStatusPanel.vue'
import ControlPanel from '../panels/ControlPanel.vue'
import TaskDispatchPanel from '../panels/TaskDispatchPanel.vue'
import TaskQueuePanel from '../panels/TaskQueuePanel.vue'

const STORAGE_KEY = 'agv-section-layout'
const rootEl = ref(null)
const leftWidth = ref(320)
const rightWidth = ref(320)
const dragging = ref(null) // 'left' | 'right' | null

// 还原上次保存的宽度
try {
  const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  if (saved.leftWidth) leftWidth.value = saved.leftWidth
  if (saved.rightWidth) rightWidth.value = saved.rightWidth
} catch {}

let dragStartX = 0
let dragStartWidth = 0

function startDrag(which, e) {
  dragging.value = which
  dragStartX = e.clientX
  dragStartWidth = which === 'left' ? leftWidth.value : rightWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', stopDrag)
}

function onMove(e) {
  if (!dragging.value || !rootEl.value) return
  const total = rootEl.value.clientWidth
  const dx = e.clientX - dragStartX
  // 中央 3D 场景至少 320px
  const minSide = 220
  const maxSide = Math.max(minSide, total * 0.6)
  if (dragging.value === 'left') {
    let w = dragStartWidth + dx
    const cap = total - rightWidth.value - 320
    leftWidth.value = Math.max(minSide, Math.min(Math.min(maxSide, cap), w))
  } else {
    let w = dragStartWidth - dx
    const cap = total - leftWidth.value - 320
    rightWidth.value = Math.max(minSide, Math.min(Math.min(maxSide, cap), w))
  }
}

function stopDrag() {
  if (!dragging.value) return
  dragging.value = null
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', stopDrag)
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      leftWidth: leftWidth.value,
      rightWidth: rightWidth.value
    }))
  } catch {}
}

onMounted(() => {
  // 首次按容器尺寸自适应:左 22%、右 22%
  if (rootEl.value) {
    const total = rootEl.value.clientWidth
    const saved = (() => {
      try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') } catch { return {} }
    })()
    if (!saved.leftWidth) leftWidth.value = Math.max(280, Math.min(420, total * 0.22))
    if (!saved.rightWidth) rightWidth.value = Math.max(280, Math.min(420, total * 0.22))
  }
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', stopDrag)
})
</script>

<style scoped>
.agv-section {
  display: flex;
  align-items: stretch;
  gap: 0;
  padding: var(--gap);
  height: 100%;
}

.agv-left,
.agv-right {
  display: flex;
  flex-direction: column;
  gap: var(--gap);
  flex-shrink: 0;
  min-width: 0;
  min-height: 0;
}

.agv-left .agv-dispatch { flex: 0 0 auto; }
.agv-left .agv-queue { flex: 1 1 auto; min-height: 0; }

.agv-right .agv-status { flex: 1 1 0; min-height: 0; }
.agv-right .agv-control { flex: 1.2 1 0; min-height: 0; }

.agv-scene {
  flex: 1 1 auto;
  min-width: 320px;
  min-height: 0;
}

/* 拖拽分隔条 */
.resizer {
  flex: 0 0 6px;
  margin: 0 1px;
  background: transparent;
  cursor: col-resize;
  position: relative;
  transition: background 0.15s;
}

.resizer::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 2px;
  height: 36px;
  background: var(--border-dim);
  border-radius: 1px;
  transition: background 0.15s;
}

.resizer:hover {
  background: rgba(30, 80, 180, 0.06);
}

.resizer:hover::before,
.resizer.active::before {
  background: var(--accent-blue);
  height: 60px;
  width: 3px;
}

.resizer.active {
  background: rgba(30, 80, 180, 0.08);
}
</style>
