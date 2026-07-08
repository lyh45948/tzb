/**
 * Data formatting utilities for smart factory digital twin
 */

const TIME_PERIOD_NAMES = ['黎明巡检', '上午生产', '中午稳态', '下午生产', '黄昏补光', '晚间安全', '深夜休眠']
const LIGHT_LEVEL_NAMES = ['黑暗', '昏暗', '偏暗', '正常', '明亮', '强光']

export function formatTime(date) {
  const d = new Date(date)
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export function formatDateTime(date) {
  const d = new Date(date)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${formatTime(d)}`
}

function pad(n) {
  return n < 10 ? '0' + n : n
}

export function formatNumber(val, decimals = 1) {
  if (val == null || isNaN(val)) return '--'
  return Number(val).toFixed(decimals)
}

export function getBatteryColor(pct) {
  if (pct > 60) return '#22c55e'
  if (pct > 20) return '#f59e0b'
  return '#ef4444'
}

export function getBatteryLevel(voltage) {
  if (voltage == null) return 0
  const pct = ((voltage - 6.0) / (8.4 - 6.0)) * 100
  return Math.max(0, Math.min(100, Math.round(pct)))
}

export function getFactoryAlertLevel(data) {
  if (!data) return 'normal'
  const distance = data.minDistanceCm ?? data.minDistance ?? 999
  if (data.flameStatus || data.gasStatus || data.co2 >= 60 || data.tvoc >= 950 || data.gasMic >= 550) return 'critical'
  if (data.temperature >= 35 || data.humidity >= 80 || data.co2 >= 50 || data.tvoc >= 900 || distance <= 15) return 'danger'
  if (data.temperature >= 30 || data.humidity >= 75 || data.co2 >= 35 || data.tvoc >= 600 || distance <= 30) return 'warning'
  return 'normal'
}

function getLinkedActionReason(data) {
  if (data.flameStatus) return '火焰信号触发蜂鸣器与警示灯'
  if (data.gasStatus) return '可燃气体异常触发排风与蜂鸣器'
  if (data.co2 >= 50) return 'CO危险阈值触发强制通风'
  if (data.co2 >= 35) return 'CO偏高触发通风预警'
  if ((data.minDistanceCm ?? 999) <= 15) return 'AGV安全距离危险，建议停车避障'
  if ((data.minDistanceCm ?? 999) <= 30) return 'AGV接近障碍物，进入避障观察'
  if (data.humanDetected) return '红外检测到人员，保持安全照明'
  return '系统运行正常，无联动动作'
}

/**
 * Generate simulated workshop safety data for demo mode
 */
export function generateSimData(time) {
  const t = time * 0.001
  const co2Spike = Math.max(0, Math.sin(t * 0.12 - 1.6)) * 18
  const tvocSpike = Math.max(0, Math.sin(t * 0.16 + 0.7)) * 220
  const gasMic = 120 + tvocSpike * 0.9 + Math.random() * 45
  const minDistanceCm = Math.max(8, 60 + Math.sin(t * 0.18) * 42 + Math.random() * 8)
  // CO 浓度（ppm）：基线 8 ppm，正常波动 ±5 ppm，偶发异常加 0~18 ppm；
  // 35 ppm 警告 / 50 ppm 危险（参考 GBZ 2.1 工作场所限值）
  const co2 = Math.max(0, 8 + Math.sin(t * 0.08) * 5 + co2Spike + Math.random() * 2)
  const tvoc = 180 + Math.sin(t * 0.11) * 90 + tvocSpike + Math.random() * 35
  const flameStatus = Math.sin(t * 0.035) > 0.995 ? 1 : 0
  const gasStatus = gasMic > 430 || tvoc > 780 ? 1 : 0
  const brightness = Math.round(Math.max(20, Math.min(95, 55 + Math.sin(t * 0.1) * 30)))
  const humanDetected = Math.sin(t * 0.22) > 0.35 ? 1 : 0
  const timePeriod = Math.floor((t / 12) % 7)
  const lightLevel = Math.floor(Math.max(0, Math.min(5, (brightness / 100) * 6)))
  const goodsCount = Math.floor(1200 + t * 5 + Math.sin(t * 0.2) * 25)
  const goodsPulse = Math.sin(t * 2.1) > 0.82 ? 1 : 0

  const data = {
    temperature: 24 + Math.sin(t * 0.09) * 5 + Math.random() * 1.5,
    humidity: 56 + Math.sin(t * 0.07) * 16 + Math.random() * 3,
    lux: Math.max(80, 720 + Math.sin(t * 0.13) * 520 + Math.random() * 60),
    ps: Math.round(humanDetected ? 520 + Math.random() * 260 : 80 + Math.random() * 120),
    ir: humanDetected,
    humanDetected,
    pirStatus: humanDetected ? 'detected' : 'clear',
    co2,
    tvoc,
    gasMic,
    gasStatus,
    flameStatus,
    minDistance: minDistanceCm,
    minDistanceCm,
    minDistanceMm: Math.round(minDistanceCm * 10),
    goodsCount,
    goodsPulse,
    counterDigits: String(goodsCount).padStart(6, '0'),
    fan: gasStatus || co2 > 40 ? 1 : 0,
    led: humanDetected ? 1 : 0,
    buzzer: flameStatus || gasStatus ? 1 : 0,
    linkage: {
      enabled: true,
      fan: gasStatus || co2 > 40 ? 1 : 0,
      led: humanDetected ? 1 : 0,
      rgb: flameStatus
        ? { r: 255, g: 0, b: 0 }
        : (gasStatus
          ? { r: 255, g: 0, b: 0 }
          : (co2 > 35 || tvoc > 600 || gasMic > 300
            ? { r: 255, g: 255, b: 0 }
            : { r: 0, g: 0, b: 0 })),
      alertLevel: flameStatus
        ? 'critical'
        : (gasStatus || co2 > 50 || tvoc > 900 || gasMic > 500
          ? 'danger'
          : (co2 > 35 || tvoc > 600 || gasMic > 300 ? 'warning' : 'normal')),
      reasons: {
        fan: `temp=${(24 + Math.sin(t * 0.09) * 5).toFixed(1)},humi=${(56 + Math.sin(t * 0.07) * 16).toFixed(1)}`,
        led: humanDetected ? 'PIR detected' : 'PIR clear',
        rgb: flameStatus ? '检测到火焰' : (gasStatus ? '危气danger' : '环境正常')
      },
      manualOverrideRemaining: { fan: 0, led: 0, rgb: 0 }
    }
  }

  data.alertLevel = getFactoryAlertLevel(data)
  data.linkedActionReason = getLinkedActionReason(data)
  return data
}

// ─── Waypoint-based AGV trajectory system ───
// 路径只在安全通道交叉点之间走(H通道 z∈{-8.5,-1.5,4,9.5}, V通道 x∈{-8,-1,3.5,13}),
// 避免穿越货架/工位/危气区/货物区等建筑物。

const PATHS = {
  // 大循环巡检:绕厂区一圈(避开危气区/货物区)
  inspectionLoop: [
    { x: -8, z: -8.5 },  { x: 13, z: -8.5 },
    { x: 13, z: -1.5 },  { x:  3.5, z: -1.5 },
    { x:  3.5, z:  4 },  { x:  3.5, z:  9.5 },
    { x: -8, z:  9.5 },  { x: -8, z: -8.5 }
  ],
  // 仓库侧来回:在 V=-8 走廊上下穿梭
  warehouseLoop: [
    { x: -8, z: -8.5 }, { x: -8, z: -1.5 },
    { x: -8, z:  4 },   { x: -8, z:  9.5 },
    { x: -8, z:  4 },   { x: -8, z: -1.5 },
    { x: -8, z: -8.5 }
  ],
  // 物料转运:仓库 ↔ 加工区 ↔ 出货
  materialRoute: [
    { x: -8, z:  4 },    { x: -1, z:  4 },
    { x: -1, z: -1.5 },  { x:  3.5, z: -1.5 },
    { x:  3.5, z:  4 },  { x:  3.5, z:  9.5 },
    { x: -8, z:  9.5 },  { x: -8, z:  4 }
  ],
  // 安防巡检:在右侧 V=13 / 加工线 / 包装区之间循环
  safetyRoute: [
    { x: 13, z:  9.5 }, { x: 13, z:  4 },
    { x: 13, z: -1.5 }, { x: 13, z: -8.5 },
    { x:  3.5, z: -8.5 }, { x:  3.5, z: -1.5 },
    { x: 13, z: -1.5 }, { x: 13, z:  9.5 }
  ]
}

const robotPathState = []

function ensurePathState(robotCount) {
  while (robotPathState.length < robotCount) {
    robotPathState.push({ waypointIndex: 0, progress: 0 })
  }
}

function getDist(a, b) {
  const dx = a.x - b.x
  const dz = a.z - b.z
  return Math.sqrt(dx * dx + dz * dz)
}

const ROBOT_SPEEDS = [260, 210, 230, 190]
const ROBOT_PATHS = ['inspectionLoop', 'warehouseLoop', 'materialRoute', 'safetyRoute']
const ROBOT_TASKS = ['obstacleAvoidance', 'patrol', 'goodsCount', 'gasMonitor']
const ROBOT_NAMES = ['AGV-01', '巡检车-01', '物料车-01', '安防巡检-02']

// 让 store 在 AGV 返航完成后,把巡逻状态对齐到目标 waypoint 上,避免下一帧"瞬移"
export function getDefaultPatrolStart(robotIndex) {
  const key = ROBOT_PATHS[robotIndex] || 'inspectionLoop'
  return PATHS[key][0]
}

export function resetRobotPathToWaypoint(robotIndex, waypoint) {
  ensurePathState(robotIndex + 1)
  const key = ROBOT_PATHS[robotIndex] || 'inspectionLoop'
  const path = PATHS[key]
  // 找出与给定 waypoint 完全相等(或最近)的索引
  let bestIdx = 0
  let bestDist = Infinity
  for (let i = 0; i < path.length; i++) {
    const d = Math.hypot(path[i].x - waypoint.x, path[i].z - waypoint.z)
    if (d < bestDist) { bestDist = d; bestIdx = i }
  }
  robotPathState[robotIndex].waypointIndex = bestIdx
  robotPathState[robotIndex].progress = 0
}

// 在做碰撞回滚时,store 需要把巡逻 state 也撤回到上一帧,避免视觉抖动
export function snapshotPatrolState(robotIndex) {
  ensurePathState(robotIndex + 1)
  const s = robotPathState[robotIndex]
  return { waypointIndex: s.waypointIndex, progress: s.progress }
}

export function restorePatrolState(robotIndex, snap) {
  if (!snap) return
  ensurePathState(robotIndex + 1)
  robotPathState[robotIndex].waypointIndex = snap.waypointIndex
  robotPathState[robotIndex].progress = snap.progress
}

function buildRobotPayload({ robotId, index, task, status, carMode, speed, distanceCm, position, rotation, factoryData }) {
  const batteryPercent = Math.max(15, 92 - (((factoryData?._t || 0) + index * 45) % 220) * 0.28)
  const batteryVoltage = Math.round(7200 + (batteryPercent / 100) * 1200)
  return {
    id: robotId,
    device_id: `demo_car_${String(index + 1).padStart(3, '0')}`,
    name: ROBOT_NAMES[index] || `设备-${index + 1}`,
    online: true,
    last_receive_time: Date.now(),
    status,
    task,
    mode: carMode,
    carStatus: speed > 0 ? 'run' : 'stop',
    carMode,
    carSpeed: speed >= 900 ? 'high' : speed >= 500 ? 'middle' : 'low',
    L_spd: Math.round(speed + Math.sin((factoryData?._t || 0) + index) * 15),
    R_spd: Math.round(speed + Math.cos((factoryData?._t || 0) + index) * 15),
    battery: batteryPercent,
    batteryPercent,
    batteryVoltage,
    carPowerRaw: batteryVoltage,
    speed,
    distance: distanceCm,
    distanceCm,
    distanceMm: Math.round(distanceCm * 10),
    goodsCount: Math.floor((factoryData?.goodsCount || 0) + index * 12),
    alertLevel: status === 'warning' ? 'critical' : distanceCm <= 15 ? 'danger' : distanceCm <= 30 ? 'warning' : 'normal',
    position,
    rotation
  }
}

/**
 * Generate simulated AGV fleet data with factory waypoint routes
 */
export function generateFleetData(time, robotCount, manualOverrides = null, factoryData = null) {
  ensurePathState(robotCount)
  const t = time * 0.001
  const data = factoryData ? { ...factoryData, _t: t } : { _t: t }
  const robots = []

  for (let i = 0; i < robotCount; i++) {
    const robotId = `robot_${i + 1}`
    const task = ROBOT_TASKS[i] || 'patrol'

    if (manualOverrides && manualOverrides.overrides && manualOverrides.overrides[robotId]) {
      const pos = manualOverrides.positions[robotId]
      const dir = manualOverrides.direction
      const isMoving = dir && dir !== 'stop'
      let rotation = 0
      if (dir === 'forward') rotation = 0
      else if (dir === 'back') rotation = Math.PI
      else if (dir === 'left') rotation = Math.PI / 2
      else if (dir === 'right') rotation = -Math.PI / 2

      const distanceCm = Math.max(8, 45 + Math.sin(t * 0.7 + i) * 28 + Math.random() * 8)
      const status = isMoving ? (distanceCm <= 30 ? 'avoiding' : 'pathExecuting') : 'idle'
      const speed = isMoving ? 300 : 0

      robots.push(buildRobotPayload({
        robotId,
        index: i,
        task,
        status,
        carMode: 'manual',
        speed,
        distanceCm,
        factoryData: data,
        position: {
          x: pos.x + (Math.random() - 0.5) * 0.02,
          z: pos.z + (Math.random() - 0.5) * 0.02
        },
        rotation
      }))
      continue
    }

    const pathKey = ROBOT_PATHS[i] || 'inspectionLoop'
    const path = PATHS[pathKey]
    const state = robotPathState[i]
    const speed = ROBOT_SPEEDS[i] || 200

    if (path.length < 2) continue

    const currentIdx = state.waypointIndex
    const nextIdx = (currentIdx + 1) % path.length
    const segmentDist = getDist(path[currentIdx], path[nextIdx])

    if (segmentDist > 0) {
      state.progress += (speed * 0.001) / segmentDist
    }

    while (state.progress >= 1) {
      state.progress -= 1
      state.waypointIndex = (state.waypointIndex + 1) % path.length
    }

    const curIdx = state.waypointIndex
    const nxtIdx = (curIdx + 1) % path.length
    const cur = path[curIdx]
    const nxt = path[nxtIdx]
    const prog = state.progress
    const x = cur.x + (nxt.x - cur.x) * prog + (Math.random() - 0.5) * 0.04
    const z = cur.z + (nxt.z - cur.z) * prog + (Math.random() - 0.5) * 0.04
    const distanceCm = Math.max(8, 52 + Math.sin(t * 0.4 + i * 1.7) * 38 + Math.random() * 8)

    let status = 'pathExecuting'
    let carMode = 'path'
    if (task === 'patrol') { status = 'patrolling'; carMode = 'path' }
    if (task === 'goodsCount') { status = 'lineTracking'; carMode = 'line' }
    if (task === 'obstacleAvoidance') { status = distanceCm <= 30 ? 'avoiding' : 'pathExecuting'; carMode = 'avoid' }
    if (task === 'gasMonitor') {
      status = factoryData?.gasStatus || factoryData?.flameStatus ? 'warning' : 'patrolling'
      carMode = 'path'
    }

    robots.push(buildRobotPayload({
      robotId,
      index: i,
      task,
      status,
      carMode,
      speed,
      distanceCm,
      factoryData: data,
      position: { x, z },
      rotation: Math.atan2(nxt.x - cur.x, nxt.z - cur.z)
    }))
  }

  return robots
}
