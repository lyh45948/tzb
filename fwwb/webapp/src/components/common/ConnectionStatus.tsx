import { Wifi, WifiOff, Plug, Unplug } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ConnectionStatusProps {
  wsConnected: boolean
  carConnected: boolean
  className?: string
}

export default function ConnectionStatus({
  wsConnected,
  carConnected,
  className,
}: ConnectionStatusProps) {
  return (
    <div className={cn('flex items-center gap-4', className)}>
      {/* WebSocket 连接状态 */}
      <div className="flex items-center gap-1.5">
        {wsConnected ? (
          <Wifi className="w-4 h-4 text-green-500" />
        ) : (
          <WifiOff className="w-4 h-4 text-red-500" />
        )}
        <span
          className={cn(
            'text-sm font-medium',
            wsConnected ? 'text-green-600' : 'text-red-600'
          )}
        >
          {wsConnected ? 'WebSocket已连接' : 'WebSocket未连接'}
        </span>
      </div>

      {/* 小车连接状态 */}
      <div className="flex items-center gap-1.5">
        {carConnected ? (
          <Plug className="w-4 h-4 text-green-500" />
        ) : (
          <Unplug className="w-4 h-4 text-gray-400" />
        )}
        <span
          className={cn(
            'text-sm font-medium',
            carConnected ? 'text-green-600' : 'text-gray-500'
          )}
        >
          {carConnected ? '小车已连接' : '小车未连接'}
        </span>
      </div>
    </div>
  )
}
