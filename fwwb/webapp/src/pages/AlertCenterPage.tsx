import { useState } from 'react'
import { AlertTriangle, CheckCircle, Trash2, Bell } from 'lucide-react'
import { useAppStore } from '@/store/app-store'

export default function AlertCenterPage() {
  const { alerts, acknowledgeAlert, clearAlerts } = useAppStore()
  const [filter, setFilter] = useState<'all' | 'warning' | 'danger' | 'critical'>('all')

  const filteredAlerts = filter === 'all'
    ? alerts
    : alerts.filter((a) => a.level === filter)

  const stats = {
    total: alerts.length,
    unacknowledged: alerts.filter((a) => !a.acknowledged).length,
    warning: alerts.filter((a) => a.level === 'warning').length,
    danger: alerts.filter((a) => a.level === 'danger').length,
    critical: alerts.filter((a) => a.level === 'critical').length,
  }

  const levelConfig = {
    warning: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', badge: 'bg-yellow-500' },
    danger: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', badge: 'bg-orange-500' },
    critical: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-500' },
  }

  const formatTime = (timestamp: number) => {
    const d = new Date(timestamp)
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <AlertTriangle className="w-6 h-6 text-sky-600" />
        告警中心
      </h2>

      {/* 统计 */}
      <div className="grid grid-cols-4 gap-2">
        <div className="bg-white rounded-xl p-3 shadow-sm border border-gray-100 text-center">
          <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
          <p className="text-xs text-gray-500">总计</p>
        </div>
        <div className="bg-yellow-50 rounded-xl p-3 shadow-sm border border-yellow-100 text-center">
          <p className="text-2xl font-bold text-yellow-600">{stats.warning}</p>
          <p className="text-xs text-yellow-600">警告</p>
        </div>
        <div className="bg-orange-50 rounded-xl p-3 shadow-sm border border-orange-100 text-center">
          <p className="text-2xl font-bold text-orange-600">{stats.danger}</p>
          <p className="text-xs text-orange-600">危险</p>
        </div>
        <div className="bg-red-50 rounded-xl p-3 shadow-sm border border-red-100 text-center">
          <p className="text-2xl font-bold text-red-600">{stats.critical}</p>
          <p className="text-xs text-red-600">严重</p>
        </div>
      </div>

      {/* 筛选 */}
      <div className="flex gap-2">
        {(['all', 'warning', 'danger', 'critical'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === f
                ? 'bg-sky-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f === 'all' ? '全部' : f === 'warning' ? '警告' : f === 'danger' ? '危险' : '严重'}
          </button>
        ))}
        <button
          onClick={clearAlerts}
          className="ml-auto flex items-center gap-1 px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-xs font-medium hover:bg-red-100"
        >
          <Trash2 className="w-3 h-3" />
          清空
        </button>
      </div>

      {/* 告警列表 */}
      <div className="space-y-2">
        {filteredAlerts.length === 0 ? (
          <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-100 text-center">
            <Bell className="w-12 h-12 text-gray-300 mx-auto mb-2" />
            <p className="text-gray-500">暂无告警</p>
          </div>
        ) : (
          filteredAlerts.map((alert) => {
            const cfg = levelConfig[alert.level]
            return (
              <div
                key={alert.id}
                className={`${cfg.bg} border ${cfg.border} rounded-xl p-3 ${
                  alert.acknowledged ? 'opacity-50' : ''
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 ${cfg.badge} text-white text-xs rounded-full font-medium`}>
                      {alert.level === 'warning' ? '警告' : alert.level === 'danger' ? '危险' : '严重'}
                    </span>
                    <span className="text-xs text-gray-500">{formatTime(alert.timestamp)}</span>
                  </div>
                  {!alert.acknowledged && (
                    <button
                      onClick={() => acknowledgeAlert(alert.id)}
                      className="flex items-center gap-1 px-2 py-1 bg-white rounded-lg text-xs text-gray-600 hover:bg-gray-50"
                    >
                      <CheckCircle className="w-3 h-3" />
                      确认
                    </button>
                  )}
                </div>
                <p className={`mt-1.5 text-sm font-medium ${cfg.text}`}>{alert.message}</p>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
