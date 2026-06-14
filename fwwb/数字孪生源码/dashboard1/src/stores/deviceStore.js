import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  generateSimData,
  generateFleetData,
  getDefaultPatrolStart,
  resetRobotPathToWaypoint,
  snapshotPatrolState,
  restorePatrolState
} from '../utils/dataFormatter'
import { FACTORY_WAYPOINTS, planRoute } from '../utils/waypoints'
import config from '../config'

function findWaypoint(id) {
  return FACTORY_WAYPOINTS.find(w => w.id === id) || null
}

// 用 robotId 直线插值速度近似 0.18(场景单位/秒),按 dt 步进 progress
const TASK_LINEAR_SPEED = 1.8
// AGV 之间允许的最小中心距(场景单位 ≈ 米);小于此值视为相撞,需要其中一方让步
const MIN_AGV_DIST = 1.4

export const useDeviceStore = defineStore('device', () => {
  // System is always in demo mode
  const demoMode = ref(true)
  const online = ref(true)

  // Workshop environment and safety data
  const temperature = ref(24.5)
  const humidity = ref(58.2)
  const lux = ref(650)
  const ps = ref(120)
  const ir = ref(0)
  const humanDetected = ref(0)
  const pirStatus = ref('clear')
  const co2 = ref(520)
  const tvoc = ref(180)
  const gasMic = ref(120)
  const gasStatus = ref(0)
  const flameStatus = ref(0)
  const minDistance = ref(60)
  const minDistanceCm = ref(60)
  const minDistanceMm = ref(600)
  const goodsCount = ref(1200)
  const goodsPulse = ref(0)
  const counterDigits = ref('001200')
  const fan = ref(0)
  const led = ref(1)
  const buzzer = ref(0)
  const alertLevel = ref('normal')
  const linkedActionReason = ref('系统运行正常，无联动动作')
  const linkage = ref({
    enabled: true,
    fan: 0,
    led: 0,
    rgb: { r: 0, g: 0, b: 0 },
    alertLevel: 'normal',
    reasons: { fan: '', led: '', rgb: '' },
    manualOverrideRemaining: { fan: 0, led: 0, rgb: 0 }
  })

  // AGV/device fleet data
  const fleet = ref([])

  // Shared selected device ID for cross-component sync
  const selectedRobotId = ref(null)

  // Manual control state
  const manualOverrides = ref({})
  const manualPositions = ref({})
  const manualDirection = ref(null)

  // Safety alarm events and simulated control logs
  const alarmEvents = ref([])
  const commandLogs = ref([])

  // ─── AGV 调度任务队列 ───
  // 任务结构: { id, type, fromId, toId, robotId, status, priority, progress,
  //            createdAt, startedAt, completedAt, distance, note }
  const tasks = ref([])
  let taskSeq = 1
  function nextTaskId() {
    return `T${String(taskSeq++).padStart(4, '0')}`
  }

  // 返航计划:任务完成后,AGV 沿曼哈顿走廊驶回默认巡逻起点,而不是"瞬移"
  // { robotId: { robotIndex, route, distance, traveled, target } }
  const returningRobots = ref({})

  // 上一帧位置快照,用于碰撞回滚(普通对象,非响应式)
  const prevPositions = {}
  // 记录上一帧巡逻 state,用于巡逻车被回退时同步回滚 dataFormatter 的 waypointIndex/progress
  const prevPatrolStates = {}

  // Chart history data
  const historyLabels = ref([])
  const historyTemp = ref([])
  const historyHumi = ref([])
  const historyLux = ref([])
  const historyCO2 = ref([])
  const historyTVOC = ref([])
  const historyGasMic = ref([])
  const historyGoodsCount = ref([])

  // Time tracking
  const lastUpdateTime = ref(Date.now())
  const startTime = ref(Date.now())

  // Backend connection status: idle | live | polling | demo | disconnected
  const connectionStatus = ref('idle')

  const isOnline = computed(() => online.value)
  const highestAlert = computed(() => {
    const priority = { normal: 0, warning: 1, danger: 2, critical: 3 }
    return fleet.value.reduce((highest, r) => {
      return priority[r.alertLevel] > priority[highest] ? r.alertLevel : highest
    }, alertLevel.value || 'normal')
  })

  let simTimer = null

  function pushCommandLog(commandType, command, reason, deviceId = 'system') {
    commandLogs.value.unshift({
      id: Date.now() + Math.random(),
      timestamp: Date.now(),
      device_id: deviceId,
      command_type: commandType,
      command,
      source: 'system',
      is_simulated: true,
      result: 'mocked',
      reason
    })
    if (commandLogs.value.length > 12) commandLogs.value = commandLogs.value.slice(0, 12)
  }

  function pushAlarm(level, type, message, asset = '系统', metric = '--', value = '--', threshold = '--') {
    const last = alarmEvents.value[0]
    if (last && last.type === type && Date.now() - last.timestamp < 6000) return
    alarmEvents.value.unshift({
      id: Date.now(),
      timestamp: Date.now(),
      level,
      type,
      asset,
      device_id: asset,
      title: message,
      message,
      metric,
      value,
      threshold,
      source: 'simulated',
      handled: false,
      suggestion: getAlarmSuggestion(type),
      status: 'active'
    })
    if (alarmEvents.value.length > 10) {
      alarmEvents.value = alarmEvents.value.slice(0, 10)
    }
  }

  function getAlarmSuggestion(type) {
    const map = {
      flame: '立即停机并检查火源，保持蜂鸣器告警',
      gas: '启动排风并疏散危气区域人员',
      co2: '增强通风，检查车间空气循环',
      temperature: '检查空调/风扇并降低设备负载',
      obstacle: 'AGV减速停车，清理通道障碍'
    }
    return map[type] || '请值班人员复核现场状态'
  }

  function updateAlarmEvents(simData, fleetData) {
    if (simData.flameStatus) pushAlarm('critical', 'flame', '检测到火焰信号，已触发蜂鸣器', '危气监测区', 'flameStatus', 1, '1=触发')
    if (simData.gasStatus) pushAlarm('critical', 'gas', '可燃气体浓度异常，已启动排风', '危气监测区', 'gasStatus', 1, '1=泄漏')
    if (simData.co2 >= 1000) pushAlarm('danger', 'co2', `CO2浓度 ${Math.round(simData.co2)}ppm 超过危险阈值`, '车间环境', 'CO2', Math.round(simData.co2), '1000ppm')
    else if (simData.co2 >= 800) pushAlarm('warning', 'co2', `CO2浓度 ${Math.round(simData.co2)}ppm 偏高`, '车间环境', 'CO2', Math.round(simData.co2), '800ppm')
    if (simData.temperature >= 35) pushAlarm('danger', 'temperature', `温度 ${simData.temperature.toFixed(1)}℃ 超过危险阈值`, '车间环境', '温度', simData.temperature.toFixed(1), '35℃')
    else if (simData.temperature >= 30) pushAlarm('warning', 'temperature', `温度 ${simData.temperature.toFixed(1)}℃ 偏高`, '车间环境', '温度', simData.temperature.toFixed(1), '30℃')

    const nearest = fleetData.reduce((min, r) => r.distanceCm < min.distanceCm ? r : min, { distanceCm: Infinity })
    if (nearest.distanceCm <= 15) pushAlarm('danger', 'obstacle', `${nearest.name} 障碍物距离 ${Math.round(nearest.distanceCm)}cm`, nearest.device_id, '安全距离', Math.round(nearest.distanceCm), '15cm')
    else if (nearest.distanceCm <= 30) pushAlarm('warning', 'obstacle', `${nearest.name} 接近障碍物 ${Math.round(nearest.distanceCm)}cm`, nearest.device_id, '安全距离', Math.round(nearest.distanceCm), '30cm')
  }

  // 派发新任务进入队列(默认 pending,等下一 tick 自动分配)
  function dispatchTask(payload) {
    const from = findWaypoint(payload.fromId)
    const to = findWaypoint(payload.toId)
    if (!from || !to || from.id === to.id) return null

    // 送达段 from→to 的曼哈顿路径(避建筑)
    const route = planRoute(from, to)
    let distance = 0
    for (let i = 1; i < route.length; i++) {
      distance += Math.hypot(route[i].x - route[i - 1].x, route[i].z - route[i - 1].z)
    }

    const task = {
      id: nextTaskId(),
      type: payload.type || 'transport',
      fromId: from.id,
      toId: to.id,
      fromName: from.name,
      toName: to.name,
      robotId: payload.robotId || null, // 指定 AGV;为空则自动分配
      status: 'pending',
      priority: payload.priority || 'normal',
      progress: 0,
      createdAt: Date.now(),
      startedAt: null,
      completedAt: null,
      distance,
      route, // 送达段路径(包括 from / to)
      pickupRoute: null, // 取货段路径,assign 时计算
      note: payload.note || ''
    }
    tasks.value = [task, ...tasks.value]
    pushCommandLog('task', `dispatch ${task.id} ${from.id}→${to.id}`, `任务 ${task.id} 已下发,等待分配`, task.robotId || 'auto')
    return task
  }

  function cancelTask(taskId) {
    const t = tasks.value.find(x => x.id === taskId)
    if (!t || t.status === 'completed' || t.status === 'cancelled') return
    const wasRunning = t.status === 'running'
    t.status = 'cancelled'
    t.completedAt = Date.now()
    pushCommandLog('task', `cancel ${taskId}`, `任务 ${taskId} 已取消`, t.robotId || 'system')
    // 取消运行中的任务时,让该 AGV 也走回去
    if (wasRunning && t.robotId) {
      const robot = fleet.value.find(r => r.id === t.robotId)
      if (robot) startReturning(t.robotId, robot)
    }
    tasks.value = [...tasks.value]
  }

  function clearCompletedTasks() {
    tasks.value = tasks.value.filter(t => t.status !== 'completed' && t.status !== 'cancelled')
  }

  // 给 pending 任务挑选空闲 AGV;紧急任务优先
  function assignPendingTasks(fleetData) {
    if (!tasks.value.length) return
    const busyRobotIds = new Set(
      tasks.value.filter(t => t.status === 'running' && t.robotId).map(t => t.robotId)
    )
    // 返航中的 AGV 同样视为占用,等返航完成才能接新任务
    Object.keys(returningRobots.value).forEach(id => busyRobotIds.add(id))

    // 紧急任务优先,然后按 createdAt 升序
    const pending = tasks.value
      .filter(t => t.status === 'pending')
      .sort((a, b) => {
        if (a.priority !== b.priority) return a.priority === 'high' ? -1 : 1
        return a.createdAt - b.createdAt
      })

    for (const task of pending) {
      // 指定了 robotId 的任务必须等该车空闲且非手动
      if (task.robotId) {
        if (busyRobotIds.has(task.robotId)) continue
        if (manualOverrides.value[task.robotId]) continue
        const robot = fleetData.find(r => r.id === task.robotId)
        if (!robot) continue
        startTaskOnRobot(task, robot)
        busyRobotIds.add(task.robotId)
        continue
      }

      // 自动分配:挑离起点最近、空闲且非手动的 AGV
      const from = findWaypoint(task.fromId)
      let best = null
      let bestDist = Infinity
      for (const robot of fleetData) {
        if (busyRobotIds.has(robot.id)) continue
        if (manualOverrides.value[robot.id]) continue
        const d = Math.hypot(robot.position.x - from.x, robot.position.z - from.z)
        if (d < bestDist) { best = robot; bestDist = d }
      }
      if (best) {
        task.robotId = best.id
        startTaskOnRobot(task, best)
        busyRobotIds.add(best.id)
      }
    }
    tasks.value = [...tasks.value]
  }

  function startTaskOnRobot(task, robot) {
    task.status = 'running'
    task.startedAt = Date.now()
    task.progress = 0
    // 取货段:robot 当前位置 → from,也用 planRoute 避障
    const from = findWaypoint(task.fromId)
    const robotPos = { x: robot.position.x, z: robot.position.z }
    task.pickupRoute = planRoute(robotPos, from)
    task.pickupDistance = 0
    for (let i = 1; i < task.pickupRoute.length; i++) {
      task.pickupDistance += Math.hypot(
        task.pickupRoute[i].x - task.pickupRoute[i - 1].x,
        task.pickupRoute[i].z - task.pickupRoute[i - 1].z
      )
    }
    pushCommandLog('task', `start ${task.id} on ${robot.id}`, `${robot.name} 开始执行任务 ${task.id}`, robot.id)
  }

  // 在多段折线上按弧长 s 找到对应位置
  function pointAlongPath(path, s) {
    if (!path || path.length < 2) return path?.[0] || { x: 0, z: 0 }
    let acc = 0
    for (let i = 1; i < path.length; i++) {
      const segLen = Math.hypot(path[i].x - path[i - 1].x, path[i].z - path[i - 1].z)
      if (acc + segLen >= s || i === path.length - 1) {
        const k = segLen === 0 ? 1 : Math.min(1, (s - acc) / segLen)
        return {
          x: path[i - 1].x + (path[i].x - path[i - 1].x) * k,
          z: path[i - 1].z + (path[i].z - path[i - 1].z) * k
        }
      }
      acc += segLen
    }
    return path[path.length - 1]
  }

  // 推进 running 任务: 阶段一 robot→from(pickupRoute), 阶段二 from→to(route)
  function advanceRunningTasks(fleetData, dt) {
    if (!tasks.value.length || !dt) return
    const robotMap = new Map(fleetData.map(r => [r.id, r]))
    let touched = false

    for (const task of tasks.value) {
      if (task.status !== 'running') continue
      const robot = robotMap.get(task.robotId)
      if (!robot) continue
      // 手动模式下任务暂停,不推进
      if (manualOverrides.value[task.robotId]) continue
      touched = true

      const pickupDist = task.pickupDistance || 0
      const deliverDist = task.distance || 0
      const totalDist = (pickupDist + deliverDist) || 1
      const prevProgress = task.progress
      task.progress = Math.min(1, task.progress + (TASK_LINEAR_SPEED * dt) / totalDist)

      const traveled = task.progress * totalDist
      let pos
      if (traveled <= pickupDist) {
        pos = pointAlongPath(task.pickupRoute, traveled)
      } else {
        pos = pointAlongPath(task.route, traveled - pickupDist)
      }

      // 覆盖 fleetData 数据 — 这是渲染/3D 的真实数据源
      robot.position = { x: pos.x, z: pos.z }
      robot.status = 'pathExecuting'
      robot.carMode = 'path'
      robot.taskId = task.id
      robot.taskFrom = task.fromName
      robot.taskTo = task.toName
      robot.taskProgress = task.progress
      robot._driver = 'task'
      robot._priority = task.priority === 'high' ? 4 : 3
      // 记录回滚信息 — resolveCollisions 让步时用
      robot._rollback = () => {
        task.progress = prevProgress
        const t2 = task.progress * totalDist
        const p2 = t2 <= pickupDist
          ? pointAlongPath(task.pickupRoute, t2)
          : pointAlongPath(task.route, t2 - pickupDist)
        robot.position = { x: p2.x, z: p2.z }
        robot.taskProgress = task.progress
      }

      if (task.progress >= 1) {
        task.status = 'completed'
        task.completedAt = Date.now()
        task.progress = 1
        pushCommandLog('task', `complete ${task.id}`, `任务 ${task.id} 已送达 ${task.toName}`, robot.id)
        // 任务完成后,让 AGV 沿走廊驶回默认巡逻起点,而非瞬移
        startReturning(task.robotId, robot)
      }
    }

    if (touched) tasks.value = [...tasks.value]
  }

  // 任务完成后启动返航:robot 当前位置 → 默认巡逻路径起点
  function startReturning(robotId, robot) {
    const robotIndex = parseInt(robotId.replace('robot_', ''), 10) - 1
    if (Number.isNaN(robotIndex) || robotIndex < 0) return
    const target = getDefaultPatrolStart(robotIndex)
    if (!target) return
    const robotPos = { x: robot.position.x, z: robot.position.z }
    // 已经在巡逻起点附近就直接复位,不必返航
    if (Math.hypot(robotPos.x - target.x, robotPos.z - target.z) < 0.4) {
      resetRobotPathToWaypoint(robotIndex, target)
      return
    }
    const route = planRoute(robotPos, target)
    let distance = 0
    for (let i = 1; i < route.length; i++) {
      distance += Math.hypot(route[i].x - route[i - 1].x, route[i].z - route[i - 1].z)
    }
    returningRobots.value = {
      ...returningRobots.value,
      [robotId]: { robotIndex, route, distance, traveled: 0, target }
    }
    pushCommandLog('task', `return ${robotId}`, `${robot.name || robotId} 任务结束,返航至 (${target.x},${target.z})`, robotId)
  }

  // 推进返航中的 AGV;走完即归还给默认巡逻
  function advanceReturningRobots(fleetData, dt) {
    if (!dt) return
    const ids = Object.keys(returningRobots.value)
    if (!ids.length) return
    const robotMap = new Map(fleetData.map(r => [r.id, r]))
    let mutated = false
    const next = { ...returningRobots.value }

    for (const robotId of ids) {
      const plan = next[robotId]
      const robot = robotMap.get(robotId)
      if (!robot) continue
      // 手动模式 — 取消返航,把巡逻状态对齐到当前位置最近的 waypoint
      if (manualOverrides.value[robotId]) {
        resetRobotPathToWaypoint(plan.robotIndex, { x: robot.position.x, z: robot.position.z })
        delete next[robotId]
        mutated = true
        continue
      }

      const prevTraveled = plan.traveled
      plan.traveled = Math.min(plan.distance, plan.traveled + TASK_LINEAR_SPEED * dt)
      const pos = pointAlongPath(plan.route, plan.traveled)

      robot.position = { x: pos.x, z: pos.z }
      robot.status = 'pathExecuting'
      robot.carMode = 'path'
      robot.taskId = null
      robot.taskFrom = null
      robot.taskTo = '巡逻起点'
      robot.taskProgress = plan.distance ? plan.traveled / plan.distance : 1
      robot.returning = true
      robot._driver = 'returning'
      robot._priority = 2
      robot._rollback = () => {
        plan.traveled = prevTraveled
        const p2 = pointAlongPath(plan.route, plan.traveled)
        robot.position = { x: p2.x, z: p2.z }
        robot.taskProgress = plan.distance ? plan.traveled / plan.distance : 1
      }

      if (plan.traveled >= plan.distance) {
        // 抵达巡逻起点 — 把 dataFormatter 的 waypointIndex 复位到这里,下一帧无缝接管
        resetRobotPathToWaypoint(plan.robotIndex, plan.target)
        delete next[robotId]
        mutated = true
      }
    }

    if (mutated || ids.length) returningRobots.value = next
  }

  // 检测 AGV 互相靠近 (< MIN_AGV_DIST),让低优先级一方原地等待。
  // 让步规则:
  //   - 优先级高的一方继续执行(manual=5 > task-high=4 > task=3 > returning=2 > patrol=1)
  //   - 同级时 robotId 大的让步
  //   - 让步动作 = 调用该车的 _rollback(回退到上一帧位置 + 撤销本帧推进进度)
  //   - 让步车 status='avoiding', speed=0, L_spd/R_spd=0
  // 链式让步可能引发新冲突,迭代到稳定或 4 次封顶
  function resolveCollisions(fleetData) {
    if (!fleetData || fleetData.length < 2) return
    for (let iter = 0; iter < 4; iter++) {
      let changed = false
      for (let i = 0; i < fleetData.length; i++) {
        for (let j = i + 1; j < fleetData.length; j++) {
          const a = fleetData[i]
          const b = fleetData[j]
          if (!a.position || !b.position) continue
          const d = Math.hypot(a.position.x - b.position.x, a.position.z - b.position.z)
          if (d >= MIN_AGV_DIST) continue
          // 决定谁让
          const aPrio = a._priority || 0
          const bPrio = b._priority || 0
          let yielder
          if (aPrio !== bPrio) yielder = aPrio < bPrio ? a : b
          else yielder = a.id < b.id ? b : a // 同级:ID 大者让

          // 已经停了/已经被让过 — 跳过,避免死循环
          if (yielder._yielded) continue
          yielder._yielded = true
          if (typeof yielder._rollback === 'function') yielder._rollback()
          yielder.status = 'avoiding'
          yielder.carMode = 'avoid'
          yielder.speed = 0
          yielder.L_spd = 0
          yielder.R_spd = 0
          yielder.alertLevel = 'warning'
          changed = true
        }
      }
      if (!changed) break
    }

    // 把本帧最终位置写回 prevPositions,供下一帧回滚使用
    for (const r of fleetData) {
      if (r.position) prevPositions[r.id] = { x: r.position.x, z: r.position.z }
      // 清理一次性标记
      delete r._yielded
      delete r._rollback
    }
  }

  function startSimulation() {
    startTime.value = Date.now()
    let lastTick = Date.now()
    simTimer = setInterval(() => {
      const now = Date.now()
      const dt = (now - lastTick) / 1000
      lastTick = now
      const elapsed = now - startTime.value
      const simData = generateSimData(elapsed)

      if (manualDirection.value && manualDirection.value !== 'stop') {
        const activeId = selectedRobotId.value
        if (activeId && manualOverrides.value[activeId] && manualPositions.value[activeId]) {
          const pos = manualPositions.value[activeId]
          const speed = 0.3 * dt
          const dir = manualDirection.value
          if (dir === 'forward') pos.z -= speed
          else if (dir === 'back') pos.z += speed
          else if (dir === 'left') pos.x -= speed
          else if (dir === 'right') pos.x += speed
          pos.x = Math.max(-13, Math.min(13, pos.x))
          pos.z = Math.max(-10, Math.min(10, pos.z))
        }
      }

      const overrides = {
        overrides: { ...manualOverrides.value },
        positions: { ...manualPositions.value },
        direction: manualDirection.value
      }
      // 在巡逻 state 推进前快照,便于碰撞回滚
      for (let i = 0; i < config.robotCount; i++) {
        prevPatrolStates['robot_' + (i + 1)] = snapshotPatrolState(i)
      }
      const fleetData = generateFleetData(elapsed, config.robotCount, overrides, simData)

      // 默认所有车都是 patrol/manual driver,稍后任务/返航推进会覆盖
      for (const r of fleetData) {
        if (manualOverrides.value[r.id]) {
          r._driver = 'manual'
          r._priority = 5
        } else {
          r._driver = 'patrol'
          r._priority = 1
          // patrol 回滚:位置回到上一帧,patrol state 回到上一帧
          const idx = parseInt(r.id.replace('robot_', ''), 10) - 1
          const prevPos = prevPositions[r.id]
          const prevState = prevPatrolStates[r.id]
          r._rollback = () => {
            if (prevPos) r.position = { x: prevPos.x, z: prevPos.z }
            restorePatrolState(idx, prevState)
          }
        }
      }

      // ─── 任务调度 ───
      // 1) 给 pending 任务自动分配空闲 AGV(避开手动模式 / 返航中)
      assignPendingTasks(fleetData)
      // 2) 推进 running 任务,覆盖被占用 AGV 的位置/状态
      advanceRunningTasks(fleetData, dt)
      // 3) 推进返航中的 AGV(任务结束后驶回默认巡逻路径,避免瞬移)
      advanceReturningRobots(fleetData, dt)
      // 4) AGV 间避让 — 相距过近的低优先级一方原地等待
      resolveCollisions(fleetData)

      temperature.value = simData.temperature
      humidity.value = simData.humidity
      lux.value = simData.lux
      ps.value = simData.ps
      ir.value = simData.ir
      humanDetected.value = simData.humanDetected
      pirStatus.value = simData.pirStatus
      co2.value = simData.co2
      tvoc.value = simData.tvoc
      gasMic.value = simData.gasMic
      gasStatus.value = simData.gasStatus
      flameStatus.value = simData.flameStatus
      minDistanceCm.value = Math.min(simData.minDistanceCm, ...fleetData.map(r => r.distanceCm))
      minDistanceMm.value = Math.round(minDistanceCm.value * 10)
      minDistance.value = minDistanceCm.value
      goodsCount.value = simData.goodsCount
      goodsPulse.value = simData.goodsPulse
      counterDigits.value = simData.counterDigits
      fan.value = simData.fan
      led.value = simData.led
      buzzer.value = simData.buzzer
      alertLevel.value = simData.alertLevel
      linkedActionReason.value = simData.linkedActionReason
      linkage.value = simData.linkage
      fleet.value = fleetData

      for (const robotId in manualOverrides.value) {
        if (manualOverrides.value[robotId] && fleetData.length) {
          const robot = fleetData.find(r => r.id === robotId)
          if (robot && manualPositions.value[robotId]) {
            manualPositions.value[robotId].x = robot.position.x
            manualPositions.value[robotId].z = robot.position.z
          }
        }
      }

      updateAlarmEvents(simData, fleetData)
      if (simData.fan || simData.buzzer) {
        pushCommandLog('peripheral', `fan=${simData.fan};buzzer=${simData.buzzer}`, simData.linkedActionReason)
      }

      const dateNow = new Date()
      const label = `${String(dateNow.getHours()).padStart(2, '0')}:${String(dateNow.getMinutes()).padStart(2, '0')}:${String(dateNow.getSeconds()).padStart(2, '0')}`
      historyLabels.value.push(label)
      historyTemp.value.push(+simData.temperature.toFixed(1))
      historyHumi.value.push(+simData.humidity.toFixed(1))
      historyLux.value.push(+simData.lux.toFixed(0))
      historyCO2.value.push(+simData.co2.toFixed(0))
      historyTVOC.value.push(+simData.tvoc.toFixed(0))
      historyGasMic.value.push(+simData.gasMic.toFixed(0))
      historyGoodsCount.value.push(+simData.goodsCount)

      const maxHistoryPoints = config.maxDataPoints || 60
      if (historyLabels.value.length > maxHistoryPoints) {
        historyLabels.value.shift()
        historyTemp.value.shift()
        historyHumi.value.shift()
        historyLux.value.shift()
        historyCO2.value.shift()
        historyTVOC.value.shift()
        historyGasMic.value.shift()
        historyGoodsCount.value.shift()
      }

      lastUpdateTime.value = Date.now()
    }, config.chartUpdateInterval)
  }

  function stopSimulation() {
    if (simTimer) {
      clearInterval(simTimer)
      simTimer = null
    }
  }

  function setManualMode(robotId, enabled) {
    manualOverrides.value = { ...manualOverrides.value, [robotId]: enabled }
    if (enabled) {
      const robot = fleet.value.find(r => r.id === robotId)
      if (robot) {
        manualPositions.value = {
          ...manualPositions.value,
          [robotId]: { x: robot.position.x, z: robot.position.z }
        }
      }
    } else {
      const newPositions = { ...manualPositions.value }
      delete newPositions[robotId]
      manualPositions.value = newPositions
      if (selectedRobotId.value === robotId) {
        manualDirection.value = null
      }
    }
  }

  function moveRobot(direction) {
    manualDirection.value = direction
  }

  return {
    demoMode,
    online,
    isOnline,
    highestAlert,
    temperature,
    humidity,
    lux,
    ps,
    ir,
    humanDetected,
    pirStatus,
    co2,
    tvoc,
    gasMic,
    gasStatus,
    flameStatus,
    minDistance,
    minDistanceCm,
    minDistanceMm,
    goodsCount,
    goodsPulse,
    counterDigits,
    fan,
    led,
    buzzer,
    alertLevel,
    linkedActionReason,
    linkage,
    fleet,
    selectedRobotId,
    manualOverrides,
    manualDirection,
    historyLabels,
    historyTemp,
    historyHumi,
    historyLux,
    historyCO2,
    historyTVOC,
    historyGasMic,
    historyGoodsCount,
    alarmEvents,
    commandLogs,
    tasks,
    returningRobots,
    lastUpdateTime,
    connectionStatus,
    startSimulation,
    stopSimulation,
    setManualMode,
    moveRobot,
    dispatchTask,
    cancelTask,
    clearCompletedTasks
  }
})
