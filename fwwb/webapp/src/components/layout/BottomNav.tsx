import { useLocation, useNavigate } from 'react-router-dom'
import {
  Home,
  Gamepad2,
  Settings,
  AlertTriangle,
  Link,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { path: '/', label: '首页', icon: Home },
  { path: '/connect', label: '连接', icon: Link },
  { path: '/control', label: '控制', icon: Gamepad2 },
  { path: '/alerts', label: '告警', icon: AlertTriangle },
  { path: '/settings', label: '设置', icon: Settings },
]

export default function BottomNav() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex justify-center">
      <div className="w-full max-w-md bg-white border-t border-gray-200 shadow-lg">
        <div className="flex justify-around items-center py-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={cn(
                  'flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg transition-colors',
                  isActive
                    ? 'text-sky-600'
                    : 'text-gray-400 hover:text-gray-600'
                )}
              >
                <Icon className="w-5 h-5" />
                <span className="text-[10px] font-medium">{item.label}</span>
              </button>
            )
          })}
        </div>
      </div>
    </nav>
  )
}