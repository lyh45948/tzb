import { useCallback } from 'react'
import { Mic, Power, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Octagon, Radar, Route, Fan, Thermometer, Droplets } from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'

// 语音指令映射（与小程序 voice_control 页面一致）
const voiceCommands = [
  { hex: '0x10', label: '电源开', icon: Power, action: () => ({ carStatus: 'on' }), color: 'bg-green-500' },
  { hex: '0x11', label: '电源关', icon: Power, action: () => ({ carStatus: 'off' }), color: 'bg-red-500' },
  { hex: '0x20', label: '前进', icon: ArrowUp, action: () => ({ carStatus: 'run' }), color: 'bg-blue-500' },
  { hex: '0x21', label: '后退', icon: ArrowDown, action: () => ({ carStatus: 'back' }), color: 'bg-blue-500' },
  { hex: '0x22', label: '左转', icon: ArrowLeft, action: () => ({ carStatus: 'left' }), color: 'bg-blue-500' },
  { hex: '0x23', label: '右转', icon: ArrowRight, action: () => ({ carStatus: 'right' }), color: 'bg-blue-500' },
  { hex: '0x24', label: '停止', icon: Octagon, action: () => ({ carStatus: 'stop' }), color: 'bg-red-600' },
  { hex: '0x30', label: '避障模式', icon: Radar, action: () => ({ carMode: 'avoid' }), color: 'bg-purple-500' },
  { hex: '0x31', label: '巡线模式', icon: Route, action: () => ({ carMode: 'line' }), color: 'bg-indigo-500' },
  { hex: '0x40', label: '方形路径', icon: Route, action: () => ({ carMode: 'path' }), color: 'bg-teal-500' },
  { hex: '0x41', label: '三角路径', icon: Route, action: () => ({ carMode: 'path' }), color: 'bg-teal-500' },
  { hex: '0x50', label: '风扇开', icon: Fan, action: () => ({ fan: 1 }), color: 'bg-cyan-500' },
  { hex: '0x51', label: '风扇关', icon: Fan, action: () => ({ fan: 0 }), color: 'bg-gray-500' },
  { hex: '0x60', label: '查询温湿度', icon: Thermometer, action: () => ({}), color: 'bg-orange-500' },
]

export default function VoiceControlPage() {
  const { carConnected, demoMode } = useAppStore()

  const handleCommand = useCallback((action: () => Record<string, unknown>) => {
    if (!carConnected && !demoMode) return
    const cmd = action()
    if (Object.keys(cmd).length > 0) {
      wsManager.sendControl(cmd)
    }
  }, [carConnected, demoMode])

  const disabled = !carConnected && !demoMode

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Mic className="w-6 h-6 text-sky-600" />
        语音控制
      </h2>

      <p className="text-sm text-gray-500">
        点击按钮发送对应的语音指令（模拟语音模块的十六进制命令）
      </p>

      <div className="grid grid-cols-2 gap-3">
        {voiceCommands.map((cmd) => {
          const Icon = cmd.icon
          return (
            <button
              key={cmd.hex}
              onClick={() => handleCommand(cmd.action)}
              disabled={disabled}
              className={`${cmd.color} text-white rounded-xl p-4 flex flex-col items-center gap-2 shadow-md hover:shadow-lg transition-shadow disabled:opacity-50 active:scale-95`}
            >
              <Icon className="w-6 h-6" />
              <span className="font-medium text-sm">{cmd.label}</span>
              <span className="text-xs opacity-70">{cmd.hex}</span>
            </button>
          )
        })}
      </div>

      {disabled && (
        <div className="bg-yellow-50 rounded-xl p-4 text-center">
          <p className="text-yellow-700 text-sm">请先连接小车或开启演示模式</p>
        </div>
      )}
    </div>
  )
}
