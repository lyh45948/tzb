import { useState, useEffect, useRef, useCallback } from 'react'
import { Leaf, Thermometer, Droplets, Sun, Wind, Gauge } from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'

export default function EnvironmentPage() {
  const { sensorData, carConnected, demoMode, thresholds, updateSensorData } = useAppStore()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [history, setHistory] = useState<{ timestamp: number; temp: number; humi: number }[]>([])

  // 监听数据更新
  useEffect(() => {
    const handleMessage = (msg: Record<string, unknown>) => {
      if (msg.type === 'realtime' && msg.data) {
        const data = msg.data as Record<string, unknown>
        const env = (data.env as Record<string, number | null>) || {}

        // 同步更新 store 中的传感器数据（让数值卡片实时刷新）
        updateSensorData({
          temperature: env.temp ?? null,
          humidity: env.humi ?? null,
          light: env.lux ?? null,
          co2: env.co2 ?? null,
          tvoc: env.tvoc ?? null,
          gasMic: env.gasMic ?? null,
        })

        // 更新历史数据用于图表
        if (env.temp != null && env.humi != null) {
          setHistory(prev => {
            const next = [...prev, { timestamp: Date.now(), temp: env.temp!, humi: env.humi! }]
            return next.slice(-60)
          })
        }
      }
    }
    wsManager.onMessage(handleMessage)
    return () => wsManager.offMessage(handleMessage)
  }, [updateSensorData])

  // 绘制实时图表
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const w = canvas.clientWidth
    const h = canvas.clientHeight
    canvas.width = w * dpr
    canvas.height = h * dpr
    ctx.scale(dpr, dpr)

    ctx.clearRect(0, 0, w, h)

    if (history.length < 2) {
      ctx.fillStyle = '#9ca3af'
      ctx.font = '14px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('等待数据...', w / 2, h / 2)
      return
    }

    // 网格
    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    for (let i = 0; i <= 4; i++) {
      const y = (h / 4) * i
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(w, y)
      ctx.stroke()
    }

    const maxTemp = 50
    const maxHumi = 100

    // 温度曲线
    ctx.strokeStyle = '#f97316'
    ctx.lineWidth = 2
    ctx.beginPath()
    history.forEach((pt, i) => {
      const x = (i / (history.length - 1)) * w
      const y = h - (pt.temp / maxTemp) * h
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.stroke()

    // 湿度曲线
    ctx.strokeStyle = '#0ea5e9'
    ctx.lineWidth = 2
    ctx.beginPath()
    history.forEach((pt, i) => {
      const x = (i / (history.length - 1)) * w
      const y = h - (pt.humi / maxHumi) * h
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.stroke()

    // 图例
    ctx.font = '12px sans-serif'
    ctx.fillStyle = '#f97316'
    ctx.fillText('温度', 10, 15)
    ctx.fillStyle = '#0ea5e9'
    ctx.fillText('湿度', 50, 15)
  }, [history])

  const sensorItems = [
    { icon: Thermometer, label: '温度', value: sensorData.temperature, unit: '°C', warning: thresholds.tempWarning, danger: thresholds.tempDanger, color: 'text-orange-500' },
    { icon: Droplets, label: '湿度', value: sensorData.humidity, unit: '%', warning: thresholds.humiWarning, danger: thresholds.humiDanger, color: 'text-blue-500' },
    { icon: Sun, label: '光照', value: sensorData.light, unit: 'lux', color: 'text-yellow-500' },
    { icon: Wind, label: 'CO2', value: sensorData.co2, unit: 'ppm', warning: thresholds.co2Warning, danger: thresholds.co2Danger, color: 'text-green-500' },
    { icon: Gauge, label: 'TVOC', value: sensorData.tvoc, unit: 'ppb', color: 'text-purple-500' },
    { icon: Leaf, label: '气体浓度', value: sensorData.gasMic, unit: '', warning: thresholds.smokeWarning, danger: thresholds.smokeDanger, color: 'text-red-500' },
  ]

  const disabled = !carConnected && !demoMode

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Leaf className="w-6 h-6 text-sky-600" />
        环境监控
      </h2>

      {/* 传感器数值 */}
      <div className="grid grid-cols-2 gap-3">
        {sensorItems.map((item) => {
          const Icon = item.icon
          const isWarning = item.warning != null && item.value != null && item.value >= item.warning
          const isDanger = item.danger != null && item.value != null && item.value >= item.danger

          return (
            <div
              key={item.label}
              className={`bg-white rounded-xl p-4 shadow-sm border ${
                isDanger ? 'border-red-300 bg-red-50' :
                isWarning ? 'border-yellow-300 bg-yellow-50' :
                'border-gray-100'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <Icon className={`w-5 h-5 ${item.color}`} />
                {isDanger && <span className="text-xs px-2 py-0.5 bg-red-500 text-white rounded-full">危险</span>}
                {isWarning && !isDanger && <span className="text-xs px-2 py-0.5 bg-yellow-500 text-white rounded-full">警告</span>}
              </div>
              <p className="text-xs text-gray-500">{item.label}</p>
              <p className="text-2xl font-bold text-gray-800">
                {item.value != null ? item.value.toFixed(1) : '--'}
                <span className="text-sm text-gray-400 ml-1">{item.unit}</span>
              </p>
            </div>
          )
        })}
      </div>

      {/* 实时图表 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">温湿度趋势</h3>
        <canvas
          ref={canvasRef}
          className="w-full bg-gray-50 rounded-lg"
          style={{ width: '100%', height: 200 }}
        />
      </div>

      {disabled && (
        <div className="bg-yellow-50 rounded-xl p-4 text-center">
          <p className="text-yellow-700 text-sm">请先连接小车或开启演示模式以查看实时数据</p>
        </div>
      )}
    </div>
  )
}
