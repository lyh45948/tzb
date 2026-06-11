/**
 * 协议工具 - JSON消息构造与解析
 * 与后端 app/utils/protocol.py 对应
 */

import type { WSMessage, RealtimeData } from '@/types'

export const MessageType = {
  PING: 'ping',
  PONG: 'pong',
  CONNECT: 'connect',
  CONNECT_RESULT: 'connect_result',
  DISCONNECT: 'disconnect',
  DISCONNECT_RESULT: 'disconnect_result',
  CONTROL: 'control',
  CONTROL_RESULT: 'control_result',
  REALTIME: 'realtime',
  QUERY: 'query',
  QUERY_RESULT: 'query_result',
  DEMO_MODE: 'demo_mode',
  DEMO_MODE_RESULT: 'demo_mode_result',
  HEARTBEAT: 'heartbeat',
  ERROR: 'error',
  STATUS: 'status',
} as const

// 构造ping消息
export function createPing(): WSMessage {
  return { type: MessageType.PING }
}

// 构造连接请求
export function createConnectRequest(carIp: string, carPort = 7788, deviceId?: string): WSMessage {
  return {
    type: MessageType.CONNECT,
    carIp,
    carPort,
    deviceId: deviceId || `car_${carIp.replace(/\./g, '_')}`,
  }
}

// 构造断开请求
export function createDisconnectRequest(): WSMessage {
  return { type: MessageType.DISCONNECT }
}

// 构造控制命令
export function createControlCommand(command: Record<string, unknown>): WSMessage {
  return { type: MessageType.CONTROL, command }
}

// 构造演示模式切换
export function createDemoMode(enabled: boolean, deviceId = 'demo_car'): WSMessage {
  return { type: MessageType.DEMO_MODE, enabled, deviceId }
}

// 构造查询请求
export function createQueryRequest(action: string, params: Record<string, unknown> = {}): WSMessage {
  return { type: MessageType.QUERY, action, params }
}

// 构造心跳
export function createHeartbeat(): WSMessage {
  return { type: MessageType.HEARTBEAT }
}

// 解析消息
export function parseMessage(data: string): WSMessage | null {
  try {
    const msg = JSON.parse(data.trim())
    if (msg && typeof msg === 'object' && msg.type) {
      return msg as WSMessage
    }
    return null
  } catch {
    return null
  }
}

// 规范化小车数据
export function normalizeCarData(data: Record<string, unknown>): RealtimeData {
  const env = (data.env as Record<string, unknown>) || {}
  const agri = (env.agri as Record<string, unknown>) || {}

  return {
    carStatus: String(data.carStatus || 'off'),
    carMode: String(data.carMode || 'manual'),
    L_spd: Number(data.L_spd || 0),
    R_spd: Number(data.R_spd || 0),
    carPower: data.carPower != null ? Number(data.carPower) : null,
    distance: data.distance != null ? Number(data.distance) : null,
    env: {
      temp: env.temp != null ? Number(env.temp) : null,
      humi: env.humi != null ? Number(env.humi) : null,
      lux: env.lux != null ? Number(env.lux) : null,
      co2: env.co2 != null ? Number(env.co2) : null,
      tvoc: env.tvoc != null ? Number(env.tvoc) : null,
      gasStatus: env.gasStatus != null ? Number(env.gasStatus) : null,
      gasMic: env.gasMic != null ? Number(env.gasMic) : null,
      ps: env.ps != null ? Number(env.ps) : null,
      ir: env.ir != null ? Number(env.ir) : null,
      fan: Number(env.fan || 0),
      led: Number(env.led || 0),
      buzzer: Number(env.buzzer || 0),
      agri: agri ? {
        co2: Number(agri.co2 || 0),
        tvoc: Number(agri.tvoc || 0),
        gasStatus: Number(agri.gasStatus || 0),
        gasMic: Number(agri.gasMic || 0),
        flameStatus: Number(agri.flameStatus || 0),
      } : undefined,
    },
    imu: data.imu as RealtimeData['imu'],
    lidar: data.lidar as RealtimeData['lidar'],
    timestamp: data.timestamp as number || Date.now(),
  }
}
