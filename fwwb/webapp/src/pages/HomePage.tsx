import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Gamepad2,
  BarChart3,
  AlertTriangle,
  Settings,
  Factory,
  Route,
  Shield,
  Radio,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'
import SensorCard from '@/components/sensors/SensorCard'
import type { Alert } from '@/types'

const menuItems = [
  { path: '/control', label: '小车控制', icon: Gamepad2, color: 'bg-blue-500' },
  { path: '/environment', label: '环境监控', icon: BarChart3, color: 'bg-green-500' },
  { path: '/factory', label: '工厂看板', icon: Factory, color: 'bg-orange-500' },
  { path: '/equipment', label: '设备控制', icon: Radio, color: 'bg-purple-500' },
  { path: '/alerts', label: '告警中心', icon: AlertTriangle, color: 'bg-red-500' },
  { path: '/monitor', label: '监控面板', icon: BarChart3, color: 'bg-emerald-500' },
  { path: '/path', label: '路径规划', icon: Route, color: 'bg-indigo-500' },
  { path: '/fence', label: '虚拟围栏', icon: Shield, color: 'bg-teal-500' },
  { path: '/settings', label: '系统设置', icon: Settings, color: 'bg-gray-500' },
]

export default function HomePage() {
  const navigate = useNavigate()
  const {
    wsConnected,
    carConnected,
    demoMode,
    sensorData,
    carStatus,
    alerts,
    thresholds,
    activeCarId,
    updateSensorData,
    updateCarStatus,
    updateDeviceStatus,
    addAlert,
    setWsConnected,
    setCarConnected,
  } = useAppStore()

  // 监听 WebSocket 消息
  useEffect(() => {
    const handleMessage = (msg: Record<string, unknown>) => {
      if (msg.type === 'realtime' && msg.data) {
        const data = msg.data as Record<string, unknown>
        const env = (data.env as Record<string, number | null>) || {}

        updateSensorData({
          temperature: env.temp ?? null,
          humidity: env.humi ?? null,
          light: env.lux ?? null,
          co2: env.co2 ?? null,
          tvoc: env.tvoc ?? null,
          gasMic: env.gasMic ?? null,
          fan: env.fan ?? 0,
          led: env.led ?? 0,
          buzzer: env.buzzer ?? 0,
        })

        updateCarStatus({
          status: String(data.carStatus || 'off'),
          mode: String(data.carMode || 'manual'),
          L_spd: Number(data.L_spd || 0),
          R_spd: Number(data.R_spd || 0),
          carPower: data.carPower != null ? Number(data.carPower) : null,
          distance: data.distance != null ? Number(data.distance) : null,
        })

        updateDeviceStatus({
          fan: Boolean(env.fan),
          led: Boolean(env.led),
          buzzer: Boolean(env.buzzer),
          pump: false,
          valve: false,
        })

        // 阈值告警检查
        checkThresholds(env)
      }

      if (msg.type === 'connect_result') {
        setCarConnected(Boolean(msg.success))
      }
    }

    const handleConnectionChange = (connected: boolean) => {
      setWsConnected(connected)
    }

    wsManager.onMessage(handleMessage)
    wsManager.onConnectionChange(handleConnectionChange)

    return () => {
      wsManager.offMessage(handleMessage)
      wsManager.offConnectionChange(handleConnectionChange)
    }
  }, [updateSensorData, updateCarStatus, updateDeviceStatus, addAlert, setWsConnected, setCarConnected, thresholds])

  const checkThresholds = useCallback(
    (env: Record<string, number | null>) => {
      const checks: { value: number | null; threshold: number; type: string; label: string; level: Alert['level'] }[] = [
        { value: env.temp, threshold: thresholds.tempDanger, type: 'temperature', label: '温度过高', level: 'danger' },
        { value: env.temp, threshold: thresholds.tempWarning, type: 'temperature', label: '温度警告', level: 'warning' },
        { value: env.humi, threshold: thresholds.humiDanger, type: 'humidity', label: '湿度过高', level: 'danger' },
        { value: env.humi, threshold: thresholds.humiWarning, type: 'humidity', label: '湿度警告', level: 'warning' },
        { value: env.co2, threshold: thresholds.co2Danger, type: 'co2', label: 'CO2浓度过高', level: 'danger' },
        { value: env.co2, threshold: thresholds.co2Warning, type: 'co2', label: 'CO2浓度警告', level: 'warning' },
        { value: env.gasMic, threshold: thresholds.smokeDanger, type: 'gas', label: '气体浓度过高', level: 'danger' },
        { value: env.gasMic, threshold: thresholds.smokeWarning, type: 'gas', label: '气体浓度警告', level: 'warning' },
      ]

      checks.forEach((check) => {
        if (check.value != null && check.value >= check.threshold) {
          const id = `${check.type}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
          addAlert({
            id,
            level: check.level,
            type: check.type,
            message: `${check.label}: ${check.value}`,
            timestamp: Date.now(),
            acknowledged: false,
          })
        }
      })
    },
    [thresholds, addAlert]
  )

  const activeAlerts = alerts.filter((a) => !a.acknowledged)

  return (
    <div className="p-4 space-y-4">
      {/* 状态栏 */}
      <div className="flex items-center justify-between bg-white rounded-xl p-3 shadow-sm border border-gray-100">
        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-1 ${wsConnected ? 'text-green-600' : 'text-red-500'}`}>
            {wsConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            <span className="text-xs font-medium">{wsConnected ? '在线' : '离线'}</span>
          </div>
          {carConnected && activeCarId && (
            <div className="flex items-center gap-1 text-green-600">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs font-medium">{activeCarId}</span>
            </div>
          )}
          {demoMode && (
            <span className="px-2 py-0.5 bg-yellow-500 text-white text-xs rounded-full font-medium">
              演示
            </span>
          )}
        </div>
        {activeAlerts.length > 0 && (
          <button
            onClick={() => navigate('/alerts')}
            className="flex items-center gap-1 px-2 py-1 bg-red-50 text-red-600 rounded-lg text-xs font-medium"
          >
            <AlertTriangle className="w-3 h-3" />
            {activeAlerts.length} 个告警
          </button>
        )}
      </div>

      {/* 传感器卡片 */}
      <div className="grid grid-cols-2 gap-3">
        <SensorCard
          type="temperature"
          value={sensorData.temperature}
          unit="°C"
          label="温度"
          warningThreshold={thresholds.tempWarning}
          dangerThreshold={thresholds.tempDanger}
        />
        <SensorCard
          type="humidity"
          value={sensorData.humidity}
          unit="%"
          label="湿度"
          warningThreshold={thresholds.humiWarning}
          dangerThreshold={thresholds.humiDanger}
        />
        <SensorCard
          type="light"
          value={sensorData.light}
          unit="lux"
          label="光照"
        />
        <SensorCard
          type="co2"
          value={sensorData.co2}
          unit="ppm"
          label="CO2"
          warningThreshold={thresholds.co2Warning}
          dangerThreshold={thresholds.co2Danger}
        />
        <SensorCard
          type="tvoc"
          value={sensorData.tvoc}
          unit="ppb"
          label="TVOC"
        />
        <SensorCard
          type="gas"
          value={sensorData.gasMic}
          unit=""
          label="气体浓度"
          warningThreshold={thresholds.smokeWarning}
          dangerThreshold={thresholds.smokeDanger}
        />
      </div>

      {/* 小车状态 */}
      {carConnected && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-700 mb-3">小车状态</h3>
          <div className="grid grid-cols-4 gap-2 text-center">
            <div className="bg-gray-50 rounded-lg p-2">
              <p className="text-xs text-gray-500">状态</p>
              <p className="text-sm font-semibold text-gray-800">{carStatus.status}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-2">
              <p className="text-xs text-gray-500">模式</p>
              <p className="text-sm font-semibold text-gray-800">{carStatus.mode}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-2">
              <p className="text-xs text-gray-500">左轮速</p>
              <p className="text-sm font-semibold text-gray-800">{carStatus.L_spd}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-2">
              <p className="text-xs text-gray-500">右轮速</p>
              <p className="text-sm font-semibold text-gray-800">{carStatus.R_spd}</p>
            </div>
          </div>
          {carStatus.distance != null && (
            <div className="mt-2 flex items-center justify-between bg-gray-50 rounded-lg p-2">
              <span className="text-xs text-gray-500">障碍物距离</span>
              <span className={`text-sm font-semibold ${
                carStatus.distance < 15 ? 'text-red-600' :
                carStatus.distance < 30 ? 'text-yellow-600' : 'text-gray-800'
              }`}>
                {carStatus.distance} cm
              </span>
            </div>
          )}
        </div>
      )}

      {/* 功能菜单 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">功能导航</h3>
        <div className="grid grid-cols-5 gap-2">
          {menuItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className="flex flex-col items-center gap-1 p-2 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className={`w-10 h-10 ${item.color} rounded-xl flex items-center justify-center`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <span className="text-[10px] text-gray-600 font-medium">{item.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* 未连接提示 */}
      {!wsConnected && (
        <div className="bg-blue-50 rounded-xl p-4 text-center">
          <p className="text-blue-700 text-sm mb-2">尚未连接到后端服务</p>
          <button
            onClick={() => navigate('/connect')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            前往连接页面
          </button>
        </div>
      )}
    </div>
  )
}
