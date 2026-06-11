import { useRef, useState, useCallback, useEffect } from 'react'
import { Route, RotateCcw, Send, Square, Triangle, Circle } from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'

interface PathPoint {
  d: number  // distance in mm
  a: number  // angle in degrees
}

export default function PathPlanningPage() {
  const { carConnected, demoMode } = useAppStore()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [pathPoints, setPathPoints] = useState<PathPoint[]>([])
  const [drawing, setDrawing] = useState(false)
  const lastPoint = useRef<{ x: number; y: number } | null>(null)

  // Canvas setup
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

    // Clear and draw grid
    ctx.clearRect(0, 0, w, h)
    ctx.fillStyle = '#f9fafb'
    ctx.fillRect(0, 0, w, h)

    // Grid
    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    const gridSize = 20
    for (let x = 0; x <= w; x += gridSize) {
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, h)
      ctx.stroke()
    }
    for (let y = 0; y <= h; y += gridSize) {
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(w, y)
      ctx.stroke()
    }

    // Draw path
    if (pathPoints.length > 0) {
      const scale = 0.5 // mm to px
      let cx = w / 2
      let cy = h / 2
      let angle = -90 // start facing up

      ctx.strokeStyle = '#0ea5e9'
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      ctx.beginPath()
      ctx.moveTo(cx, cy)

      // Draw start point
      ctx.fillStyle = '#22c55e'
      ctx.beginPath()
      ctx.arc(cx, cy, 5, 0, Math.PI * 2)
      ctx.fill()

      pathPoints.forEach((pt) => {
        angle += pt.a
        const rad = (angle * Math.PI) / 180
        cx += pt.d * scale * Math.cos(rad)
        cy += pt.d * scale * Math.sin(rad)
        ctx.lineTo(cx, cy)
      })
      ctx.stroke()

      // Draw end point
      ctx.fillStyle = '#ef4444'
      ctx.beginPath()
      ctx.arc(cx, cy, 5, 0, Math.PI * 2)
      ctx.fill()
    }
  }, [pathPoints])

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    lastPoint.current = { x, y }
    setDrawing(true)
  }, [])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!drawing || !lastPoint.current) return
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const dx = x - lastPoint.current.x
    const dy = y - lastPoint.current.y
    const dist = Math.sqrt(dx * dx + dy * dy)

    if (dist > 20) {
      const angle = Math.atan2(dy, dx) * (180 / Math.PI) + 90
      setPathPoints(prev => [...prev, { d: Math.round(dist * 2), a: Math.round(angle) }])
      lastPoint.current = { x, y }
    }
  }, [drawing])

  const handlePointerUp = useCallback(() => {
    setDrawing(false)
    lastPoint.current = null
  }, [])

  const generateShape = useCallback((shape: 'square' | 'circle' | 'triangle') => {
    const points: PathPoint[] = []
    const size = 500 // mm

    if (shape === 'square') {
      points.push({ d: size, a: 0 })
      points.push({ d: size, a: 90 })
      points.push({ d: size, a: 90 })
      points.push({ d: size, a: 90 })
    } else if (shape === 'triangle') {
      points.push({ d: size, a: 0 })
      points.push({ d: size, a: 120 })
      points.push({ d: size, a: 120 })
    } else if (shape === 'circle') {
      const segments = 12
      const r = size / 2
      const stepAngle = 360 / segments
      const chord = 2 * r * Math.sin((stepAngle * Math.PI) / 360)
      for (let i = 0; i < segments; i++) {
        points.push({ d: Math.round(chord * 10), a: stepAngle })
      }
    }

    setPathPoints(points)
  }, [])

  const handleSendPath = useCallback(() => {
    if (!carConnected && !demoMode) return
    if (pathPoints.length === 0) return
    wsManager.sendControl({
      carMode: 'path',
      path: pathPoints,
    })
  }, [carConnected, demoMode, pathPoints])

  const handleClear = useCallback(() => {
    setPathPoints([])
  }, [])

  const disabled = !carConnected && !demoMode

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Route className="w-6 h-6 text-sky-600" />
        路径规划
      </h2>

      {/* 形状生成 */}
      <div className="flex gap-2">
        <button
          onClick={() => generateShape('square')}
          disabled={disabled}
          className="flex items-center gap-1 px-3 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 disabled:opacity-50"
        >
          <Square className="w-4 h-4" /> 方形
        </button>
        <button
          onClick={() => generateShape('triangle')}
          disabled={disabled}
          className="flex items-center gap-1 px-3 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 disabled:opacity-50"
        >
          <Triangle className="w-4 h-4" /> 三角形
        </button>
        <button
          onClick={() => generateShape('circle')}
          disabled={disabled}
          className="flex items-center gap-1 px-3 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200 disabled:opacity-50"
        >
          <Circle className="w-4 h-4" /> 圆形
        </button>
        <button
          onClick={handleClear}
          className="flex items-center gap-1 px-3 py-2 bg-red-50 text-red-600 rounded-lg text-sm hover:bg-red-100"
        >
          <RotateCcw className="w-4 h-4" /> 清空
        </button>
      </div>

      {/* 画布 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full cursor-crosshair touch-none"
          style={{ width: '100%', height: 300 }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        />
      </div>

      {/* 路径信息 */}
      {pathPoints.length > 0 && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <p className="text-sm text-gray-500 mb-2">路径点 ({pathPoints.length} 个)</p>
          <div className="max-h-32 overflow-y-auto text-xs space-y-1">
            {pathPoints.map((pt, i) => (
              <div key={i} className="flex justify-between bg-gray-50 rounded px-2 py-1">
                <span>点 {i + 1}</span>
                <span>距离: {pt.d}mm, 角度: {pt.a}°</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 发送按钮 */}
      <button
        onClick={handleSendPath}
        disabled={disabled || pathPoints.length === 0}
        className="w-full flex items-center justify-center gap-2 bg-sky-600 text-white py-3 rounded-xl font-medium hover:bg-sky-700 disabled:opacity-50 transition-colors"
      >
        <Send className="w-4 h-4" />
        发送路径
      </button>

      {disabled && (
        <div className="bg-yellow-50 rounded-xl p-4 text-center">
          <p className="text-yellow-700 text-sm">请先连接小车或开启演示模式</p>
        </div>
      )}
    </div>
  )
}
