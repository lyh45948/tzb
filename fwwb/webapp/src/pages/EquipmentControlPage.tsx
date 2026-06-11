import { useCallback, useEffect, useState } from 'react'
import {
  Radio,
  Fan,
  Lightbulb,
  Bell,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Octagon,
  Palette,
} from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'

export default function EquipmentControlPage() {
  const {
    deviceStatus,
    carConnected,
    demoMode,
    carStatus,
    updateDeviceStatus,
    cars,
    activeCarId,
  } = useAppStore()

  // RGB 本地状态
  const [rgb, setRgb] = useState({ r: 255, g: 255, b: 255 })
  const [rgbOn, setRgbOn] = useState(false)

  // 监听 WebSocket 消息更新设备状态（修复bug：风扇等设备打开后无法关闭）
  useEffect(() => {
    const handleMessage = (msg: Record<string, unknown>) => {
      if (msg.type === 'realtime' && msg.data) {
        const data = msg.data as Record<string, unknown>
        const env = (data.env as Record<string, unknown>) || {}

        updateDeviceStatus({
          fan: Boolean(env.fan),
          led: Boolean(env.led),
          buzzer: Boolean(env.buzzer),
          pump: false,
          valve: false,
        })

        // 同步 RGB 状态（如果后端上报了 rgb 数据）
        const envRgb = env.rgb as Record<string, number> | undefined
        if (envRgb) {
          setRgb({
            r: envRgb.r ?? 255,
            g: envRgb.g ?? 255,
            b: envRgb.b ?? 255,
          })
          setRgbOn(envRgb.r > 0 || envRgb.g > 0 || envRgb.b > 0)
        }
      }
    }

    wsManager.onMessage(handleMessage)
    return () => wsManager.offMessage(handleMessage)
  }, [updateDeviceStatus])

  const sendCommand = useCallback((cmd: Record<string, unknown>) => {
    if (!carConnected && !demoMode) return
    wsManager.sendControl(cmd, activeCarId || undefined)
  }, [carConnected, demoMode, activeCarId])

  const toggleDevice = useCallback((device: string, status: boolean) => {
    sendCommand({ [device]: status ? 1 : 0 })
  }, [sendCommand])

  const handleDirection = useCallback((dir: string) => {
    if (!carConnected && !demoMode) return
    wsManager.sendControl({ carStatus: dir }, activeCarId || undefined)
  }, [carConnected, demoMode, activeCarId])

  // RGB 控制
  const handleRgbChange = useCallback((channel: 'r' | 'g' | 'b', value: number) => {
    const newRgb = { ...rgb, [channel]: value }
    setRgb(newRgb)
    if (rgbOn) {
      sendCommand({ rgb: newRgb })
    }
  }, [rgb, rgbOn, sendCommand])

  const toggleRgb = useCallback(() => {
    const newOn = !rgbOn
    setRgbOn(newOn)
    if (newOn) {
      sendCommand({ rgb })
    } else {
      sendCommand({ rgb: { r: 0, g: 0, b: 0 } })
    }
  }, [rgbOn, rgb, sendCommand])

  const devices = [
    { key: 'fan', label: '风扇', icon: Fan, active: deviceStatus.fan },
    { key: 'led', label: 'LED灯', icon: Lightbulb, active: deviceStatus.led },
    { key: 'buzzer', label: '蜂鸣器', icon: Bell, active: deviceStatus.buzzer },
  ]

  const disabled = !carConnected && !demoMode

  const rgbColor = `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Radio className="w-6 h-6 text-sky-600" />
        设备控制
      </h2>

      {/* 小车选择器 */}
      {(cars.length > 0 || demoMode) && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500 mb-2">当前控制小车</p>
          <div className="flex items-center gap-2">
            <select
              value={activeCarId || ''}
              onChange={(e) => {
                const id = e.target.value
                if (id) wsManager.switchCar(id)
              }}
              disabled={disabled}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 outline-none disabled:opacity-50"
            >
              {demoMode && <option value="demo_car">演示小车</option>}
              {cars.filter(c => c.connected).map(car => (
                <option key={car.device_id} value={car.device_id}>
                  {car.device_id} ({car.car_ip})
                </option>
              ))}
            </select>
            {activeCarId && (
              <span className="px-2 py-1 bg-sky-50 text-sky-600 text-xs rounded-lg font-medium">
                {activeCarId}
              </span>
            )}
          </div>
        </div>
      )}

      {/* 设备开关 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">设备开关</h3>
        <div className="grid grid-cols-3 gap-3">
          {devices.map((dev) => {
            const Icon = dev.icon
            return (
              <button
                key={dev.key}
                onClick={() => toggleDevice(dev.key, !dev.active)}
                disabled={disabled}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl transition-all disabled:opacity-50 active:scale-95 ${
                  dev.active
                    ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/30'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
              >
                <Icon className="w-6 h-6" />
                <span className="text-sm font-medium">{dev.label}</span>
                <span className="text-xs opacity-70">{dev.active ? '开' : '关'}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* RGB 灯控制 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-700 flex items-center gap-2">
            <Palette className="w-5 h-5" />
            RGB 灯控制
          </h3>
          <button
            onClick={toggleRgb}
            disabled={disabled}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
              rgbOn
                ? 'bg-sky-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {rgbOn ? '关闭' : '开启'}
          </button>
        </div>

        {/* 颜色预览 */}
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-16 h-16 rounded-xl border-2 border-gray-200 shadow-inner transition-colors"
            style={{ backgroundColor: rgbOn ? rgbColor : '#e5e7eb' }}
          />
          <div className="text-sm text-gray-500">
            <p>R: {rgb.r}</p>
            <p>G: {rgb.g}</p>
            <p>B: {rgb.b}</p>
          </div>
        </div>

        {/* R/G/B 滑条 */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-red-500 w-4">R</span>
            <input
              type="range"
              min={0}
              max={255}
              value={rgb.r}
              onChange={(e) => handleRgbChange('r', Number(e.target.value))}
              disabled={disabled}
              className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-red-500 disabled:opacity-50"
            />
            <span className="text-xs text-gray-500 w-8 text-right">{rgb.r}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-green-500 w-4">G</span>
            <input
              type="range"
              min={0}
              max={255}
              value={rgb.g}
              onChange={(e) => handleRgbChange('g', Number(e.target.value))}
              disabled={disabled}
              className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-500 disabled:opacity-50"
            />
            <span className="text-xs text-gray-500 w-8 text-right">{rgb.g}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-blue-500 w-4">B</span>
            <input
              type="range"
              min={0}
              max={255}
              value={rgb.b}
              onChange={(e) => handleRgbChange('b', Number(e.target.value))}
              disabled={disabled}
              className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500 disabled:opacity-50"
            />
            <span className="text-xs text-gray-500 w-8 text-right">{rgb.b}</span>
          </div>
        </div>
      </div>

      {/* AGV 手动控制 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">AGV 手动控制</h3>
        <div className="grid grid-cols-3 gap-2 max-w-[200px] mx-auto">
          <div />
          <button
            onClick={() => handleDirection('run')}
            disabled={disabled}
            className="py-3 bg-sky-500 text-white rounded-lg font-medium hover:bg-sky-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            <ArrowUp className="w-5 h-5 mx-auto" />
          </button>
          <div />
          <button
            onClick={() => handleDirection('left')}
            disabled={disabled}
            className="py-3 bg-sky-500 text-white rounded-lg font-medium hover:bg-sky-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            <ArrowLeft className="w-5 h-5 mx-auto" />
          </button>
          <button
            onClick={() => handleDirection('stop')}
            disabled={disabled}
            className="py-3 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            <Octagon className="w-5 h-5 mx-auto" />
          </button>
          <button
            onClick={() => handleDirection('right')}
            disabled={disabled}
            className="py-3 bg-sky-500 text-white rounded-lg font-medium hover:bg-sky-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            <ArrowRight className="w-5 h-5 mx-auto" />
          </button>
          <div />
          <button
            onClick={() => handleDirection('back')}
            disabled={disabled}
            className="py-3 bg-sky-500 text-white rounded-lg font-medium hover:bg-sky-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            <ArrowDown className="w-5 h-5 mx-auto" />
          </button>
          <div />
        </div>
      </div>

      {/* 传感器状态 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">传感器状态</h3>
        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-xs text-gray-500">风扇</p>
            <div className={`w-3 h-3 rounded-full mx-auto mt-1 ${deviceStatus.fan ? 'bg-green-500' : 'bg-gray-300'}`} />
          </div>
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-xs text-gray-500">LED</p>
            <div className={`w-3 h-3 rounded-full mx-auto mt-1 ${deviceStatus.led ? 'bg-green-500' : 'bg-gray-300'}`} />
          </div>
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-xs text-gray-500">蜂鸣器</p>
            <div className={`w-3 h-3 rounded-full mx-auto mt-1 ${deviceStatus.buzzer ? 'bg-green-500' : 'bg-gray-300'}`} />
          </div>
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-xs text-gray-500">RGB</p>
            <div
              className="w-3 h-3 rounded-full mx-auto mt-1 border border-gray-200"
              style={{ backgroundColor: rgbOn ? rgbColor : '#d1d5db' }}
            />
          </div>
        </div>
      </div>

      {/* 小车状态 */}
      {carStatus.status !== 'off' && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-700 mb-2">小车状态</h3>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">运行状态</span>
            <span className="font-medium text-gray-800">{carStatus.status}</span>
          </div>
          <div className="flex items-center justify-between text-sm mt-1">
            <span className="text-gray-500">运行模式</span>
            <span className="font-medium text-gray-800">{carStatus.mode}</span>
          </div>
        </div>
      )}

      {disabled && (
        <div className="bg-yellow-50 rounded-xl p-4 text-center">
          <p className="text-yellow-700 text-sm">请先连接小车或开启演示模式</p>
        </div>
      )}
    </div>
  )
}
