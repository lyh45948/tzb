import { Wifi, WifiOff, Radio, Car } from 'lucide-react'
import { useAppStore } from '@/store/app-store'

export default function Header() {
  const { wsConnected, carConnected, demoMode, cars, activeCarId } = useAppStore()

  const carCount = cars.filter(c => c.connected).length

  return (
    <header className="sticky top-0 z-50 bg-gradient-to-r from-sky-600 to-blue-600 text-white px-4 py-3 shadow-md">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio className="w-5 h-5" />
          <h1 className="text-lg font-bold">智慧工厂监测平台</h1>
        </div>
        <div className="flex items-center gap-3 text-xs">
          {demoMode && (
            <span className="px-2 py-0.5 bg-yellow-500 rounded-full text-white font-medium">
              演示
            </span>
          )}
          <div className="flex items-center gap-1">
            {wsConnected ? (
              <Wifi className="w-4 h-4 text-green-300" />
            ) : (
              <WifiOff className="w-4 h-4 text-red-300" />
            )}
            <span className={wsConnected ? 'text-green-200' : 'text-red-200'}>
              {wsConnected ? '在线' : '离线'}
            </span>
          </div>
          {carConnected && carCount > 0 && (
            <div className="flex items-center gap-1">
              <Car className="w-3.5 h-3.5 text-green-300" />
              <span className="text-green-200">
                {carCount}辆
                {activeCarId && (
                  <span className="ml-0.5 opacity-80">({activeCarId})</span>
                )}
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
