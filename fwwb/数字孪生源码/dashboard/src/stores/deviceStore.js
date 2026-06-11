import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { generateSimData, generateFleetData } from '../utils/dataFormatter'
import config from '../config'

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
  const smartLight = ref({
    mode: 1,
    modeName: '自动',
    brightness: 50,
    targetBrightness: 70,
    timePeriod: 1,
    timePeriodName: '上午生产',
    lightLevel: 3,
    lightLevelName: '正常'
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

  // Chart history data
  const historyLabels = ref([])
  const historyTemp = ref([])
  const historyHumi = ref([])
  const historyLux = ref([])
  const historyCO2 = ref([])
  const historyTVOC = ref([])
  const historyGasMic = ref([])
  const historyGoodsCount = ref([])
  const historySmartLight = ref([])

  // Time tracking
  const lastUpdateTime = ref(Date.now())
  const startTime = ref(Date.now())

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
      const fleetData = generateFleetData(elapsed, config.robotCount, overrides, simData)

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
      smartLight.value = simData.smartLight
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
      historySmartLight.value.push(+simData.smartLight.brightness)

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
        historySmartLight.value.shift()
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
    smartLight,
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
    historySmartLight,
    alarmEvents,
    commandLogs,
    lastUpdateTime,
    startSimulation,
    stopSimulation,
    setManualMode,
    moveRobot
  }
})
