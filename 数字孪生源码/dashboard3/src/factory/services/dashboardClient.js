/**
 * 数据接入编排器（live / polling / demo 状态机）
 *
 * 状态：
 *   idle        — 未启动
 *   live        — SSE 在线，接收推送
 *   polling     — SSE 失败，降级为定时轮询 /v1/dashboard/snapshot
 *   demo        — 后端完全不可用，前端本地模拟兜底
 *   disconnected— SSE 已彻底断开但还未触发降级（短暂状态）
 *
 * 切换：
 *   start: REST 拉初始 snapshot+history → 试 SSE
 *   SSE open      → live
 *   SSE 失败 N 次 → polling
 *   polling 失败 M 次 → demo（启动 store.startSimulation）
 *   live 恢复    → 关 polling/demo，回到 live
 */
import config from '../config'
import { fetchHistory, fetchSnapshot, ApiError } from './api'
import { connectDashboardStream } from './sseClient'
import { appendHistoryFromSnapshot, applyHistory, applySnapshot } from './dashboardAdapter'

export function createDashboardClient() {
  let store = null
  let sseConn = null
  let pollTimer = null
  let pollFailCount = 0
  let bootstrapTimer = null
  let started = false

  function setStatus(status) {
    if (!store) return
    if (store.connectionStatus !== status) {
      store.connectionStatus = status
    }
  }

  let cancelled = false  // stop() 被调用后置 true，阻止异步回调继续操作

  // ─── 公共 API ───
  async function start(targetStore) {
    if (started) return
    started = true
    cancelled = false
    store = targetStore
    setStatus('idle')

    // 先尝试一次 REST 引导：snapshot + history。任一失败都不阻塞 SSE 连接。
    await bootstrap()

    // stop() 可能在 bootstrap 期间被调用，此时不应继续建立 SSE
    if (cancelled || !started) return

    // 然后建立 SSE
    connectSse()
  }

  function stop() {
    cancelled = true
    started = false
    setStatus('idle')
    sseConn?.disconnect()
    sseConn = null
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (bootstrapTimer) {
      clearTimeout(bootstrapTimer)
      bootstrapTimer = null
    }
    // 如果之前进入 demo 模式，把它停掉
    try { store?.stopSimulation?.() } catch (_) { /* noop */ }
    store = null
  }

  // ─── 内部：初始引导 ───
  async function bootstrap() {
    try {
      const [snap, hist] = await Promise.all([
        fetchSnapshot().catch((e) => { throw e }),
        fetchHistory(config.maxDataPoints || 60).catch(() => null), // history 失败可降级
      ])
      // stop() 可能在 await 期间被调用
      if (cancelled || !store) return
      applySnapshot(store, snap)
      if (hist) applyHistory(store, hist)
      setStatus('live') // SSE 还没真的 open，先乐观置 live；SSE error 会改回去
    } catch (e) {
      // stop() 可能在 await 期间被调用
      if (cancelled || !store) return
      // bootstrap 失败 → 直接尝试 polling/demo 路径
      handleConnectFailure(e)
    }
  }

  // ─── 内部：SSE ───
  function connectSse() {
    sseConn?.disconnect()
    sseConn = connectDashboardStream({
      onSnapshot: (data) => {
        if (cancelled || !store) return
        applySnapshot(store, data)
        appendHistoryFromSnapshot(store, data)
        // 收到 SSE 帧 → 一定是 live；同步关掉降级路径
        if (store.connectionStatus !== 'live') {
          stopPolling()
          stopDemo()
          setStatus('live')
        }
      },
      onStatusChange: (sseStatus) => {
        if (cancelled || !store) return
        if (sseStatus === 'open') {
          stopPolling()
          stopDemo()
          setStatus('live')
        } else if (sseStatus === 'reconnecting') {
          // 短暂中断：先转 polling，避免大屏长时间不动
          startPolling()
          setStatus('polling')
        } else if (sseStatus === 'disconnected') {
          // 累计失败超过阈值 → 走 demo
          startPolling() // 仍保留 polling 作中间层；polling 也连续失败再进 demo
          setStatus('disconnected')
        }
      },
    })
  }

  // ─── 内部：轮询降级 ───
  function startPolling() {
    if (pollTimer) return
    pollFailCount = 0
    const interval = config.pollIntervalMs || 2000
    pollTimer = setInterval(pollOnce, interval)
    pollOnce() // 立即拉一次，避免等待
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    pollFailCount = 0
  }

  async function pollOnce() {
    if (cancelled || !store) return
    try {
      const snap = await fetchSnapshot()
      if (cancelled || !store) return
      applySnapshot(store, snap)
      appendHistoryFromSnapshot(store, snap)
      pollFailCount = 0
      // polling 成功 → 不再是 demo，但保持 polling 状态直到 SSE 恢复
      stopDemo()
      if (store.connectionStatus !== 'live') setStatus('polling')
    } catch (e) {
      if (cancelled || !store) return
      pollFailCount += 1
      const threshold = config.pollFailFallbackCount || 3
      if (pollFailCount >= threshold) {
        startDemo()
      }
    }
  }

  // ─── 内部：本地模拟兜底 ───
  function startDemo() {
    if (!store) return
    if (store.connectionStatus === 'demo') return
    try { store.startSimulation?.() } catch (_) { /* noop */ }
    setStatus('demo')
  }

  function stopDemo() {
    if (!store) return
    if (store.connectionStatus === 'demo') {
      try { store.stopSimulation?.() } catch (_) { /* noop */ }
    }
  }

  function handleConnectFailure(_e) {
    // bootstrap 整体失败 —— 直接进 polling 流程，让 polling/demo 决策
    startPolling()
    setStatus('polling')
  }

  return { start, stop, get status() { return store?.connectionStatus ?? 'idle' } }
}

// 便捷单例
export const dashboardClient = createDashboardClient()
