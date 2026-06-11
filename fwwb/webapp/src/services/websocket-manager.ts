/**
 * WebSocket 管理器 - 替代微信小程序的 udp-backend-manager.js
 * 与后端 WebSocket 服务通信，使用相同的 JSON 协议
 */

import {
  createPing,
  createConnectRequest,
  createDisconnectRequest,
  createControlCommand,
  createDemoMode,
  createQueryRequest,
  createHeartbeat,
  parseMessage,
  normalizeCarData,
} from '@/utils/protocol'
import type { WSMessage, RealtimeData } from '@/types'

type MessageCallback = (data: WSMessage) => void
type ConnectionCallback = (connected: boolean, message: string) => void

class WebSocketManager {
  private ws: WebSocket | null = null
  private url: string = ''
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 10
  private reconnectDelay: number = 1000
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private messageCallbacks: MessageCallback[] = []
  private connectionCallbacks: ConnectionCallback[] = []
  private _connected: boolean = false

  // 获取连接状态
  get connected(): boolean {
    return this._connected
  }

  // 连接 WebSocket
  connect(url: string): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] 已连接')
      return true
    }

    try {
      this.url = url
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('[WebSocket] 连接成功')
        this._connected = true
        this.reconnectAttempts = 0
        this._notifyConnectionChange(true, '连接成功')
        this._startHeartbeat()

        // 发送 ping 验证
        this._send(createPing())

        // 请求小车列表，恢复连接状态（刷新后重连用）
        this.getCarList()
      }

      this.ws.onmessage = (event) => {
        const msg = parseMessage(event.data)
        if (msg) {
          this._handleMessage(msg)
        }
      }

      this.ws.onclose = () => {
        console.log('[WebSocket] 连接关闭')
        this._connected = false
        this._stopHeartbeat()
        this._notifyConnectionChange(false, '连接已关闭')
        this._scheduleReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('[WebSocket] 连接错误:', error)
        this._connected = false
        this._notifyConnectionChange(false, '连接错误')
      }

      return true
    } catch (e) {
      console.error('[WebSocket] 创建连接失败:', e)
      this._connected = false
      this._notifyConnectionChange(false, '创建连接失败')
      return false
    }
  }

  // 断开连接
  disconnect(): void {
    this._stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.reconnectAttempts = this.maxReconnectAttempts // 阻止自动重连

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this._connected = false
    this._notifyConnectionChange(false, '已断开')
  }

  // 连接小车（通过后端转发）
  connectToCar(carIp: string, carPort = 7788, deviceId?: string): void {
    this._send(createConnectRequest(carIp, carPort, deviceId))
  }

  // 断开小车（可指定deviceId）
  disconnectFromCar(deviceId?: string): void {
    const msg: WSMessage = { type: 'disconnect' }
    if (deviceId) msg.deviceId = deviceId
    this._send(msg)
  }

  // 发送控制命令（可指定deviceId）
  sendControl(command: Record<string, unknown>, deviceId?: string): void {
    const msg: WSMessage = { type: 'control', command }
    if (deviceId) msg.deviceId = deviceId
    this._send(msg)
  }

  // 切换当前活跃小车
  switchCar(deviceId: string): void {
    this._send({ type: 'switch_car', deviceId } as WSMessage)
  }

  // 请求小车列表
  getCarList(): void {
    this._send({ type: 'car_list' } as WSMessage)
  }

  // 切换演示模式
  setDemoMode(enabled: boolean, deviceId = 'demo_car'): void {
    this._send(createDemoMode(enabled, deviceId))
  }

  // 查询历史数据
  queryHistory(action: string, params: Record<string, unknown> = {}): void {
    this._send(createQueryRequest(action, params))
  }

  // 发送原始消息
  sendRaw(msg: WSMessage): void {
    this._send(msg)
  }

  // 注册消息回调
  onMessage(callback: MessageCallback): void {
    if (!this.messageCallbacks.includes(callback)) {
      this.messageCallbacks.push(callback)
    }
  }

  // 取消注册消息回调
  offMessage(callback: MessageCallback): void {
    this.messageCallbacks = this.messageCallbacks.filter((cb) => cb !== callback)
  }

  // 注册连接状态回调
  onConnectionChange(callback: ConnectionCallback): void {
    if (!this.connectionCallbacks.includes(callback)) {
      this.connectionCallbacks.push(callback)
    }
  }

  // 取消注册连接状态回调
  offConnectionChange(callback: ConnectionCallback): void {
    this.connectionCallbacks = this.connectionCallbacks.filter((cb) => cb !== callback)
  }

  // 内部：发送消息
  private _send(msg: WSMessage): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(msg) + '\n')
        return true
      } catch (e) {
        console.error('[WebSocket] 发送失败:', e)
        return false
      }
    }
    console.warn('[WebSocket] 未连接，无法发送消息')
    return false
  }

  // 内部：处理接收到的消息
  private _handleMessage(msg: WSMessage): void {
    // 通知所有消息回调
    this.messageCallbacks.forEach((cb) => {
      try {
        cb(msg)
      } catch (e) {
        console.error('[WebSocket] 消息回调错误:', e)
      }
    })
  }

  // 内部：通知连接状态变化
  private _notifyConnectionChange(connected: boolean, message: string): void {
    this.connectionCallbacks.forEach((cb) => {
      try {
        cb(connected, message)
      } catch (e) {
        console.error('[WebSocket] 连接回调错误:', e)
      }
    })
  }

  // 内部：启动心跳
  private _startHeartbeat(): void {
    this._stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      this._send(createHeartbeat())
    }, 5000)
  }

  // 内部：停止心跳
  private _stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  // 内部：计划重连
  private _scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WebSocket] 达到最大重连次数')
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000)
    console.log(`[WebSocket] ${delay}ms 后尝试第 ${this.reconnectAttempts} 次重连`)

    this.reconnectTimer = setTimeout(() => {
      if (this.url) {
        this.connect(this.url)
      }
    }, delay)
  }
}

// 单例导出
export const wsManager = new WebSocketManager()
export default WebSocketManager
