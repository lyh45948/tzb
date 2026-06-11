import { useMemo } from 'react'
import {
  Thermometer,
  Droplets,
  Sun,
  Wind,
  FlaskConical,
  AlertTriangle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface SensorCardProps {
  type: 'temperature' | 'humidity' | 'light' | 'co2' | 'tvoc' | 'gas'
  value: number | null
  unit: string
  label: string
  warningThreshold?: number
  dangerThreshold?: number
}

const iconMap = {
  temperature: Thermometer,
  humidity: Droplets,
  light: Sun,
  co2: Wind,
  tvoc: FlaskConical,
  gas: AlertTriangle,
}

const colorMap = {
  temperature: 'from-orange-400 to-red-500',
  humidity: 'from-blue-400 to-cyan-500',
  light: 'from-yellow-400 to-amber-500',
  co2: 'from-green-400 to-emerald-500',
  tvoc: 'from-purple-400 to-violet-500',
  gas: 'from-red-400 to-rose-500',
}

export default function SensorCard({
  type,
  value,
  unit,
  label,
  warningThreshold,
  dangerThreshold,
}: SensorCardProps) {
  const Icon = iconMap[type]

  const status = useMemo(() => {
    if (value == null) return 'normal'
    if (dangerThreshold != null && value >= dangerThreshold) return 'danger'
    if (warningThreshold != null && value >= warningThreshold) return 'warning'
    return 'normal'
  }, [value, warningThreshold, dangerThreshold])

  const displayValue = value != null ? value.toFixed(1) : '--'

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl p-4 text-white shadow-md',
        'bg-gradient-to-br',
        colorMap[type]
      )}
    >
      {/* 状态指示点 */}
      {status !== 'normal' && (
        <div
          className={cn(
            'absolute top-2 right-2 w-3 h-3 rounded-full animate-pulse',
            status === 'danger' ? 'bg-red-200' : 'bg-yellow-200'
          )}
        />
      )}

      <div className="flex items-start justify-between">
        <div>
          <p className="text-white/80 text-sm">{label}</p>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-2xl font-bold">{displayValue}</span>
            <span className="text-white/70 text-sm">{unit}</span>
          </div>
        </div>
        <div className="p-2 bg-white/20 rounded-lg">
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>

      {/* 进度条 */}
      {value != null && warningThreshold != null && (
        <div className="mt-3">
          <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                status === 'danger'
                  ? 'bg-red-200'
                  : status === 'warning'
                    ? 'bg-yellow-200'
                    : 'bg-white/60'
              )}
              style={{
                width: `${Math.min((value / (dangerThreshold || warningThreshold * 1.5)) * 100, 100)}%`,
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
