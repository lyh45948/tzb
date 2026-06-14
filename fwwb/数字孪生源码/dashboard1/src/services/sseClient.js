/**
 * dashboard SSE 客户端 —— 自带指数退避重连
 *
 * 用法：
 *   const conn = connectDashboardStream({
 *     onSnapshot: data => applySnapshot(store, data),
 *     onStatusChange: s => console.log(s)  // 'open' | 'reconnecting' | 'disconnected'
 *   })
 *   conn.disconnect()
 */
import { getStreamUrl } from './api'

const MAX_BACKOFF_MS = 30_000

export function connectDashboardStream({
  onSnapshot,
  onStatusChange,
  failThreshold = 3,            // 累计连续失败次数达到后视为彻底掉线
} = {}) {
  let es = null
  let closed = false
  let retries = 0
  let backoffTimer = null

  function notify(status) {
    try {
      onStatusChange?.(status)
    } catch (_) {
      /* noop */
    }
  }

  function open() {
    if (closed) return
    try {
      es = new EventSource(getStreamUrl())
    } catch (e) {
      scheduleReconnect()
      return
    }

    es.addEventListener('open', () => {
      retries = 0
      notify('open')
    })

    es.addEventListener('snapshot', (event) => {
      if (!event.data) return
      try {
        const payload = JSON.parse(event.data)
        onSnapshot?.(payload)
      } catch (e) {
        // 单帧解析失败不影响连接
      }
    })

    // 心跳：仅用于保活，不需要做事，但收到说明连接正常
    es.addEventListener('ping', () => {
      if (retries !== 0) {
        retries = 0
        notify('open')
      }
    })

    es.addEventListener('error', () => {
      // 浏览器 EventSource 自带重连，但行为不可控；这里直接关闭后用退避策略重连
      try { es?.close() } catch (_) { /* noop */ }
      es = null
      if (closed) return
      scheduleReconnect()
    })
  }

  function scheduleReconnect() {
    retries += 1
    notify(retries >= failThreshold ? 'disconnected' : 'reconnecting')
    const delay = Math.min(MAX_BACKOFF_MS, 1000 * 2 ** Math.min(retries - 1, 5))
    if (backoffTimer) clearTimeout(backoffTimer)
    backoffTimer = setTimeout(() => {
      if (!closed) open()
    }, delay)
  }

  function disconnect() {
    closed = true
    if (backoffTimer) clearTimeout(backoffTimer)
    backoffTimer = null
    try { es?.close() } catch (_) { /* noop */ }
    es = null
  }

  open()
  return { disconnect }
}
