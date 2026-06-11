import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Power,
  PowerOff,
  Car,
  Gauge,
  RotateCcw,
  RotateCw,
  AlertTriangle,
} from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'
import Joystick from '@/components/controls/Joystick'

const modes = [
  { key: 'manual', label: '手动', icon: Car },
  { key: 'avoid', label: '避障', icon: AlertTriangle },
  { key: 'line', label: '巡线', icon: Car },
]

const speedGears = [
  { key: 'low', label: '低速', value: 'low' },
  { key: 'middle', label: '中速', value: 'middle' },
  { key: 'high', label: '高速', value: 'high' },
]

export default function ControlPage() {
  const { carConnected, carStatus, demoMode, cars, activeCarId } = useAppStore()
  const [powerOn, setPowerOn] = useState(false)
  const [currentMode, setCurrentMode] = useState('manual')
  const [speed, setSpeed] = useState('low')
  const [distance, setDistance] = useState<number | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const speedHistory = useRef<number[]>([])
  const directionTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const directionRef = useRef<string | null>(null)

  const sendCommand = useCallback((cmd: Record<string, unknown>) => {
    if (!carConnected && !demoMode) return
    wsManager.sendControl(cmd, activeCarId || undefined)
  }, [carConnected, demoMode, activeCarId])

  const clearDirectionHold = useCallback(() => {
    if (directionTimer.current) {
      clearInterval(directionTimer.current)
      directionTimer.current = null
    }
    directionRef.current = null
  }, [])

  const handlePowerToggle = useCallback(() => {
    const newPower = !powerOn
    if (!newPower) {
      clearDirectionHold()
    }
    setPowerOn(newPower)
    sendCommand({ carStatus: newPower ? 'on' : 'off' })
  }, [powerOn, clearDirectionHold, sendCommand])

  const handleModeChange = useCallback((mode: string) => {
    setCurrentMode(mode)
    sendCommand({ carMode: mode })
  }, [sendCommand])

  const handleSpeedChange = useCallback((s: string) => {
    setSpeed(s)
    sendCommand({ carSpeed: s })
  }, [sendCommand])

  const handleJoystickMove = useCallback((x: number, y: number) => {
    sendCommand({ joyX: x, joyY: y })
  }, [sendCommand])

  const handleJoystickEnd = useCallback(() => {
    sendCommand({ joyX: 0, joyY: 0 })
    sendCommand({ carStatus: 'stop' })
  }, [sendCommand])

  const stopHoldDirection = useCallback(() => {
    const wasHolding = directionTimer.current !== null || directionRef.current !== null
    clearDirectionHold()
    if (!wasHolding || !powerOn) return
    sendCommand({ carStatus: 'stop' })
  }, [powerOn, clearDirectionHold, sendCommand])

  const startHoldDirection = useCallback((dir: string) => {
    if (!powerOn) return
    clearDirectionHold()
    directionRef.current = dir
    sendCommand({ carStatus: dir })
    directionTimer.current = setInterval(() => {
      if (directionRef.current) {
        sendCommand({ carStatus: directionRef.current })
      }
    }, 200)
  }, [powerOn, clearDirectionHold, sendCommand])

  const handleStop = useCallback(() => {
    clearDirectionHold()
    if (!powerOn) return
    sendCommand({ carStatus: 'stop' })
  }, [powerOn, clearDirectionHold, sendCommand])

  const handleRotate = useCallback((dir: 'left' | 'right') => {
    if (!powerOn) return
    sendCommand({ carStatus: dir })
    setTimeout(() => sendCommand({ carStatus: 'stop' }), 500)
  }, [powerOn, sendCommand])

  useEffect(() => {
    return () => clearDirectionHold()
  }, [clearDirectionHold])

  // 速度图表绘制
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    // 清空
    ctx.clearRect(0, 0, width, height)

    // 绘制网格
    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    for (let i = 0; i <= 4; i++) {
      const y = (height / 4) * i
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(width, y)
      ctx.stroke()
    }

    // 绘制速度曲线
    const data = speedHistory.current
    if (data.length < 2) return

    ctx.strokeStyle = '#0ea5e9'
    ctx.lineWidth = 2
    ctx.beginPath()

    const maxSpeed = 1200
    data.forEach((val, i) => {
      const x = (i / (data.length - 1)) * width
      const y = height - (val / maxSpeed) * height
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.stroke()

    // 填充
    ctx.fillStyle = 'rgba(14, 165, 233, 0.1)'
    ctx.lineTo(width, height)
    ctx.lineTo(0, height)
    ctx.closePath()
    ctx.fill()
  }, [carStatus.L_spd, carStatus.R_spd])

  // 更新速度历史
  useEffect(() => {
    const avg = (carStatus.L_spd + carStatus.R_spd) / 2
    speedHistory.current.push(Math.abs(avg))
    if (speedHistory.current.length > 60) {
      speedHistory.current.shift()
    }
  }, [carStatus.L_spd, carStatus.R_spd])

  // 监听小车数据
  useEffect(() => {
    const handleMessage = (msg: Record<string, unknown>) => {
      if (msg.type === 'realtime' && msg.data) {
        const data = msg.data as Record<string, unknown>
        setDistance(data.distance != null ? Number(data.distance) : null)
      }
    }
    wsManager.onMessage(handleMessage)
    return () => wsManager.offMessage(handleMessage)
  }, [])

  const disabled = !carConnected && !demoMode

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Car className="w-6 h-6 text-sky-600" />
        小车控制
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

      {/* 电源开关 + 距离 */}
      <div className="flex items-center justify-between bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <button
          onClick={handlePowerToggle}
          disabled={disabled}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-white transition-all ${
            powerOn
              ? 'bg-red-500 hover:bg-red-600 shadow-lg shadow-red-500/30'
              : 'bg-green-500 hover:bg-green-600 shadow-lg shadow-green-500/30'
          } disabled:opacity-50 disabled:shadow-none`}
        >
          {powerOn ? (
            <>
              <PowerOff className="w-5 h-5" />
              关闭电源
            </>
          ) : (
            <>
              <Power className="w-5 h-5" />
              开启电源
            </>
          )}
        </button>

        <div className="text-right">
          <p className="text-xs text-gray-500">障碍物距离</p>
          <p className={`text-2xl font-bold ${
            distance != null && distance < 15 ? 'text-red-600' :
            distance != null && distance < 30 ? 'text-yellow-600' : 'text-gray-800'
          }`}>
            {distance != null ? `${distance} cm` : '--'}
          </p>
        </div>
      </div>

      {/* 模式选择 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <p className="text-sm text-gray-500 mb-2">运行模式</p>
        <div className="flex gap-2">
          {modes.map((m) => {
            const Icon = m.icon
            return (
              <button
                key={m.key}
                onClick={() => handleModeChange(m.key)}
                disabled={disabled || !powerOn}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  currentMode === m.key
                    ? 'bg-sky-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                } disabled:opacity-50`}
              >
                <Icon className="w-4 h-4" />
                {m.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* 速度档位 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <p className="text-sm text-gray-500 mb-2 flex items-center gap-1">
          <Gauge className="w-4 h-4" />
          速度档位
        </p>
        <div className="flex gap-2">
          {speedGears.map((s) => (
            <button
              key={s.key}
              onClick={() => handleSpeedChange(s.value)}
              disabled={disabled || !powerOn}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                speed === s.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              } disabled:opacity-50`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* 摇杆控制 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 flex flex-col items-center">
        <p className="text-sm text-gray-500 mb-3">摇杆控制</p>
        <Joystick
          onMove={handleJoystickMove}
          onEnd={handleJoystickEnd}
          disabled={disabled || !powerOn}
        />
        {powerOn && (
          <div className="mt-2 text-xs text-gray-400">
            左轮: {carStatus.L_spd} | 右轮: {carStatus.R_spd}
          </div>
        )}
      </div>

      {/* 方向按钮 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <p className="text-sm text-gray-500 mb-3">方向控制</p>
        <div className="grid grid-cols-3 gap-2 max-w-[200px] mx-auto">
          <div />
          <button
            onPointerDown={(e) => {
              e.preventDefault()
              startHoldDirection('run')
            }}
            onPointerUp={(e) => {
              e.preventDefault()
              stopHoldDirection()
            }}
            onPointerLeave={stopHoldDirection}
            onPointerCancel={stopHoldDirection}
            disabled={disabled || !powerOn}
            className="py-3 bg-sky-500 text-white rounded-lg font-medium hover:bg-sky-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            前
          </button>
          <div />
          <button
            onPointerDown={(e) => {
              e.preventDefault()
              startHoldDirection('left')
            }}
            onPointerUp={(e) => {
              e.preventDefault()
              stopHoldDirection()
            }}
            onPointerLeave={stopHoldDirection}
            onPointerCancel={stopHoldDirection}
            disabled={disabled || !powerOn}
            className="py-3 bg-sky-500 text-white rounded-lg font-medium hover:bg-sky-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            左
          </button>
          <button
            onClick={handleStop}
            disabled={disabled || !powerOn}
            className="py-3 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            停
          </button>
          <button
            onPointerDown={(e) => {
              e.preventDefault()
              startHoldDirection('right')
            }}
            onPointerUp={(e) => {
              e.preventDefault()
              stopHoldDirection()
            }}
            onPointerLeave={stopHoldDirection}
            onPointerCancel={stopHoldDirection}
            disabled={disabled || !powerOn}
            className="py-3 bg-sky-500 text-white rounded-lg font-medium hover:bg-sky-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            右
          </button>
          <div />
          <button
            onPointerDown={(e) => {
              e.preventDefault()
              startHoldDirection('back')
            }}
            onPointerUp={(e) => {
              e.preventDefault()
              stopHoldDirection()
            }}
            onPointerLeave={stopHoldDirection}
            onPointerCancel={stopHoldDirection}
            disabled={disabled || !powerOn}
            className="py-3 bg-sky-500 text-white rounded-lg font-medium hover:bg-sky-600 disabled:opacity-50 active:scale-95 transition-transform"
          >
            后
          </button>
          <div />
        </div>

        {/* 旋转按钮 */}
        <div className="flex gap-2 mt-3 max-w-[200px] mx-auto">
          <button
            onClick={() => handleRotate('left')}
            disabled={disabled || !powerOn}
            className="flex-1 flex items-center justify-center gap-1 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
            左转
          </button>
          <button
            onClick={() => handleRotate('right')}
            disabled={disabled || !powerOn}
            className="flex-1 flex items-center justify-center gap-1 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
          >
            <RotateCw className="w-4 h-4" />
            右转
          </button>
        </div>
      </div>

      {/* 速度图表 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <p className="text-sm text-gray-500 mb-2">实时速度</p>
        <canvas
          ref={canvasRef}
          className="w-full h-24 bg-gray-50 rounded-lg"
          style={{ width: '100%', height: 96 }}
        />
      </div>
    </div>
  )
}
