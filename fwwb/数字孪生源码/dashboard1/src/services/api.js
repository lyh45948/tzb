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
