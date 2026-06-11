import { useEffect, useState } from 'react'
import { Sprout, Thermometer, Droplets, Sun, Wind, Gauge, Fan, Lightbulb, Bell, AlertTriangle } from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'

export default function AgriculturePage() {
  const { sensorData, carConnected, demoMode, thresholds } = useAppStore()
  const [alerts, setAlerts] = useState<string[]>([])

  useEffect(() => {
    const newAlerts: string[] = []
    if (sensorData.temperature != null && sensorData.temperature >= thresholds.tempDanger) {
      newAlerts.push('温度过高')
    }
    if (sensorData.humidity != null && sensorData.humidity >= thresholds.humiDanger) {
      newAlerts.push('湿度过高')
    }
    if (sensorData.co2 != null && sensorData.co2 >= thresholds.co2Danger) {
      newAlerts.push('CO2浓度过高')
    }
    setAlerts(newAlerts)
  }, [sensorData, thresholds])

  const sensors = [
    { icon: Thermometer, label: '温度', value: sensorData.temperature, unit: '°C', warning: thresholds.tempWarning, danger: thresholds.tempDanger },
    { icon: Droplets, label: '湿度', value: sensorData.humidity, unit: '%', warning: thresholds.humiWarning, danger: thresholds.humiDanger },
    { icon: Sun, label: '光照', value: sensorData.light, unit: 'lux' },
    { icon: Wind, label: 'CO2', value: sensorData.co2, unit: 'ppm', warning: thresholds.co2Warning, danger: thresholds.co2Danger },
    { icon: Gauge, label: 'TVOC', value: sensorData.tvoc, unit: 'ppb' },
    { icon: AlertTriangle, label: '气体浓度', value: sensorData.gasMic, unit: '', warning: thresholds.smokeWarning, danger: thresholds.smokeDanger },
  ]

  const devices = [
    { icon: Fan, label: '风扇', active: sensorData.fan === 1 },
    { icon: Lightbulb, label: 'LED灯', active: sensorData.led === 1 },
    { icon: Bell, label: '蜂鸣器', active: sensorData.buzzer === 1 },
  ]

  const disabled = !carConnected && !demoMode

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Sprout className="w-6 h-6 text-sky-600" />
        农业安防
      </h2>

      {/* 告警横幅 */}
      {alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-center gap-2 text-red-700 font-bold mb-1">
            <AlertTriangle className="w-5 h-5" />
            环境告警
          </div>
          <div className="flex flex-wrap gap-1">
            {alerts.map((alert, i) => (
              <span key={i} className="px-2 py-0.5 bg-red-100 text-red-600 text-xs rounded-full">
                {alert}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 传感器 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">环境传感器</h3>
        <div className="grid grid-cols-2 gap-3">
          {sensors.map((s) => {
            const Icon = s.icon
            const isWarning = s.warning != null && s.value != null && s.value >= s.warning
            const isDanger = s.danger != null && s.value != null && s.value >= s.danger

            return (
              <div
                key={s.label}
                className={`rounded-lg p-3 ${
                  isDanger ? 'bg-red-50 border border-red-200' :
                  isWarning ? 'bg-yellow-50 border border-yellow-200' :
                  'bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <Icon className="w-4 h-4 text-gray-500" />
                  <span className="text-xs text-gray-500">{s.label}</span>
                </div>
                <p className={`text-xl font-bold ${
                  isDanger ? 'text-red-600' :
                  isWarning ? 'text-yellow-600' :
                  'text-gray-800'
                }`}>
                  {s.value != null ? `${s.value}${s.unit}` : '--'}
                </p>
              </div>
            )
          })}
        </div>
      </div>

      {/* 设备状态 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-700 mb-3">设备状态</h3>
        <div className="grid grid-cols-3 gap-3">
          {devices.map((dev) => {
            const Icon = dev.icon
            return (
              <div
                key={dev.label}
                className={`flex flex-col items-center gap-1 p-3 rounded-lg ${
                  dev.active ? 'bg-green-50 border border-green-200' : 'bg-gray-50'
                }`}
              >
                <Icon className={`w-5 h-5 ${dev.active ? 'text-green-600' : 'text-gray-400'}`} />
                <span className="text-xs text-gray-600">{dev.label}</span>
                <div className={`w-2 h-2 rounded-full ${dev.active ? 'bg-green-500' : 'bg-gray-300'}`} />
              </div>
            )
          })}
        </div>
      </div>

      {/* 自动灌溉提示（农业场景） */}
      <div className="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl p-4 text-white">
        <h3 className="font-bold mb-1">智能农业监测</h3>
        <p className="text-sm text-white/80">
          基于温湿度、光照等环境数据，系统实时监测农作物生长环境。
          当环境参数超过阈值时，将自动触发告警提醒。
        </p>
      </div>

      {disabled && (
        <div className="bg-yellow-50 rounded-xl p-4 text-center">
          <p className="text-yellow-700 text-sm">请先连接小车或开启演示模式</p>
        </div>
      )}
    </div>
  )
}
