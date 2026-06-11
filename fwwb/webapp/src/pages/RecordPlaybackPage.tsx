import { useRef, useState, useCallback, useEffect } from 'react'
import { Play, Square, RotateCcw, Save, Disc3 } from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'
import { storage, STORAGE_KEYS } from '@/utils/local-storage'

interface RecordedPath {
  name: string
  points: { x: number; y: number }[]
  timestamp: number
}

export default function RecordPlaybackPage() {
  const { carConnected, demoMode, carStatus } = useAppStore()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [recording, setRecording] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [path, setPath] = useState<{ x: number; y: number }[]>([])
  const [savedPaths, setSavedPaths] = useState<RecordedPath[]>([])
  const playbackIndex = useRef(0)
  const recordStart = useRef<{ x: number; y: number } | null>(null)

  // 航位推算位置
  const [position, setPosition] = useState({ x: 0, y: 0, angle: -90 })

  // 加载保存的路径
  useEffect(() => {
    const saved = storage.get<RecordedPath[]>(STORAGE_KEYS.SAVED_PATHS, [])
    setSavedPaths(saved)
  }, [])

  // 航位推算
  useEffect(() => {
    if (!recording) return

    const dt = 0.1 // 100ms
    const scale = 0.01 // mm/s to px per dt
    const WHEEL_BASELINE = 286 // mm

    const L = carStatus.L_spd * scale * dt
    const R = carStatus.R_spd * scale * dt

    setPosition(prev => {
      const newPos = { ...prev }
      if (Math.abs(L - R) < 0.001) {
        // Straight
        const rad = (newPos.angle * Math.PI) / 180
        newPos.x += L * Math.cos(rad)
        newPos.y += L * Math.sin(rad)
      } else {
        // Turn
        const R_turn = (WHEEL_BASELINE * (L + R)) / (2 * (R - L))
        const omega = (R - L) / WHEEL_BASELINE
        const deltaAngle = (omega * 180) / Math.PI
        newPos.angle += deltaAngle
        const rad = (newPos.angle * Math.PI) / 180
        newPos.x += R_turn * (Math.sin((newPos.angle * Math.PI) / 180) - Math.sin(((newPos.angle - deltaAngle) * Math.PI) / 180))
        newPos.y -= R_turn * (Math.cos((newPos.angle * Math.PI) / 180) - Math.cos(((newPos.angle - deltaAngle) * Math.PI) / 180))
      }
      return newPos
    })
  }, [carStatus.L_spd, carStatus.R_spd, recording])

  // 记录路径
  useEffect(() => {
    if (recording) {
      setPath(prev => [...prev, { x: position.x, y: position.y }])
    }
  }, [position, recording])

  // 绘制 Canvas
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

    if (path.length < 2) return

    // Center and scale path
    const margin = 20
    const xs = path.map(p => p.x)
    const ys = path.map(p => p.y)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    const pathW = maxX - minX || 1
    const pathH = maxY - minY || 1

    const scaleX = (w - margin * 2) / pathW
    const scaleY = (h - margin * 2) / pathH
    const scale = Math.min(scaleX, scaleY, 1)

    const offsetX = (w - pathW * scale) / 2 - minX * scale
    const offsetY = (h - pathH * scale) / 2 - minY * scale

    // Draw path
    ctx.strokeStyle = '#0ea5e9'
    ctx.lineWidth = 2
    ctx.beginPath()
    path.forEach((pt, i) => {
      const x = pt.x * scale + offsetX
      const y = pt.y * scale + offsetY
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.stroke()

    // Start point
    if (path.length > 0) {
      const start = path[0]
      ctx.fillStyle = '#22c55e'
      ctx.beginPath()
      ctx.arc(start.x * scale + offsetX, start.y * scale + offsetY, 4, 0, Math.PI * 2)
      ctx.fill()
    }

    // Current position
    if (playing && playbackIndex.current < path.length) {
      const cur = path[playbackIndex.current]
      ctx.fillStyle = '#ef4444'
      ctx.beginPath()
      ctx.arc(cur.x * scale + offsetX, cur.y * scale + offsetY, 5, 0, Math.PI * 2)
      ctx.fill()
    }
  }, [path, playing])

  const handleToggleRecord = useCallback(() => {
    if (recording) {
      setRecording(false)
    } else {
      setPath([])
      setPosition({ x: 0, y: 0, angle: -90 })
      setRecording(true)
    }
  }, [recording])

  const handleSave = useCallback(() => {
    if (path.length === 0) return
    const newPath: RecordedPath = {
      name: `路径 ${savedPaths.length + 1}`,
      points: [...path],
      timestamp: Date.now(),
    }
    const updated = [...savedPaths, newPath].slice(-20)
    setSavedPaths(updated)
    storage.set(STORAGE_KEYS.SAVED_PATHS, updated)
  }, [path, savedPaths])

  const handlePlayback = useCallback(() => {
    if (path.length === 0) return
    setPlaying(true)
    playbackIndex.current = 0

    const interval = setInterval(() => {
      playbackIndex.current++
      if (playbackIndex.current >= path.length) {
        clearInterval(interval)
        setPlaying(false)
      }
      // Trigger re-render
      setPosition(prev => ({ ...prev }))
    }, 50)
  }, [path])

  const handleClear = useCallback(() => {
    setPath([])
    setPosition({ x: 0, y: 0, angle: -90 })
    setRecording(false)
    setPlaying(false)
  }, [])

  const disabled = !carConnected && !demoMode

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Disc3 className="w-6 h-6 text-sky-600" />
        录制回放
      </h2>

      {/* 控制按钮 */}
      <div className="flex gap-2">
        <button
          onClick={handleToggleRecord}
          disabled={disabled}
          className={`flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
            recording
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-red-50 text-red-600 hover:bg-red-100'
          }`}
        >
          {recording ? <Square className="w-4 h-4" /> : <Disc3 className="w-4 h-4" />}
          {recording ? '停止录制' : '开始录制'}
        </button>
        <button
          onClick={handlePlayback}
          disabled={disabled || path.length === 0 || playing}
          className="flex items-center gap-1 px-4 py-2 bg-green-50 text-green-600 rounded-lg text-sm font-medium hover:bg-green-100 disabled:opacity-50"
        >
          <Play className="w-4 h-4" /> 回放
        </button>
        <button
          onClick={handleSave}
          disabled={path.length === 0}
          className="flex items-center gap-1 px-4 py-2 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-100 disabled:opacity-50"
        >
          <Save className="w-4 h-4" /> 保存
        </button>
        <button
          onClick={handleClear}
          className="flex items-center gap-1 px-4 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200"
        >
          <RotateCcw className="w-4 h-4" /> 清空
        </button>
      </div>

      {/* 状态 */}
      <div className="flex items-center gap-4 text-sm">
        {recording && (
          <div className="flex items-center gap-1 text-red-600">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            录制中... ({path.length} 点)
          </div>
        )}
        {playing && (
          <div className="flex items-center gap-1 text-green-600">
            <Play className="w-3 h-3" />
            回放中... ({playbackIndex.current}/{path.length})
          </div>
        )}
      </div>

      {/* Canvas */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full"
          style={{ width: '100%', height: 280 }}
        />
      </div>

      {/* 保存的路径 */}
      {savedPaths.length > 0 && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-700 mb-2">已保存路径</h3>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {savedPaths.map((p, i) => (
              <div key={i} className="flex justify-between items-center bg-gray-50 rounded px-3 py-2 text-sm">
                <span>{p.name} ({p.points.length} 点)</span>
                <button
                  onClick={() => {
                    setPath(p.points)
                    setPosition({ x: 0, y: 0, angle: -90 })
                  }}
                  className="text-sky-600 hover:text-sky-700 text-xs"
                >
                  加载
                </button>
              </div>
            ))}
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
