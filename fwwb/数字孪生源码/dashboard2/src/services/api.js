/**
 * 后端 REST API 客户端
 *
 * 后端响应统一包装为 { code: 0, data, message }。
 * 这里所有方法都剥掉外层包装，直接返回 data；非 0 code 抛 ApiError。
 */
import config from '../config'

export class ApiError extends Error {
  constructor(message, { status, code, payload } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.payload = payload
  }
}

function joinUrl(base, path) {
  if (!base) return path
  if (base.endsWith('/') && path.startsWith('/')) return base + path.slice(1)
  if (!base.endsWith('/') && !path.startsWith('/')) return base + '/' + path
  return base + path
}

async function request(path, { signal, method = 'GET', body = null } = {}) {
  const url = joinUrl(config.apiBaseUrl, path)
  const init = { method, signal, credentials: 'omit', headers: {} }
  if (body !== null && body !== undefined) {
    init.headers['Content-Type'] = 'application/json'
    init.body = typeof body === 'string' ? body : JSON.stringify(body)
  }
  let res
  try {
    res = await fetch(url, init)
  } catch (e) {
    throw new ApiError(`请求失败: ${e.message}`, { status: 0 })
  }
  // 尝试解析 body —— 即使 status 非 2xx，后端通常也会回 { code, message }，能给到更可读的错误
  let parsed = null
  try {
    parsed = await res.json()
  } catch (_) {
    /* 没 body 或非 JSON */
  }
  if (parsed && typeof parsed === 'object' && 'code' in parsed) {
    if (parsed.code !== 0) {
      throw new ApiError(parsed.message || `HTTP ${res.status}`, {
        status: res.status,
        code: parsed.code,
        payload: parsed,
      })
    }
    return parsed.data
  }
  if (!res.ok) {
    throw new ApiError(`HTTP ${res.status}`, { status: res.status })
  }
  return parsed
}

export function fetchSnapshot(opts) {
  return request('/v1/dashboard/snapshot', opts)
}

export function fetchHistory(limit = 60, opts) {
  return request(`/v1/dashboard/history?limit=${encodeURIComponent(limit)}`, opts)
}

export function getStreamUrl() {
  return joinUrl(config.apiBaseUrl, '/v1/dashboard/stream')
}

// ─── 小车连接管理 ───
export function listCars(opts) {
  return request('/v1/agv/cars', opts)
}

export function connectCar({ carIp, carPort = 7788, deviceId } = {}, opts) {
  const body = { carIp, carPort }
  if (deviceId) body.deviceId = deviceId
  return request('/v1/agv/cars/connect', { ...opts, method: 'POST', body })
}

export function disconnectCar(deviceId, opts) {
  if (deviceId) {
    return request(`/v1/agv/cars/${encodeURIComponent(deviceId)}`, {
      ...opts,
      method: 'DELETE',
    })
  }
  return request('/v1/agv/cars', { ...opts, method: 'DELETE' })
}

// ─── 联动控制（风扇 / 阈值） ───
export function fetchLinkageConfig(opts) {
  return request('/v1/linkage/config', opts)
}

export function updateLinkageConfig(updates, opts) {
  return request('/v1/linkage/config', { ...opts, method: 'PUT', body: updates })
}

export function fetchFanStatus(opts) {
  return request('/v1/linkage/fan', opts)
}

/**
 * 手动设置风扇。
 * @param {Object} payload - { fan: 0|1 } 或 { gear: 0..3 }，可附 ttl: 秒
 */
export function setFanManual(payload, opts) {
  return request('/v1/linkage/fan', { ...opts, method: 'POST', body: payload })
}

// ─── 视觉：OpenMV GUI 实时画面 + 计数器开关 ───
/** 后端转发的 OpenMV 实时画面 URL（前端 <img> 直接 src 引用） */
export function getVisionFrameUrl() {
  return joinUrl(config.apiBaseUrl, '/v1/vision/frame.jpg')
}

/** 查询计数器识别开关状态 */
export function fetchCounterControl(opts) {
  return request('/v1/vision/counter/control', opts)
}

/** 控制计数器识别开/关（GUI 侧 1Hz 轮询此值自动启停） */
export function setCounterControl(enabled, opts) {
  return request('/v1/vision/counter/control', {
    ...opts,
    method: 'POST',
    body: { enabled: !!enabled },
  })
}

// ─── 车辆环境智能体 ───
export function fetchAgentStatus(opts) {
  return request('/v1/agent/status', opts)
}

export function fetchAgentAlerts(limit = 20, opts) {
  return request(`/v1/agent/alerts?limit=${encodeURIComponent(limit)}`, opts)
}

export function fetchAgentReports(type = 'daily', limit = 7, opts) {
  return request(
    `/v1/agent/reports?type=${encodeURIComponent(type)}&limit=${encodeURIComponent(limit)}`,
    opts,
  )
}

/** 手动触发：'analysis' | 'daily' | 'weekly' */
export function triggerAgent(type = 'analysis', opts) {
  return request(`/v1/agent/trigger?type=${encodeURIComponent(type)}`, {
    ...opts,
    method: 'POST',
  })
}
