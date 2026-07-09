<template>
  <div ref="container" class="car-scene"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import { useDeviceStore } from '../../stores/deviceStore'
import config from '../../config'
import { CarModel } from './CarModel'
import { SceneEnvironment } from './SceneEnvironment'
import { AnimationController } from './AnimationController'
import { ROBOT_STATUS_MAP } from '../../utils/constants'
import { FACTORY_WAYPOINTS } from '../../utils/waypoints'

const container = ref(null)
const store = useDeviceStore()

let renderer, scene, camera, controls
let labelRenderer
let carModels = []
let labelObjects = [] // { css2d: CSS2DObject, nameEl, dotEl, statusEl }
let sceneEnv, animController
let raycaster, pointer
let resizeObserver = null
let _initialized = false  // 标记 Three.js 是否已成功初始化

// Pointer tracking for drag-vs-click detection
let pointerDownPos = null

function init() {
  const el = container.value
  if (!el) return

  const w = el.clientWidth
  const h = el.clientHeight
  if (!w || !h) {
    // 容器尺寸为 0（Transition 动画中或弹性布局未就绪），等待 ResizeObserver 重试
    return
  }

  // 避免重复初始化
  if (_initialized) return

  // Raycaster for click detection
  raycaster = new THREE.Raycaster()
  pointer = new THREE.Vector2()

  // WebGL Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 0.8
  el.appendChild(renderer.domElement)

  // CSS2D Renderer for floating labels
  labelRenderer = new CSS2DRenderer()
  labelRenderer.setSize(w, h)
  labelRenderer.domElement.style.position = 'absolute'
  labelRenderer.domElement.style.top = '0'
  labelRenderer.domElement.style.left = '0'
  labelRenderer.domElement.style.pointerEvents = 'none'
  labelRenderer.domElement.style.borderRadius = 'var(--radius, 6px)'
  labelRenderer.domElement.style.overflow = 'hidden'
  el.appendChild(labelRenderer.domElement)

  // Pointer events: use pointerdown/pointerup pair to avoid drag-triggered selection
  renderer.domElement.addEventListener('pointerdown', onPointerDown)
  renderer.domElement.addEventListener('pointerup', onPointerUp)

  // Scene
  scene = new THREE.Scene()

  // Camera
  camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 100)
  camera.position.set(0, 14, 16)
  camera.lookAt(0, 0, 0)

  // OrbitControls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = false
  controls.minDistance = 5
  controls.maxDistance = 35
  controls.maxPolarAngle = Math.PI / 2.1
  controls.minPolarAngle = 0.2
  controls.target.set(0, 0, 0)

  // Environment
  sceneEnv = new SceneEnvironment(scene)

  // Create factory AGVs with task-specific modules
  const robotTypes = ['obstacleAvoidance', 'patrol', 'goodsCount', 'gasMonitor']
  config.robotColors.forEach((color, i) => {
    const type = robotTypes[i] || 'patrol'
    const car = new CarModel(scene, color, type)
    car.group.userData.robotId = 'robot_' + (i + 1)
    // Spread initial positions
    car.setPosition(-3 + i * 2, -3 + i * 1.5)
    carModels.push(car)

    // Create floating label
    _createLabel(car, i)
  })

  // Animation controller
  animController = new AnimationController(carModels, sceneEnv)

  // Waypoint labels (CSS2D, anchored on scene markers)
  _createWaypointLabels()

  // Start render loop — Three.js setAnimationLoop 会在标签页隐藏时自动暂停，
  // 避免后台持续渲染消耗 CPU
  renderer.setAnimationLoop(animate)
  _initialized = true
}

function _createWaypointLabels() {
  FACTORY_WAYPOINTS.forEach(wp => {
    const wrapper = document.createElement('div')
    wrapper.className = 'waypoint-label'
    wrapper.style.borderColor = wp.color
    wrapper.style.color = wp.color

    const idEl = document.createElement('span')
    idEl.className = 'wp-id'
    idEl.textContent = wp.id
    idEl.style.background = wp.color

    const nameEl = document.createElement('span')
    nameEl.className = 'wp-name'
    nameEl.textContent = wp.name

    wrapper.appendChild(idEl)
    wrapper.appendChild(nameEl)

    const obj = new CSS2DObject(wrapper)
    obj.position.set(wp.x, 1.25, wp.z)
    scene.add(obj)
  })
}

function _createLabel(car, index) {
  const name = config.robotNames[index] || `机器人-${index + 1}`

  const wrapper = document.createElement('div')
  wrapper.className = 'robot-label'

  const nameEl = document.createElement('span')
  nameEl.className = 'robot-label__name'
  nameEl.textContent = name

  const dotEl = document.createElement('span')
  dotEl.className = 'robot-label__dot'

  const statusEl = document.createElement('span')
  statusEl.className = 'robot-label__status'
  statusEl.textContent = '待机'

  wrapper.appendChild(nameEl)
  wrapper.appendChild(dotEl)
  wrapper.appendChild(statusEl)

  const css2dObj = new CSS2DObject(wrapper)
  css2dObj.position.set(0, 1.0, 0)
  car.group.add(css2dObj)

  labelObjects.push({ css2d: css2dObj, nameEl, dotEl, statusEl })
}

function onPointerDown(event) {
  pointerDownPos = { x: event.clientX, y: event.clientY }
}

