import { useEffect, useState } from 'react'
import { Factory, AlertTriangle, Flame, Wind, Users, Package, Car } from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'

export default function FactoryDashboardPage() {
  const { sensorData, carStatus, carConnected, demoMode, thresholds } = useAppStore()
  const [gasAlerts, setGasAlerts] = useState<string[]>([])
  const [pirDetected, setPirDetected] = useState(false)
  const [goodsCount, setGoodsCount] = useState(0)
  const [flameDetected, setFlameDetected] = useState(false)

  useEffect(() => {
    const handleMessage = (msg: Record<string, unknown>) => {
      if (msg.type === 'realtime' && msg.data) {
        const data = msg.data as Record<string, unknown>
        const env = (data.env as Record<string, unknown>) || {}
        const agri = (env.agri as Record<string, number>) || {}

        // PIR检测
        setPirDetected(Boolean(env.ir))

        // 火焰检测
        setFlameDetected(agri.flameStatus === 1)

        // 货物计数（模拟）
        if (env.ps === 1) {
          setGoodsCount(prev => prev + 1)
        }

        // 气体告警
        const alerts: string[] = []
        const co2 = env.co2 as number
        const gasMic = env.gasMic as number
        if (co2 != null) {
          if (co2 >= thresholds.co2Danger) alerts.push('CO2浓度危险')
          else if (co2 >= thresholds.co2Warning) alerts.push('CO2浓度警告')
        }
        if (gasMic != null) {
          if (gasMic >= thresholds.smokeDanger) alerts.push('烟雾浓度危险')
          else if (gasMic >= thresholds.smokeWarning) alerts.push('烟雾浓度警告')
        }
        setGasAlerts(alerts)
      }
    }

    wsManager.onMessage(handleMessage)
    return () => wsManager.offMessage(handleMessage)
  }, [thresholds])

  const disabled = !carConnected && !demoMode

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Factory className="w-6 h-6 text-sky-600" />
        工厂安全看板
      </h2>

      {/* 告警横幅 */}
      {gasAlerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-center gap-2 text-red-700 font-bold mb-2">
            <AlertTriangle className="w-5 h-5" />
            安全告警
          </div>
          <div className="space-y-1">
            {gasAlerts.map((alert, i) => (
              <p key={i} className="text-sm text-red-600">{alert}</p>
            ))}
          </div>
        </div>
      )}

      {/* 核心指标卡片 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 气体监测 */}
        <div className={`rounded-xl p-4 shadow-sm border ${
          gasAlerts.length > 0 ? 'bg-red-50 border-red-200' : 'bg-white border-gray-100'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            <Wind className={`w-5 h-5 ${gasAlerts.length > 0 ? 'text-red-500' : 'text-green-500'}`} />
            <span className="font-semibold text-gray-700">气体监测</span>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">CO2</span>
              <span className={`font-medium ${
                sensorData.co2 != null && sensorData.co2 >= thresholds.co2Danger ? 'text-red-600' :
                sensorData.co2 != null && sensorData.co2 >= thresholds.co2Warning ? 'text-yellow-600' : 'text-gray-800'
              }`}>
                {sensorData.co2 != null ? `${sensorData.co2} ppm` : '--'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">TVOC</span>
              <span className="font-medium text-gray-800">
                {sensorData.tvoc != null ? `${sensorData.tvoc} ppb` : '--'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">气体浓度</span>
              <span className={`font-medium ${
                sensorData.gasMic != null && sensorData.gasMic >= thresholds.smokeDanger ? 'text-red-600' :
                sensorData.gasMic != null && sensorData.gasMic >= thresholds.smokeWarning ? 'text-yellow-600' : 'text-gray-800'
              }`}>
                {sensorData.gasMic != null ? sensorData.gasMic : '--'}
              </span>
            </div>
          </div>
        </div>

        {/* PIR人体感应 */}
        <div className={`rounded-xl p-4 shadow-sm border ${
          pirDetected ? 'bg-orange-50 border-orange-200' : 'bg-white border-gray-100'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            <Users className={`w-5 h-5 ${pirDetected ? 'text-orange-500' : 'text-gray-400'}`} />
            <span className="font-semibold text-gray-700">人体感应</span>
          </div>
          <p className={`text-lg font-bold ${pirDetected ? 'text-orange-600' : 'text-gray-400'}`}>
            {pirDetected ? '检测到人体' : '未检测到'}
          </p>
          {pirDetected && (
            <div className="mt-1 flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
              <span className="text-xs text-orange-600">实时监测中</span>
            </div>
          )}
        </div>

        {/* 火焰检测 */}
        <div className={`rounded-xl p-4 shadow-sm border ${
          flameDetected ? 'bg-red-50 border-red-200' : 'bg-white border-gray-100'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            <Flame className={`w-5 h-5 ${flameDetected ? 'text-red-500' : 'text-gray-400'}`} />
            <span className="font-semibold text-gray-700">火焰检测</span>
          </div>
          <p className={`text-lg font-bold ${flameDetected ? 'text-red-600' : 'text-green-600'}`}>
            {flameDetected ? '检测到火焰！' : '正常'}
          </p>
          {flameDetected && (
            <p className="text-xs text-red-600 mt-1">请立即处理！</p>
          )}
        </div>

        {/* 货物计数 */}
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-2">
            <Package className="w-5 h-5 text-blue-500" />
            <span className="font-semibold text-gray-700">货物计数</span>
          </div>
          <p className="text-3xl font-bold text-gray-800">{goodsCount}</p>
          <p className="text-xs text-gray-500">件</p>
        </div>
      </div>

      {/* AGV状态 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <Car className="w-5 h-5 text-sky-600" />
          AGV 状态
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500">运行状态</p>
            <p className="text-lg font-bold text-gray-800">{carStatus.status}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500">运行模式</p>
            <p className="text-lg font-bold text-gray-800">{carStatus.mode}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-xs text-gray-500">障碍物距离</p>
            <p className={`text-lg font-bold ${
              carStatus.distance != null && carStatus.distance < 15 ? 'text-red-600' :
              carStatus.distance != null && carStatus.distance < 30 ? 'text-yellow-600' : 'text-gray-800'
            }`}>
              {carStatus.distance != null ? `${carStatus.distance}cm` : '--'}
            </p>
          </div>
        </div>
      </div>

      {/* 环境温湿度 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">环境参数</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-orange-50 rounded-lg p-3">
            <p className="text-xs text-orange-600">温度</p>
            <p className="text-2xl font-bold text-orange-700">
              {sensorData.temperature != null ? `${sensorData.temperature}°C` : '--'}
            </p>
          </div>
          <div className="bg-blue-50 rounded-lg p-3">
            <p className="text-xs text-blue-600">湿度</p>
            <p className="text-2xl font-bold text-blue-700">
              {sensorData.humidity != null ? `${sensorData.humidity}%` : '--'}
            </p>
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
