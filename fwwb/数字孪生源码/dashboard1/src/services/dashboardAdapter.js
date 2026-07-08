/**
 * 后端 dashboard 数据 → 前端 deviceStore 的适配层
 *
 * 字段映射依据：/v1/dashboard/snapshot 响应与 deviceStore.js state 几乎一一对应，
 * 这里只做轻量的归一化与"保留前端本地状态"的合并。
 *
 * CO2→CO 映射已由后端完成（dashboard_service._co2_to_co），前端直接使用
 * snapshot.co 字段，不再做转换。
 */
import config from '../config'

/**
 * 把 /v1/dashboard/snapshot 的 data 写入 store。
 * 不会覆盖前端本地状态：tasks、returningRobots、selectedRobotId、
 * manualOverrides、manualDirection 以及 fleet[i] 上的任务/返航字段。
 */
export function applySnapshot(store, snapshot) {
  if (!snapshot || typeof snapshot !== 'object') return

  // ─── 顶层环境/外设/告警 ───
  if ('online' in snapshot) store.online = !!snapshot.online
  setIfPresent(store, 'temperature', snapshot.temperature)
  setIfPresent(store, 'humidity', snapshot.humidity)
  setIfPresent(store, 'lux', snapshot.lux)
  setIfPresent(store, 'ps', snapshot.ps)
  setIfPresent(store, 'ir', snapshot.ir)
  setIfPresent(store, 'humanDetected', snapshot.humanDetected)
  setIfPresent(store, 'pirStatus', snapshot.pirStatus)
  // 后端已提供 co（CO2→CO 映射后的值），直接使用
  setIfPresent(store, 'co', snapshot.co)
  setIfPresent(store, 'co2', snapshot.co2)
  setIfPresent(store, 'tvoc', snapshot.tvoc)
  setIfPresent(store, 'gasMic', snapshot.gasMic)
  setIfPresent(store, 'gasStatus', snapshot.gasStatus)
  setIfPresent(store, 'flameStatus', snapshot.flameStatus)
  setIfPresent(store, 'minDistance', snapshot.minDistance)
  setIfPresent(store, 'minDistanceCm', snapshot.minDistanceCm)
  setIfPresent(store, 'minDistanceMm', snapshot.minDistanceMm)
  setIfPresent(store, 'goodsCount', snapshot.goodsCount)
  setIfPresent(store, 'goodsPulse', snapshot.goodsPulse)
  setIfPresent(store, 'counterDigits', snapshot.counterDigits)
  setIfPresent(store, 'fan', snapshot.fan)
  setIfPresent(store, 'led', snapshot.led)
  setIfPresent(store, 'buzzer', snapshot.buzzer)
  setIfPresent(store, 'alertLevel', snapshot.alertLevel)
  setIfPresent(store, 'linkedActionReason', snapshot.linkedActionReason)

  // ─── linkage（结构相同，直接替换；带 thresholds 等额外字段也无害） ───
  if (snapshot.linkage && typeof snapshot.linkage === 'object') {
    store.linkage = snapshot.linkage
  }

  // ─── alarmEvents（结构相同） ───
  if (Array.isArray(snapshot.alarmEvents)) {
    store.alarmEvents = snapshot.alarmEvents
  }

  // ─── commandLogs（后端已补齐 command/is_simulated/result/reason；这里再兜底） ───
  if (Array.isArray(snapshot.commandLogs)) {
    store.commandLogs = snapshot.commandLogs.map(normalizeCommandLog)
  }

  // ─── aiAgent（车辆环境智能体快照） ───
  if (snapshot.aiAgent && typeof snapshot.aiAgent === 'object') {
    store.aiAgent = snapshot.aiAgent
  }

  // ─── fleet（合并：保留前端任务/返航局部字段） ───
  if (Array.isArray(snapshot.fleet)) {
    store.fleet = mergeFleet(store.fleet, snapshot.fleet)

    // 同时滚动一次最近距离（若后端没给）
    if (snapshot.minDistanceCm == null && store.fleet.length) {
      const min = store.fleet.reduce(
        (m, r) => (Number.isFinite(r.distanceCm) && r.distanceCm < m ? r.distanceCm : m),
        Infinity
      )
      if (Number.isFinite(min)) {
        store.minDistanceCm = min
        store.minDistanceMm = Math.round(min * 10)
        store.minDistance = min
      }
    }
  }

  // ─── 时间戳 ───
  if (snapshot.timestamp) {
    store.lastUpdateTime = snapshot.timestamp
  } else {
    store.lastUpdateTime = Date.now()
  }
}

/**
 * 把 /v1/dashboard/history 的 { labels, items } 拆成 store 里的多条数组。
 */