function onPointerUp(event) {
  if (!pointerDownPos) return

  const dx = event.clientX - pointerDownPos.x
  const dy = event.clientY - pointerDownPos.y
  pointerDownPos = null

  // Only trigger selection if mouse barely moved (< 3px) — not a drag
  if (Math.sqrt(dx * dx + dy * dy) > 3) return

  const el = container.value
  if (!el || !renderer) return

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  // Collect all car meshes for intersection test
  const carMeshes = []
  carModels.forEach(car => {
    car.group.traverse(child => {
      if (child.isMesh) carMeshes.push(child)
    })
  })

  const intersects = raycaster.intersectObjects(carMeshes, false)

  if (intersects.length > 0) {
    let obj = intersects[0].object
    while (obj && obj.userData.robotId === undefined) {
      obj = obj.parent
    }
    if (obj && obj.userData.robotId !== undefined) {
      store.selectedRobotId = obj.userData.robotId
    }
  }
}

// Highlight selected robot via LED emissive intensity
function updateHighlight() {
  carModels.forEach((car) => {
    if (!car.led) return
    if (store.selectedRobotId === car.group.userData.robotId) {
      car.led.material.emissiveIntensity = 2.0
      car.led.material.emissive.setHex(0xffffff)
    } else {
      car.led.material.emissive.setHex(0x2563eb)
    }
  })
}

// Sync store fleet data to label DOM elements
function updateLabels() {
  const fleet = store.fleet
  if (!fleet || !fleet.length) return

  fleet.forEach((robot, i) => {
    if (i >= labelObjects.length) return
    const { dotEl, statusEl } = labelObjects[i]

    const statusInfo = ROBOT_STATUS_MAP[robot.status] || ROBOT_STATUS_MAP.idle
    statusEl.textContent = statusInfo.label
    dotEl.style.backgroundColor = statusInfo.color
  })
}

function animate() {
  // Update controls (required for damping)
  controls.update()

  // Update animation from store data
  animController.update(store.fleet, store.lux)

  // Apply selection highlight
  updateHighlight()

  // Update floating labels
  updateLabels()

  // Pulse waypoint beacons
  if (sceneEnv && sceneEnv.pulseWaypointBeacons) {
    sceneEnv.pulseWaypointBeacons(performance.now())
  }

  // Render 3D scene
  renderer.render(scene, camera)

  // Render CSS2D labels on top
  labelRenderer.render(scene, camera)
}

function onResize() {
  const el = container.value
  if (!el) return
  const w = el.clientWidth
  const h = el.clientHeight
  if (!w || !h) return

  // 如果 Three.js 尚未初始化（init() 因容器 0 尺寸提前返回），现在重试
  if (!_initialized) {
    init()
    return
  }

  if (!renderer || !camera || !labelRenderer) return
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
  labelRenderer.setSize(w, h)
}

onMounted(() => {
  init()
  window.addEventListener('resize', onResize)
  if (container.value && window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => requestAnimationFrame(onResize))
    resizeObserver.observe(container.value)
  }
})

onUnmounted(() => {
  _initialized = false

  window.removeEventListener('resize', onResize)
  if (resizeObserver) {
    try { resizeObserver.disconnect() } catch (_) { /* noop */ }
    resizeObserver = null
  }

  // 第一优先：停止动画循环，防止后续帧访问已销毁资源
  if (renderer) {
    try { renderer.setAnimationLoop(null) } catch (_) { /* noop */ }
  }

  // 移除事件监听
  if (renderer && renderer.domElement) {
    try {
      renderer.domElement.removeEventListener('pointerdown', onPointerDown)
      renderer.domElement.removeEventListener('pointerup', onPointerUp)
    } catch (_) { /* noop */ }
  }

  // 销毁车辆模型（从 scene 中移除）
  if (carModels && carModels.length) {
    carModels.forEach(m => { try { m.dispose() } catch (_) { /* noop */ } })
    carModels = []
  }

  // 销毁 OrbitControls（移除 DOM 事件监听）
  if (controls) {
    try { controls.dispose() } catch (_) { /* noop */ }
    controls = null
  }

  // 销毁 WebGL 渲染器（释放 GPU 资源）
  if (renderer) {
    try { renderer.dispose() } catch (_) { /* noop */ }
    // 从 DOM 移除 canvas
    if (container.value) {
      try { container.value.removeChild(renderer.domElement) } catch (_) { /* noop */ }
    }
    renderer = null
  }

  // 移除 CSS2D 渲染器 DOM 元素
  if (labelRenderer && container.value) {
    try { container.value.removeChild(labelRenderer.domElement) } catch (_) { /* noop */ }
    labelRenderer = null
  }

  // 清空引用，确保下次 mount 干净启动
  scene = null
  camera = null
  sceneEnv = null
  animController = null
  raycaster = null
  pointer = null
  labelObjects = []
})
</script>

<style scoped>
.car-scene {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: var(--radius, 6px);
}
</style>

<style>
/* Floating robot labels — global (not scoped) so CSS2DRenderer can apply them */
.robot-label {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(30, 80, 180, 0.3);
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  user-select: none;
}

.robot-label__name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.robot-label__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #94a3b8;
  flex-shrink: 0;
}

.robot-label__status {
  font-size: 12px;
  color: #64748b;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* Waypoint labels — interactive scheduling points on the factory floor */
.waypoint-label {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 1px 8px 1px 1px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid;
  border-radius: 999px;
  white-space: nowrap;
  pointer-events: none;
  user-select: none;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.wp-id {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 18px;
  padding: 0 6px;
  border-radius: 999px;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.wp-name {
  font-size: 12px;
  font-weight: 600;
}
</style>
