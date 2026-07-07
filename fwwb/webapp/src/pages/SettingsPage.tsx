import { useState, useCallback, useEffect } from 'react'
import { Settings, Save, RotateCcw, Thermometer, Droplets, Wind, AlertTriangle, Eye, Wifi } from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'
import type { LinkageConfig } from '@/types'

// 联动配置默认值（首次连接前 / 后端不可用时使用）
const DEFAULT_LINKAGE: LinkageConfig = {
  fanTempOn: 32, fanTempOff: 30, fanHumiOn: 80, fanHumiOff: 75,
  irPs: 200, irIr: 100, irDebounceOn: 2, irDebounceOff: 5,
  tickSeconds: 1.0, manualOverrideTtl: 30, rgbBlinkHz: 1.0,
  co2Warning: 800, co2Danger: 1000,
  tvocWarning: 600, tvocDanger: 900,
  gasMicWarning: 300, gasMicDanger: 500,
  distanceWarning: 30, distanceDanger: 15,
}

export default function SettingsPage() {
  const { thresholds, setThresholds, linkageConfig, setLinkageConfig, wsConnected } = useAppStore()
  const [localThresholds, setLocalThresholds] = useState({ ...thresholds })
  const [localLinkage, setLocalLinkage] = useState<LinkageConfig>(linkageConfig || DEFAULT_LINKAGE)
  const [saved, setSaved] = useState(false)
  const [pushing, setPushing] = useState(false)
  const [pushMsg, setPushMsg] = useState<string | null>(null)

  // 当 store 中的 linkageConfig 更新（首次拉取/广播）时，同步到本地编辑副本
  useEffect(() => {
    if (linkageConfig) {
      setLocalLinkage(linkageConfig)
    }
  }, [linkageConfig])

  // 进入页面时主动拉一次最新配置（防止 App.tsx 钩子时序错开）
  useEffect(() => {
    if (wsConnected) {
      wsManager.getLinkageConfig()
    }
  }, [wsConnected])

  const handleThresholdChange = useCallback((key: string, value: number) => {
    setLocalThresholds(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }, [])

  const handleLinkageChange = useCallback((key: keyof LinkageConfig, value: number) => {
    setLocalLinkage(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }, [])

  const handleSave = useCallback(() => {
    setThresholds(localThresholds)
    setLinkageConfig(localLinkage)

    // 把所有可发的字段一次性推到后端，不区分哪些是联动哪些是告警——后端 _FIELD_MAP 自动过滤
    if (wsConnected) {
      setPushing(true)
      setPushMsg(null)
      try {
        wsManager.setLinkageConfig({
          // 风扇 / 人体感应 / 节奏
          fanTempOn: localLinkage.fanTempOn,
          fanTempOff: localLinkage.fanTempOff,
          fanHumiOn: localLinkage.fanHumiOn,
          fanHumiOff: localLinkage.fanHumiOff,
          irPs: localLinkage.irPs,
          irIr: localLinkage.irIr,
          irDebounceOn: localLinkage.irDebounceOn,
          irDebounceOff: localLinkage.irDebounceOff,
          tickSeconds: localLinkage.tickSeconds,
          manualOverrideTtl: localLinkage.manualOverrideTtl,
          rgbBlinkHz: localLinkage.rgbBlinkHz,
          // 告警阈值（与本地 thresholds 对齐 co2/smoke→gasMic）
          co2Warning: localThresholds.co2Warning,
          co2Danger: localThresholds.co2Danger,
          tvocWarning: localLinkage.tvocWarning,
          tvocDanger: localLinkage.tvocDanger,
          gasMicWarning: localThresholds.smokeWarning,
          gasMicDanger: localThresholds.smokeDanger,
          distanceWarning: localThresholds.distanceWarning,
          distanceDanger: localThresholds.distanceDanger,
        })
        setPushMsg('已下发到后端')
      } catch (e) {
        setPushMsg('下发失败：' + String(e))
      } finally {
        setTimeout(() => setPushing(false), 600)
      }
    } else {
      setPushMsg('后端未连接，仅保存到本地')
    }

    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }, [localThresholds, localLinkage, setThresholds, setLinkageConfig, wsConnected])

  const handleReset = useCallback(() => {
    const defaults = {
      tempWarning: 30, tempDanger: 35,
      humiWarning: 75, humiDanger: 80,
      co2Warning: 800, co2Danger: 1000,
      smokeWarning: 300, smokeDanger: 500,
      tvocWarning: 600, tvocDanger: 900,
      coWarning: 35, coDanger: 50,
      distanceWarning: 30, distanceDanger: 15,
    }
    setLocalThresholds(defaults)
    setThresholds(defaults)
    setLocalLinkage(DEFAULT_LINKAGE)
    setLinkageConfig(DEFAULT_LINKAGE)
  }, [setThresholds, setLinkageConfig])

  const thresholdGroups = [
    {
      title: '温度（仅显示告色）',
      icon: Thermometer,
      color: 'text-orange-500',
      items: [
        { key: 'tempWarning', label: '警告阈值', unit: '°C' },
        { key: 'tempDanger', label: '危险阈值', unit: '°C' },
      ],
    },
    {
      title: '湿度（仅显示告色）',
      icon: Droplets,
      color: 'text-blue-500',
      items: [
        { key: 'humiWarning', label: '警告阈值', unit: '%' },
        { key: 'humiDanger', label: '危险阈值', unit: '%' },
      ],
    },
    {
      title: 'CO2（影响 RGB 联动）',
      icon: Wind,
      color: 'text-green-500',
      items: [
        { key: 'co2Warning', label: '警告阈值', unit: 'ppm' },
        { key: 'co2Danger', label: '危险阈值', unit: 'ppm' },
      ],
    },
    {
      title: '烟雾/气体（影响 RGB 联动）',
      icon: AlertTriangle,
      color: 'text-red-500',
      items: [
        { key: 'smokeWarning', label: '警告阈值', unit: '' },
        { key: 'smokeDanger', label: '危险阈值', unit: '' },
      ],
    },
  ]

  const itemRange = (unit: string) =>
    unit === '%' ? 100 : unit === '°C' ? 60 : 2000

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Settings className="w-6 h-6 text-sky-600" />
        阈值设置
        <span className={`ml-auto text-xs px-2 py-0.5 rounded-full flex items-center gap-1 ${wsConnected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
          <Wifi className="w-3 h-3" />
          {wsConnected ? '后端已连接' : '后端未连接'}
        </span>
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
                      max={itemRange(item.unit)}
                      value={localThresholds[item.key as keyof typeof localThresholds]}
                      onChange={(e) => handleThresholdChange(item.key, parseInt(e.target.value))}
                      className="w-32 accent-sky-600"
                    />
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min={0}
                        max={itemRange(item.unit)}
                        value={localThresholds[item.key as keyof typeof localThresholds]}
                        onChange={(e) => {
                          const val = parseInt(e.target.value) || 0
                          handleThresholdChange(item.key, val)
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

      {/* 人体感应联动（影响 LED 自动开关） */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-3">
          <Eye className="w-5 h-5 text-sky-500" />
          <h3 className="font-semibold text-gray-700">人体感应联动 → LED</h3>
        </div>
        <p className="text-xs text-gray-500 mb-3">
          AP3216C 的 ps（接近）和 ir（红外）通道，<strong>任一</strong>超过对应阈值即认为有人。需现场标定。
        </p>
        <div className="space-y-3">
          {([
            { key: 'irPs', label: 'PS 阈值（接近）', unit: '', max: 65535 },
            { key: 'irIr', label: 'IR 阈值（红外）', unit: '', max: 65535 },
            { key: 'irDebounceOn', label: '点亮去抖（连续 N 个 tick 才点亮）', unit: 'tick', max: 20 },
            { key: 'irDebounceOff', label: '熄灭去抖（连续 N 个 tick 才熄灭）', unit: 'tick', max: 60 },
          ] as const).map((item) => (
            <div key={item.key} className="flex items-center justify-between">
              <span className="text-sm text-gray-600">{item.label}</span>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min={0}
                  max={item.max}
                  value={localLinkage[item.key]}
                  onChange={(e) => handleLinkageChange(item.key, parseInt(e.target.value))}
                  className="w-32 accent-sky-600"
                />
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    min={0}
                    max={item.max}
                    value={localLinkage[item.key]}
                    onChange={(e) => handleLinkageChange(item.key, parseInt(e.target.value) || 0)}
                    className="w-20 text-sm font-medium text-gray-800 text-right border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none"
                  />
                  <span className="text-xs text-gray-500">{item.unit}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 风扇联动（双门限回滞） */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-3">
          <Wind className="w-5 h-5 text-cyan-500" />
          <h3 className="font-semibold text-gray-700">风扇联动 → 风扇</h3>
        </div>
        <p className="text-xs text-gray-500 mb-3">
          双门限回滞：超过 <strong>开启阈值</strong> 启动；同时低于 <strong>关闭阈值</strong> 才停止。
        </p>
        <div className="space-y-3">
          {([
            { key: 'fanTempOn',  label: '温度开启阈值', unit: '°C', max: 60 },
            { key: 'fanTempOff', label: '温度关闭阈值', unit: '°C', max: 60 },
            { key: 'fanHumiOn',  label: '湿度开启阈值', unit: '%',  max: 100 },
            { key: 'fanHumiOff', label: '湿度关闭阈值', unit: '%',  max: 100 },
          ] as const).map((item) => (
            <div key={item.key} className="flex items-center justify-between">
              <span className="text-sm text-gray-600">{item.label}</span>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min={0}
                  max={item.max}
                  step={item.unit === '°C' ? 0.5 : 1}
                  value={localLinkage[item.key]}
                  onChange={(e) => handleLinkageChange(item.key, parseFloat(e.target.value))}
                  className="w-32 accent-sky-600"
                />
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    min={0}
                    max={item.max}
                    step={item.unit === '°C' ? 0.5 : 1}
                    value={localLinkage[item.key]}
                    onChange={(e) => handleLinkageChange(item.key, parseFloat(e.target.value) || 0)}
                    className="w-16 text-sm font-medium text-gray-800 text-right border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none"
                  />
                  <span className="text-xs text-gray-500">{item.unit}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 联动控制器节奏 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-3">
          <Settings className="w-5 h-5 text-purple-500" />
          <h3 className="font-semibold text-gray-700">联动控制器节奏</h3>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">主循环周期（越小响应越快，但 UDP 流量越大）</span>
            <div className="flex items-center gap-1">
              <input
                type="number"
                min={0.1} max={5} step={0.1}
                value={localLinkage.tickSeconds}
                onChange={(e) => handleLinkageChange('tickSeconds', parseFloat(e.target.value) || 1)}
                className="w-20 text-sm font-medium text-gray-800 text-right border border-gray-300 rounded px-2 py-1"
              />
              <span className="text-xs text-gray-500">s</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">手动覆盖静默期</span>
            <div className="flex items-center gap-1">
              <input
                type="number"
                min={0} max={300} step={1}
                value={localLinkage.manualOverrideTtl}
                onChange={(e) => handleLinkageChange('manualOverrideTtl', parseInt(e.target.value) || 0)}
                className="w-20 text-sm font-medium text-gray-800 text-right border border-gray-300 rounded px-2 py-1"
              />
              <span className="text-xs text-gray-500">s</span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">RGB critical 闪烁频率</span>
            <div className="flex items-center gap-1">
              <input
                type="number"
                min={0.1} max={5} step={0.1}
                value={localLinkage.rgbBlinkHz}
                onChange={(e) => handleLinkageChange('rgbBlinkHz', parseFloat(e.target.value) || 1)}
                className="w-20 text-sm font-medium text-gray-800 text-right border border-gray-300 rounded px-2 py-1"
              />
              <span className="text-xs text-gray-500">Hz</span>
            </div>
          </div>
        </div>
      </div>

      {pushMsg && (
        <div className={`text-xs px-3 py-2 rounded-lg ${pushing ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'}`}>
          {pushMsg}
        </div>
      )}

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
