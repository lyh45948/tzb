import { useRef, useState, useCallback, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface JoystickProps {
  onMove: (x: number, y: number) => void
  onEnd: () => void
  disabled?: boolean
}

export default function Joystick({ onMove, onEnd, disabled = false }: JoystickProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [active, setActive] = useState(false)
  const lastSendTime = useRef(0)
  const lastJoyRef = useRef({ x: 0, y: 0 })
  const repeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const resetJoystick = useCallback(() => {
    lastJoyRef.current = { x: 0, y: 0 }
    setPosition({ x: 0, y: 0 })
  }, [])

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (disabled) return
      e.preventDefault()
      setActive(true)
      const container = containerRef.current
      if (!container) return
      container.setPointerCapture(e.pointerId)
      updatePosition(e.clientX, e.clientY)
    },
    [disabled]
  )

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!active || disabled) return
      e.preventDefault()
      updatePosition(e.clientX, e.clientY)
    },
    [active, disabled]
  )

  const handlePointerUp = useCallback(
    (e: React.PointerEvent) => {
      if (!active) return
      e.preventDefault()
      setActive(false)
      resetJoystick()
      onEnd()
    },
    [active, resetJoystick, onEnd]
  )

  const updatePosition = useCallback(
    (clientX: number, clientY: number) => {
      const container = containerRef.current
      if (!container) return

      const rect = container.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2

      const maxRadius = rect.width / 2 - 30 // 减去摇杆头半径
      let dx = clientX - centerX
      let dy = clientY - centerY

      const distance = Math.sqrt(dx * dx + dy * dy)
      if (distance > maxRadius) {
        dx = (dx / distance) * maxRadius
        dy = (dy / distance) * maxRadius
      }

      setPosition({ x: dx, y: dy })

      // 转换为 -100 到 100
      const joyX = Math.round((dx / maxRadius) * 100)
      const joyY = Math.round((-dy / maxRadius) * 100) // Y轴翻转
      lastJoyRef.current = { x: joyX, y: joyY }

      // 50ms 节流
      const now = Date.now()
      if (now - lastSendTime.current >= 50) {
        lastSendTime.current = now
        onMove(joyX, joyY)
      }
    },
    [onMove]
  )

  // 触摸事件支持
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleTouchStart = (e: TouchEvent) => {
      if (disabled) return
      e.preventDefault()
      setActive(true)
      const touch = e.touches[0]
      updatePosition(touch.clientX, touch.clientY)
    }

    const handleTouchMove = (e: TouchEvent) => {
      if (!active || disabled) return
      e.preventDefault()
      const touch = e.touches[0]
      updatePosition(touch.clientX, touch.clientY)
    }

    const handleTouchEnd = (e: TouchEvent) => {
      if (!active) return
      e.preventDefault()
      setActive(false)
      resetJoystick()
      onEnd()
    }

    container.addEventListener('touchstart', handleTouchStart, { passive: false })
    container.addEventListener('touchmove', handleTouchMove, { passive: false })
    container.addEventListener('touchend', handleTouchEnd, { passive: false })

    return () => {
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', handleTouchEnd)
    }
  }, [active, disabled, resetJoystick, onEnd, updatePosition])

  useEffect(() => {
    if (!active || disabled) {
      if (repeatTimerRef.current) {
        clearInterval(repeatTimerRef.current)
        repeatTimerRef.current = null
      }
      return
    }

    repeatTimerRef.current = setInterval(() => {
      onMove(lastJoyRef.current.x, lastJoyRef.current.y)
    }, 200)

    return () => {
      if (repeatTimerRef.current) {
        clearInterval(repeatTimerRef.current)
        repeatTimerRef.current = null
      }
    }
  }, [active, disabled, onMove])

  return (
    <div
      ref={containerRef}
      className={cn(
        'relative w-48 h-48 rounded-full bg-gray-200 border-4 border-gray-300 touch-none select-none',
        active ? 'border-sky-400' : '',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      {/* 中心十字 */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-full h-px bg-gray-300" />
      </div>
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="h-full w-px bg-gray-300" />
      </div>

      {/* 摇杆头 */}
      <div
        className={cn(
          'absolute w-16 h-16 rounded-full shadow-lg transition-transform',
          active
            ? 'bg-sky-500 shadow-sky-500/30 scale-110'
            : 'bg-sky-400 shadow-sky-400/20'
        )}
        style={{
          left: '50%',
          top: '50%',
          transform: `translate(calc(-50% + ${position.x}px), calc(-50% + ${position.y}px))`,
        }}
      />
    </div>
  )
}
