<template>
  <!-- AGV 调度大屏: IofTV 风格 可拖拽三栏 (左任务 + 中3D场景 + 右状态/控制) -->
  <div class="section-page agv-section" ref="rootEl">
    <div class="agv-left" :style="{ width: leftWidth + 'px' }">
      <ItemWrap title="任务调度">
        <TaskDispatchPanel />
      </ItemWrap>
      <ItemWrap title="任务队列">
        <TaskQueuePanel />
      </ItemWrap>
    </div>

    <div
      class="resizer left-resizer"
      :class="{ active: dragging === 'left' }"
      @mousedown="startDrag('left', $event)"
      title="拖动调整宽度"
    ></div>

    <div class="agv-scene">
      <ItemWrap title="数字孪生调度实景">
        <div class="scene-host">
          <CarScene />
        </div>
      </ItemWrap>
    </div>

    <div
      class="resizer right-resizer"
      :class="{ active: dragging === 'right' }"
      @mousedown="startDrag('right', $event)"
      title="拖动调整宽度"
    ></div>

    <div class="agv-right" :style="{ width: rightWidth + 'px' }">
      <ItemWrap title="车辆状态">
        <CarStatusPanel />
      </ItemWrap>
      <ItemWrap title="设备控制">
        <ControlPanel />
      </ItemWrap>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import ItemWrap from '@/components/item-wrap/item-wrap.vue'
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
.section-page {
  width: 100%;
  height: 100%;
}
.agv-section {
  display: flex;
  align-items: stretch;
  gap: 0;
}

.agv-left,
.agv-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
  min-width: 0;
  min-height: 0;
}

/* 左右栏内 ItemWrap 按高度自适应分配 */
.agv-left > *,
.agv-right > * {
  flex: 1;
  min-height: 0;
}

.agv-scene {
  flex: 1 1 auto;
  min-width: 320px;
  min-height: 0;
  display: flex;
}
.agv-scene > * {
  flex: 1;
  min-height: 0;
}
.scene-host {
  width: 100%;
  height: 100%;
}

/* 拖拽分隔条 */
.resizer {
  flex: 0 0 6px;
  margin: 0 3px;
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
  background: rgba(49, 171, 227, 0.35);
  border-radius: 1px;
  transition: background 0.15s;
}

.resizer:hover {
  background: rgba(49, 171, 227, 0.08);
}

.resizer:hover::before,
.resizer.active::before {
  background: #31abe3;
  height: 60px;
  width: 3px;
}

.resizer.active {
  background: rgba(49, 171, 227, 0.12);
}
</style>
