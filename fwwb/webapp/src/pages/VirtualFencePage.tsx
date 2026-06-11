import { useRef, useState, useCallback, useEffect } from 'react'
import { Shield, ShieldAlert, RotateCcw, Save } from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'
import { storage, STORAGE_KEYS } from '@/utils/local-storage'

interface Fence {
  type: 'circle' | 'rect' | 'polygon'
  points: { x: number; y: number }[]
}

export default function VirtualFencePage() {
  const { carConnected, demoMode, carStatus } = useAppStore()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [fences, setFences] = useState<Fence[]>([])
  const [currentFence, setCurrentFence] = useState<Fence | null>(null)
  const [drawing, setDrawing] = useState(false)
  const [fenceType, setFenceType] = useState<'circle' | 'rect' | 'polygon'>('rect')
  const [savedFences, setSavedFences] = useState<Fence[]>([])
  const [violation, setViolation] = useState(false)
  const startPoint = useRef<{ x: number; y: number } | null>(null)

  // 航位推算位置
  const [carPos, setCarPos] = useState({ x: 150, y: 150 })

  useEffect(() => {
    const saved = storage.get<Fence[]>(STORAGE_KEYS.SAVED_FENCES, [])
    setSavedFences(saved)
  }, [])

  // 检查围栏违规
  useEffect(() => {
    if (fences.length === 0) return

    const checkViolation = () => {
      for (const fence of fences) {
        if (fence.type === 'circle' && fence.points.length === 2) {
          const center = fence.points[0]
          const edge = fence.points[1]
          const radius = Math.sqrt(
            Math.pow(edge.x - center.x, 2) + Math.pow(edge.y - center.y, 2)
          )
          const dist = Math.sqrt(
            Math.pow(carPos.x - center.x, 2) + Math.pow(carPos.y - center.y, 2)
          )
          if (dist > radius) {
            setViolation(true)
            // Auto stop
            if (carConnected || demoMode) {
              wsManager.sendControl({ carStatus: 'stop' })
            }
            return
          }
        }
        if (fence.type === 'rect' && fence.points.length === 2) {
          const p1 = fence.points[0]
          const p2 = fence.points[1]
          const minX = Math.min(p1.x, p2.x)
          const maxX = Math.max(p1.x, p2.x)
          const minY = Math.min(p1.y, p2.y)
          const maxY = Math.max(p1.y, p2.y)
          if (carPos.x < minX || carPos.x > maxX || carPos.y < minY || carPos.y > maxY) {
            setViolation(true)
            if (carConnected || demoMode) {
              wsManager.sendControl({ carStatus: 'stop' })
            }
            return
          }
        }
      }
      setViolation(false)
    }

    checkViolation()
  }, [carPos, fences, carConnected, demoMode])

  // 绘制
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
    ctx.fillStyle = '#f9fafb'
    ctx.fillRect(0, 0, w, h)

    // Grid
    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 1
    for (let x = 0; x <= w; x += 20) {
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, h)
      ctx.stroke()
    }
    for (let y = 0; y <= h; y += 20) {
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(w, y)
      ctx.stroke()
    }

    // Draw fences
    fences.forEach(fence => {
      ctx.strokeStyle = '#ef4444'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 5])

      if (fence.type === 'circle' && fence.points.length === 2) {
        const center = fence.points[0]
        const edge = fence.points[1]
        const radius = Math.sqrt(
          Math.pow(edge.x - center.x, 2) + Math.pow(edge.y - center.y, 2)
        )
        ctx.beginPath()
        ctx.arc(center.x, center.y, radius, 0, Math.PI * 2)
        ctx.stroke()
      } else if (fence.type === 'rect' && fence.points.length === 2) {
        const p1 = fence.points[0]
        const p2 = fence.points[1]
        ctx.strokeRect(p1.x, p1.y, p2.x - p1.x, p2.y - p1.y)
      } else if (fence.type === 'polygon') {
        ctx.beginPath()
        fence.points.forEach((pt, i) => {
          if (i === 0) ctx.moveTo(pt.x, pt.y)
          else ctx.lineTo(pt.x, pt.y)
        })
        ctx.closePath()
        ctx.stroke()
      }
      ctx.setLineDash([])
    })

    // Draw current fence being created
    if (currentFence && currentFence.points.length > 0) {
      ctx.strokeStyle = '#0ea5e9'
      ctx.lineWidth = 2
      ctx.setLineDash([3, 3])

      if (currentFence.type === 'circle' && currentFence.points.length === 2) {
        const center = currentFence.points[0]
        const edge = currentFence.points[1]
        const radius = Math.sqrt(
          Math.pow(edge.x - center.x, 2) + Math.pow(edge.y - center.y, 2)
        )
        ctx.beginPath()
        ctx.arc(center.x, center.y, radius, 0, Math.PI * 2)
        ctx.stroke()
      }
      ctx.setLineDash([])
    }

    // Draw car position
    ctx.fillStyle = violation ? '#ef4444' : '#22c55e'
    ctx.beginPath()
    ctx.arc(carPos.x, carPos.y, 6, 0, Math.PI * 2)
    ctx.fill()

    // Car direction indicator
    const angle = -Math.PI / 2
    ctx.strokeStyle = violation ? '#ef4444' : '#22c55e'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(carPos.x, carPos.y)
    ctx.lineTo(carPos.x + 15 * Math.cos(angle), carPos.y + 15 * Math.sin(angle))
    ctx.stroke()
  }, [fences, currentFence, carPos, violation])

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    startPoint.current = { x, y }
    setDrawing(true)

    if (fenceType === 'circle') {
      setCurrentFence({ type: 'circle', points: [{ x, y }] })
    } else if (fenceType === 'rect') {
      setCurrentFence({ type: 'rect', points: [{ x, y }] })
    }
  }, [fenceType])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!drawing || !startPoint.current || !currentFence) return
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    if (fenceType === 'circle') {
      setCurrentFence({ type: 'circle', points: [startPoint.current, { x, y }] })
    } else if (fenceType === 'rect') {
      setCurrentFence({ type: 'rect', points: [startPoint.current, { x, y }] })
    }
  }, [drawing, currentFence, fenceType])

  const handlePointerUp = useCallback(() => {
    if (!currentFence) return
    setDrawing(false)
    startPoint.current = null

    if (currentFence.points.length >= 2) {
      setFences(prev => [...prev, currentFence])
    }
    setCurrentFence(null)
  }, [currentFence])

  const handleSave = useCallback(() => {
    if (fences.length === 0) return
    storage.set(STORAGE_KEYS.SAVED_FENCES, fences)
    setSavedFences(fences)
  }, [fences])

  const handleClear = useCallback(() => {
    setFences([])
    setViolation(false)
  }, [])

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Shield className="w-6 h-6 text-sky-600" />
        虚拟围栏
      </h2>

      {/* 围栏类型 */}
      <div className="flex gap-2">
        {(['circle', 'rect', 'polygon'] as const).map(t => (
          <button
            key={t}
            onClick={() => setFenceType(t)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              fenceType === t
                ? 'bg-sky-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {t === 'circle' ? '圆形' : t === 'rect' ? '矩形' : '多边形'}
          </button>
        ))}
        <button
          onClick={handleSave}
          disabled={fences.length === 0}
          className="flex items-center gap-1 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm hover:bg-blue-100 disabled:opacity-50"
        >
          <Save className="w-4 h-4" /> 保存
        </button>
        <button
          onClick={handleClear}
          className="flex items-center gap-1 px-3 py-2 bg-red-50 text-red-600 rounded-lg text-sm hover:bg-red-100"
        >
          <RotateCcw className="w-4 h-4" /> 清空
        </button>
      </div>

      {/* 违规提示 */}
      {violation && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center gap-2 text-red-700">
          <ShieldAlert className="w-5 h-5" />
          <span className="font-medium">小车已离开围栏范围！已自动停车。</span>
        </div>
      )}

      {/* Canvas */}
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

      {/* 说明 */}
      <p className="text-xs text-gray-500">
        在画布上拖动绘制围栏。小车（绿色圆点）离开围栏区域时将自动停车。
      </p>

      {/* 已保存围栏 */}
      {savedFences.length > 0 && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-700 mb-2">已保存围栏</h3>
          <div className="text-sm text-gray-600">
            共 {savedFences.length} 个围栏
          </div>
        </div>
      )}
    </div>
  )
}
