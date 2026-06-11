import { useState, useCallback } from 'react'
import { Settings, Save, RotateCcw, Thermometer, Droplets, Wind, AlertTriangle } from 'lucide-react'
import { useAppStore } from '@/store/app-store'

export default function SettingsPage() {
  const { thresholds, setThresholds } = useAppStore()
  const [localThresholds, setLocalThresholds] = useState({ ...thresholds })
  const [saved, setSaved] = useState(false)

  const handleChange = useCallback((key: string, value: number) => {
    setLocalThresholds(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }, [])

  const handleSave = useCallback(() => {
    // setThresholds 会自动保存到 localStorage
    setThresholds(localThresholds)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }, [localThresholds, setThresholds])

  const handleReset = useCallback(() => {
    const defaults = {
      tempWarning: 30, tempDanger: 35,
      humiWarning: 75, humiDanger: 80,
      co2Warning: 800, co2Danger: 1000,
      smokeWarning: 300, smokeDanger: 500,
      coWarning: 35, coDanger: 50,
      distanceWarning: 30, distanceDanger: 15,
    }
    setLocalThresholds(defaults)
    // setThresholds 会自动保存到 localStorage
    setThresholds(defaults)
  }, [setThresholds])

  const thresholdGroups = [
    {
      title: '温度',
      icon: Thermometer,
      color: 'text-orange-500',
      items: [
        { key: 'tempWarning', label: '警告阈值', unit: '°C' },
        { key: 'tempDanger', label: '危险阈值', unit: '°C' },
      ],
    },
    {
      title: '湿度',
      icon: Droplets,
      color: 'text-blue-500',
      items: [
        { key: 'humiWarning', label: '警告阈值', unit: '%' },
        { key: 'humiDanger', label: '危险阈值', unit: '%' },
      ],
    },
    {
      title: 'CO2',
      icon: Wind,
      color: 'text-green-500',
      items: [
        { key: 'co2Warning', label: '警告阈值', unit: 'ppm' },
        { key: 'co2Danger', label: '危险阈值', unit: 'ppm' },
      ],
    },
    {
      title: '烟雾/气体',
      icon: AlertTriangle,
      color: 'text-red-500',
      items: [
        { key: 'smokeWarning', label: '警告阈值', unit: '' },
        { key: 'smokeDanger', label: '危险阈值', unit: '' },
      ],
    },
  ]

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Settings className="w-6 h-6 text-sky-600" />
        阈值设置
      </h2>

      {thresholdGroups.map((group) => {
        const Icon = group.icon
        return (
          <div key={group.title} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center gap-2 mb-3">
              <Icon className={`w-5 h-5 ${group.color}`} />
              <h3 className="font-semibold text-gray-700">{group.title}</h3>
            </div>
            <div className="space-y-3">
              {group.items.map((item) => (
                <div key={item.key} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{item.label}</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="range"
                      min={0}
                      max={item.unit === '%' ? 100 : item.unit === '°C' ? 60 : 2000}
                      value={localThresholds[item.key as keyof typeof localThresholds]}
                      onChange={(e) => handleChange(item.key, parseInt(e.target.value))}
                      className="w-32 accent-sky-600"
                    />
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min={0}
                        max={item.unit === '%' ? 100 : item.unit === '°C' ? 60 : 2000}
                        value={localThresholds[item.key as keyof typeof localThresholds]}
                        onChange={(e) => {
                          const val = parseInt(e.target.value) || 0
                          handleChange(item.key, val)
                        }}
                        className="w-16 text-sm font-medium text-gray-800 text-right border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none"
                      />
                      <span className="text-xs text-gray-500">{item.unit}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      })}

      {/* 保存/重置 */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-colors ${
            saved
              ? 'bg-green-500 text-white'
              : 'bg-sky-600 text-white hover:bg-sky-700'
          }`}
        >
          <Save className="w-4 h-4" />
          {saved ? '已保存' : '保存设置'}
        </button>
        <button
          onClick={handleReset}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-300 transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          重置
        </button>
      </div>
    </div>
  )
}
