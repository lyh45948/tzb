import { useState, useEffect, useRef } from 'react'
import { BarChart3, Thermometer, Droplets, Sun, Wind, Clock } from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'

type TimeRange = '1h' | '6h' | '24h'

export default function MonitorPage() {
  const { sensorData, carConnected, demoMode } = useAppStore()
  const [timeRange, setTimeRange] = useState<TimeRange>('1h')
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [history, setHistory] = useState<{ time: string; temp: number; humi: number; light: number; co2: number }[]>([])

  useEffect(() => {
    const handleMessage = (msg: Record<string, unknown>) => {
      if (msg.type === 'realtime' && msg.data) {
        const data = msg.data as Record<string, unknown>
        const env = (data.env as Record<string, number | null>) || {}
        const now = new Date()
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`

        if (env.temp != null && env.humi != null) {
          setHistory(prev => {
            const next = [...prev, {
              time: timeStr,
              temp: env.temp!,
              humi: env.humi!,
              light: env.lux ?? 0,
              co2: env.co2 ?? 0,
            }]
            return next.slice(-30)
          })
        }
      }
    }

    wsManager.onMessage(handleMessage)
    return () => wsManager.offMessage(handleMessage)
  }, [])

  // 绘制多线图
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

    const drawLine = (values: number[], max: number, color: string) => {
      ctx.strokeStyle = color
      ctx.lineWidth = 2
      ctx.beginPath()
      values.forEach((val, i) => {
        const x = (i / (values.length - 1)) * w
        const y = h - (val / max) * h
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      })
      ctx.stroke()
    }

    drawLine(history.map(h => h.temp), 50, '#f97316')
    drawLine(history.map(h => h.humi), 100, '#0ea5e9')
    drawLine(history.map(h => h.light), 2000, '#eab308')
    drawLine(history.map(h => h.co2), 2000, '#22c55e')

    // 图例
    const legends = [
      { color: '#f97316', label: '温度' },
      { color: '#0ea5e9', label: '湿度' },
      { color: '#eab308', label: '光照' },
      { color: '#22c55e', label: 'CO2' },
    ]
    legends.forEach((l, i) => {
      ctx.fillStyle = l.color
      ctx.fillRect(10 + i * 60, 10, 12, 12)
      ctx.fillStyle = '#374151'
      ctx.font = '12px sans-serif'
      ctx.fillText(l.label, 26 + i * 60, 20)
    })
  }, [history])

  const sensorCards = [
    { icon: Thermometer, label: '温度', value: sensorData.temperature, unit: '°C', color: 'bg-orange-100 text-orange-600' },
    { icon: Droplets, label: '湿度', value: sensorData.humidity, unit: '%', color: 'bg-blue-100 text-blue-600' },
    { icon: Sun, label: '光照', value: sensorData.light, unit: 'lux', color: 'bg-yellow-100 text-yellow-600' },
    { icon: Wind, label: 'CO2', value: sensorData.co2, unit: 'ppm', color: 'bg-green-100 text-green-600' },
  ]

  const disabled = !carConnected && !demoMode

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <BarChart3 className="w-6 h-6 text-sky-600" />
        环境监控
      </h2>

      {/* 时间范围 */}
      <div className="flex gap-2">
        {(['1h', '6h', '24h'] as TimeRange[]).map((r) => (
          <button
            key={r}
            onClick={() => setTimeRange(r)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              timeRange === r
                ? 'bg-sky-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <Clock className="w-3 h-3" />
            {r === '1h' ? '1小时' : r === '6h' ? '6小时' : '24小时'}
          </button>
        ))}
      </div>

      {/* 传感器数值 */}
      <div className="grid grid-cols-2 gap-3">
        {sensorCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 mb-2">
                <div className={`p-2 rounded-lg ${card.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className="text-sm text-gray-500">{card.label}</span>
              </div>
              <p className="text-2xl font-bold text-gray-800">
                {card.value != null ? card.value.toFixed(1) : '--'}
                <span className="text-sm text-gray-400 ml-1">{card.unit}</span>
              </p>
            </div>
          )
        })}
      </div>

      {/* 趋势图 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">多参数趋势</h3>
        <canvas
          ref={canvasRef}
          className="w-full bg-gray-50 rounded-lg"
          style={{ width: '100%', height: 220 }}
        />
      </div>

      {/* 设备状态 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">设备状态</h3>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-xs text-gray-500">风扇</p>
            <div className={`w-3 h-3 rounded-full mx-auto mt-1 ${sensorData.fan ? 'bg-green-500' : 'bg-gray-300'}`} />
          </div>
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-xs text-gray-500">LED</p>
            <div className={`w-3 h-3 rounded-full mx-auto mt-1 ${sensorData.led ? 'bg-green-500' : 'bg-gray-300'}`} />
          </div>
          <div className="bg-gray-50 rounded-lg p-2">
            <p className="text-xs text-gray-500">蜂鸣器</p>
            <div className={`w-3 h-3 rounded-full mx-auto mt-1 ${sensorData.buzzer ? 'bg-green-500' : 'bg-gray-300'}`} />
          </div>
        </div>
      </div>

      {disabled && (
        <div className="bg-yellow-50 rounded-xl p-4 text-center">
          <p className="text-yellow-700 text-sm">请先连接小车或开启演示模式</p>
        </div>
      )}
    </div>
  )
}