export function applyHistory(store, history) {
  if (!history || !Array.isArray(history.items)) return
  const items = history.items
  const labels = Array.isArray(history.labels) && history.labels.length === items.length
    ? history.labels
    : items.map((it) => it.label || '')

  const max = config.maxDataPoints || 60
  const sliced = items.slice(-max)
  const slicedLabels = labels.slice(-max)

  // 后端 /v1/dashboard/history 当前是占位实现：返回 60 条**完全相同**的当前快照。
  // 这种"扁平"历史会让图表显示成一条直线，反而误导。
  // 探测一下：如果 temperature/humidity 在整段历史里完全没变化（最大-最小=0），
  // 就丢弃这段历史，让前端从 SSE/polling 自己累积。
  const flat =
    sliced.length > 1 &&
    sliced.every((it) => +it.temperature === +sliced[0].temperature) &&
    sliced.every((it) => +it.humidity === +sliced[0].humidity)
  if (flat) {
    // 重置为空数组，后续每次 SSE/polling 通过 appendHistoryFromSnapshot 累积
    store.historyLabels = []
    store.historyTemp = []
    store.historyHumi = []
    store.historyLux = []
    store.historyCO2 = []
    store.historyTVOC = []
    store.historyGasMic = []
    store.historyGoodsCount = []
    return
  }

  store.historyLabels = slicedLabels
  store.historyTemp = sliced.map((it) => +(+it.temperature).toFixed(1) || 0)
  store.historyHumi = sliced.map((it) => +(+it.humidity).toFixed(1) || 0)
  store.historyLux = sliced.map((it) => round1(it.lux))
  store.historyCO2 = sliced.map((it) => +Number(it.co).toFixed(1) || 0)
  store.historyTVOC = sliced.map((it) => Math.round(+it.tvoc) || 0)
  store.historyGasMic = sliced.map((it) => Math.round(+it.gasMic) || 0)
  store.historyGoodsCount = sliced.map((it) => Math.round(+it.goodsCount) || 0)
}

/**
 * 把刚到的一帧 snapshot 的环境数据 push 到 history 数组尾部，做滚动窗口。
 * 用于 SSE 模式 —— 前端不再每秒额外请求 /history，自己累计就行。
 */
export function appendHistoryFromSnapshot(store, snapshot) {
  if (!snapshot) return
  const max = config.maxDataPoints || 60
  const ts = snapshot.timestamp ? new Date(snapshot.timestamp) : new Date()
  const label = `${pad2(ts.getHours())}:${pad2(ts.getMinutes())}:${pad2(ts.getSeconds())}`

  push(store, 'historyLabels', label, max)
  push(store, 'historyTemp', round1(snapshot.temperature), max)
  push(store, 'historyHumi', round1(snapshot.humidity), max)
  push(store, 'historyLux', round1(snapshot.lux), max)
  push(store, 'historyCO2', +Number(snapshot.co).toFixed(1), max)
  push(store, 'historyTVOC', roundInt(snapshot.tvoc), max)
  push(store, 'historyGasMic', roundInt(snapshot.gasMic), max)
  push(store, 'historyGoodsCount', roundInt(snapshot.goodsCount), max)
}

// ─── 内部工具 ───

function setIfPresent(store, key, value) {
  if (value === undefined || value === null) return
  store[key] = value
}

function pad2(n) {
  return String(n).padStart(2, '0')
}

function round1(v) {
  const n = Number(v)
  return Number.isFinite(n) ? +n.toFixed(1) : 0
}

function roundInt(v) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.round(n) : 0
}

function push(store, key, value, max) {
  const arr = Array.isArray(store[key]) ? [...store[key], value] : [value]
  while (arr.length > max) arr.shift()
  store[key] = arr
}

function normalizeCommandLog(item) {
  if (!item || typeof item !== 'object') return item
  // 后端 1.5 改造后已补齐 command 等字段；这里只做兜底
  if (item.command == null && item.command_data != null) {
    let cmd = ''
    try {
      cmd = typeof item.command_data === 'string'
        ? item.command_data
        : JSON.stringify(item.command_data)
    } catch (_) {
      cmd = String(item.command_data)
    }
    return { ...item, command: cmd }
  }
  return item
}

/**
 * 合并 fleet：以 device_id (回退到 id) 为主键，把后端字段套到现有数组项上，
 * 保留前端本地维护的任务/返航字段（taskId/taskFrom/taskTo/taskProgress/returning/_driver/_priority/_rollback）。
 */
function mergeFleet(prevFleet = [], nextFleet = []) {
  const prevMap = new Map()
  for (const r of prevFleet || []) {
    const key = r?.device_id || r?.id
    if (key) prevMap.set(key, r)
  }

  return nextFleet.map((incoming) => {
    const key = incoming?.device_id || incoming?.id
    const prev = key ? prevMap.get(key) : null
    const last_receive_time =
      typeof incoming.last_receive_time === 'string'
        ? Date.parse(incoming.last_receive_time) || null
        : incoming.last_receive_time
    const merged = {
      ...incoming,
      last_receive_time,
    }
    if (prev) {
      // 这些字段是前端任务/返航循环维护的局部状态，不能被后端覆盖
      if (prev.taskId !== undefined) merged.taskId = prev.taskId
      if (prev.taskFrom !== undefined) merged.taskFrom = prev.taskFrom
      if (prev.taskTo !== undefined) merged.taskTo = prev.taskTo
      if (prev.taskProgress !== undefined) merged.taskProgress = prev.taskProgress
      if (prev.returning !== undefined) merged.returning = prev.returning
    }
    return merged
  })
}
