import { useState, useEffect, useCallback } from 'react'
import {
  Link,
  Server,
  Car,
  Zap,
  AlertCircle,
  CheckCircle,
  Plus,
  Trash2,
  RefreshCw,
  Monitor,
  Wifi,
  WifiOff,
  ChevronDown,
  ChevronUp,
  Settings2,
} from 'lucide-react'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'
import ConnectionStatus from '@/components/common/ConnectionStatus'
import type { Car as CarType } from '@/types'

export default function BackendConnectPage() {
  const {
    wsConnected,
    carConnected,
    demoMode,
    cars,
    activeCarId,
    sensorData,
    connectionConfig,
    setConnectionConfig,
    setWsConnected,
    setCarConnected,
    setDemoMode,
    setSensorData,
    setCars,
    setActiveCarId,
    addCar,
    removeCar,
  } = useAppStore()

  // 后端配置表单
  const [backendHost, setBackendHost] = useState(connectionConfig.backendHost)
  const [backendPort, setBackendPort] = useState(String(connectionConfig.backendPort))
  const [statusMsg, setStatusMsg] = useState('')
  const [connecting, setConnecting] = useState(false)

  // 添加设备表单
  const [newCarIp, setNewCarIp] = useState('')
  const [newCarPort, setNewCarPort] = useState('7788')
  const [newCarId, setNewCarId] = useState('')
  const [addingCar, setAddingCar] = useState(false)

  // 设备管理面板展开状态
  const [devicePanelOpen, setDevicePanelOpen] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)

  // 监听 WebSocket 消息
  useEffect(() => {
    const handleMessage = (msg: Record<string, unknown>) => {
      if (msg.type === 'connect_result') {
        const success = msg.success as boolean
        const deviceId = msg.deviceId as string
        if (success && deviceId) {
          addCar({
            device_id: deviceId,
            car_ip: newCarIp || connectionConfig.carIp,
            car_port: parseInt(newCarPort) || 7788,
            connected: true,
          })
          setActiveCarId(deviceId)
          setCarConnected(true)
          setShowAddForm(false)
          setNewCarIp('')
          setNewCarId('')
        }
        setStatusMsg(msg.message as string)
        setAddingCar(false)
      }

      if (msg.type === 'disconnect_result') {
        const deviceId = msg.deviceId as string
        if (deviceId) {
          removeCar(deviceId)
        } else {
          setCars([])
          setActiveCarId(null)
          setCarConnected(false)
        }
        setStatusMsg(msg.message as string)
      }

      if (msg.type === 'car_list') {
        const carList = (msg.cars as CarType[]) || []
        setCars(carList)
        setCarConnected(carList.some(c => c.connected))
      }

      if (msg.type === 'switch_car_result') {
        const deviceId = msg.deviceId as string
        if (deviceId) {
          setActiveCarId(deviceId)
        }
        setStatusMsg(msg.message as string)
      }

      if (msg.type === 'realtime' && msg.data) {
        const data = msg.data as Record<string, unknown>
        const env = (data.env as Record<string, number | null>) || {}
        setSensorData({
          temperature: env.temp ?? null,
          humidity: env.humi ?? null,
          light: env.lux ?? null,
          co2: env.co2 ?? null,
          tvoc: env.tvoc ?? null,
          gasMic: env.gasMic ?? null,
        })
      }

      if (msg.type === 'pong') {
        setWsConnected(true)
      }
    }

    const handleConnectionChange = (connected: boolean, message: string) => {
      setWsConnected(connected)
      setStatusMsg(message)
      setConnecting(false)
      if (!connected) {
        setCarConnected(false)
        setCars([])
        setActiveCarId(null)
      }
    }

    wsManager.onMessage(handleMessage)
    wsManager.onConnectionChange(handleConnectionChange)

    return () => {
      wsManager.offMessage(handleMessage)
      wsManager.offConnectionChange(handleConnectionChange)
    }
  }, [setWsConnected, setCarConnected, setSensorData, setCars, setActiveCarId, addCar, removeCar, newCarIp, connectionConfig.carIp, newCarPort])

  // 保存后端配置
  const saveConfig = useCallback(() => {
    const config = {
      backendHost,
      backendPort: parseInt(backendPort) || 8889,
      carIp: connectionConfig.carIp,
      carPort: connectionConfig.carPort,
    }
    setConnectionConfig(config)
  }, [backendHost, backendPort, connectionConfig, setConnectionConfig])

  // 连接后端
  const handleConnectBackend = useCallback(() => {
    saveConfig()
    setConnecting(true)
    setStatusMsg('正在连接...')
    const wsUrl = `ws://${backendHost}:${backendPort}`
    wsManager.connect(wsUrl)
  }, [backendHost, backendPort, saveConfig])

  // 断开后端
  const handleDisconnectBackend = useCallback(() => {
    wsManager.disconnect()
    setWsConnected(false)
    setCarConnected(false)
    setCars([])
    setActiveCarId(null)
    setStatusMsg('已断开连接')
  }, [setWsConnected, setCarConnected, setCars, setActiveCarId])

  // 连接设备
  const handleConnectCar = useCallback(() => {
    if (!newCarIp) {
      setStatusMsg('请输入设备IP地址')
      return
    }
    const deviceId = newCarId.trim() || `car_${newCarIp.replace(/\./g, '_')}`
    setAddingCar(true)
    setStatusMsg('正在连接设备...')
    wsManager.connectToCar(newCarIp, parseInt(newCarPort) || 7788, deviceId)
  }, [newCarIp, newCarPort, newCarId])

  // 断开设备
  const handleDisconnectCar = useCallback((deviceId: string) => {
    wsManager.disconnectFromCar(deviceId)
    setStatusMsg(`正在断开设备 ${deviceId}...`)
  }, [])

  // 切换活跃设备
  const handleSwitchCar = useCallback((deviceId: string) => {
    wsManager.switchCar(deviceId)
  }, [])

  // 刷新设备列表
  const handleRefreshCarList = useCallback(() => {
    wsManager.getCarList()
    setStatusMsg('已请求刷新设备列表')
  }, [])

  // 切换演示模式
  const handleToggleDemo = useCallback(() => {
    const newMode = !demoMode
    setDemoMode(newMode)
    wsManager.setDemoMode(newMode)
    setStatusMsg(newMode ? '演示模式已开启' : '演示模式已关闭')
  }, [demoMode, setDemoMode])

  // 设备状态颜色
  const getStatusColor = (connected: boolean) =>
    connected ? 'text-green-500' : 'text-gray-400'

  // 设备状态文字
  const getStatusText = (connected: boolean) =>
    connected ? '在线' : '离线'

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Link className="w-6 h-6 text-sky-600" />
        连接管理
      </h2>

      {/* 连接状态概览 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
        <ConnectionStatus wsConnected={wsConnected} carConnected={carConnected} />
        {cars.length > 0 && (
          <div className="mt-2 flex items-center gap-2 text-sm text-gray-600">
            <Monitor className="w-4 h-4 text-sky-500" />
            已管理 {cars.length} 台设备
            <button
              onClick={handleRefreshCarList}
              className="ml-auto p-1 hover:bg-gray-100 rounded"
            >
              <RefreshCw className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* 后端配置 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 space-y-4">
        <h3 className="font-semibold text-gray-700 flex items-center gap-2">
          <Server className="w-5 h-5 text-sky-600" />
          WebSocket 后端配置
        </h3>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm text-gray-500 mb-1 block">主机地址</label>
            <input
              type="text"
              value={backendHost}
              onChange={(e) => setBackendHost(e.target.value)}
              placeholder="localhost"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-sm text-gray-500 mb-1 block">端口</label>
            <input
              type="number"
              value={backendPort}
              onChange={(e) => setBackendPort(e.target.value)}
              placeholder="8889"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none text-sm"
            />
          </div>
        </div>

        <div className="flex gap-2">
          {!wsConnected ? (
            <button
              onClick={handleConnectBackend}
              disabled={connecting}
              className="flex-1 flex items-center justify-center gap-2 bg-sky-600 text-white py-2.5 rounded-lg font-medium hover:bg-sky-700 disabled:opacity-50 transition-colors"
            >
              <Zap className="w-4 h-4" />
              {connecting ? '连接中...' : '连接后端'}
            </button>
          ) : (
            <button
              onClick={handleDisconnectBackend}
              className="flex-1 flex items-center justify-center gap-2 bg-red-500 text-white py-2.5 rounded-lg font-medium hover:bg-red-600 transition-colors"
            >
              断开连接
            </button>
          )}
        </div>
      </div>

      {/* 设备管理 */}
      {wsConnected && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          {/* 设备管理标题栏 */}
          <button
            onClick={() => setDevicePanelOpen(!devicePanelOpen)}
            className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
          >
            <h3 className="font-semibold text-gray-700 flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-sky-600" />
              设备管理
              {cars.length > 0 && (
                <span className="ml-1 px-2 py-0.5 bg-sky-100 text-sky-700 text-xs rounded-full">
                  {cars.length}
                </span>
              )}
            </h3>
            {devicePanelOpen ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {devicePanelOpen && (
            <div className="px-4 pb-4 space-y-3">
              {/* 设备列表 */}
              {cars.length > 0 ? (
                <div className="space-y-2">
                  {cars.map((car) => (
                    <div
                      key={car.device_id}
                      className={`border rounded-lg p-3 transition-colors ${
                        activeCarId === car.device_id
                          ? 'border-sky-500 bg-sky-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="relative">
                            <Car className={`w-5 h-5 ${getStatusColor(car.connected)}`} />
                            <span
                              className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white ${
                                car.connected ? 'bg-green-500' : 'bg-gray-300'
                              }`}
                            />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-800">
                              {car.device_id}
                            </p>
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              {car.connected ? (
                                <Wifi className="w-3 h-3 text-green-500" />
                              ) : (
                                <WifiOff className="w-3 h-3 text-gray-400" />
                              )}
                              {car.car_ip}:{car.car_port}
                              <span className="ml-1 text-gray-400">
                                · {getStatusText(car.connected)}
                              </span>
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5">
                          {activeCarId === car.device_id ? (
                            <span className="px-2 py-1 bg-sky-500 text-white text-xs rounded-full font-medium">
                              当前
                            </span>
                          ) : car.connected ? (
                            <button
                              onClick={() => handleSwitchCar(car.device_id)}
                              className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded hover:bg-gray-200 transition-colors"
                            >
                              切换
                            </button>
                          ) : null}
                          <button
                            onClick={() => handleDisconnectCar(car.device_id)}
                            className="p-1.5 bg-red-50 text-red-500 rounded hover:bg-red-100 transition-colors"
                            title="断开连接"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* 活跃设备显示实时数据摘要 */}
                      {activeCarId === car.device_id && car.connected && (
                        <div className="mt-2 pt-2 border-t border-sky-100 grid grid-cols-3 gap-2 text-center">
                          <div className="text-xs">
                            <span className="text-gray-400">温度</span>
                            <p className="font-medium text-gray-700">
                              {sensorData.temperature != null ? `${sensorData.temperature}°C` : '--'}
                            </p>
                          </div>
                          <div className="text-xs">
                            <span className="text-gray-400">湿度</span>
                            <p className="font-medium text-gray-700">
                              {sensorData.humidity != null ? `${sensorData.humidity}%` : '--'}
                            </p>
                          </div>
                          <div className="text-xs">
                            <span className="text-gray-400">CO₂</span>
                            <p className="font-medium text-gray-700">
                              {sensorData.co2 != null ? `${sensorData.co2}ppm` : '--'}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-gray-400">
                  <Car className="w-10 h-10 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">暂无已连接设备</p>
                  <p className="text-xs mt-1">点击下方按钮添加设备</p>
                </div>
              )}

              {/* 添加设备按钮 / 表单 */}
              {!showAddForm ? (
                <button
                  onClick={() => setShowAddForm(true)}
                  className="w-full flex items-center justify-center gap-2 py-2.5 border-2 border-dashed border-gray-300 text-gray-500 rounded-lg hover:border-sky-400 hover:text-sky-600 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  添加设备
                </button>
              ) : (
                <div className="border border-sky-200 rounded-lg p-3 space-y-3 bg-sky-50/30">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
                      <Plus className="w-4 h-4 text-sky-600" />
                      添加新设备
                    </h4>
                    <button
                      onClick={() => setShowAddForm(false)}
                      className="text-xs text-gray-400 hover:text-gray-600"
                    >
                      取消
                    </button>
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    <div className="col-span-2">
                      <label className="text-xs text-gray-500 mb-1 block">设备IP</label>
                      <input
                        type="text"
                        value={newCarIp}
                        onChange={(e) => setNewCarIp(e.target.value)}
                        placeholder="192.168.x.x"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 outline-none text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">端口</label>
                      <input
                        type="number"
                        value={newCarPort}
                        onChange={(e) => setNewCarPort(e.target.value)}
                        placeholder="7788"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 outline-none text-sm"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">设备ID（可选，默认自动生成）</label>
                    <input
                      type="text"
                      value={newCarId}
                      onChange={(e) => setNewCarId(e.target.value)}
                      placeholder="car_001"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 outline-none text-sm"
                    />
                  </div>

                  <button
                    onClick={handleConnectCar}
                    disabled={addingCar || !newCarIp}
                    className="w-full flex items-center justify-center gap-2 bg-green-600 text-white py-2.5 rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {addingCar ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Car className="w-4 h-4" />
                    )}
                    {addingCar ? '连接中...' : '连接设备'}
                  </button>
                </div>
              )}

              {/* 刷新按钮 */}
              <button
                onClick={handleRefreshCarList}
                className="w-full flex items-center justify-center gap-2 py-2 text-gray-500 text-sm hover:text-sky-600 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                刷新设备列表
              </button>
            </div>
          )}
        </div>
      )}

      {/* 演示模式 */}
      {wsConnected && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-700">演示模式</h3>
              <p className="text-xs text-gray-500 mt-0.5">无需硬件，模拟传感器数据</p>
            </div>
            <button
              onClick={handleToggleDemo}
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                demoMode
                  ? 'bg-yellow-500 text-white hover:bg-yellow-600'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {demoMode ? '关闭演示' : '开启演示'}
            </button>
          </div>
        </div>
      )}

      {/* 实时数据预览 */}
      {wsConnected && (cars.length > 0 || demoMode) && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-700 mb-3">实时数据</h3>
          <div className="grid grid-cols-3 gap-2 text-center">
            {[
              { label: '温度', value: sensorData.temperature, unit: '°C' },
              { label: '湿度', value: sensorData.humidity, unit: '%' },
              { label: '光照', value: sensorData.light, unit: 'lux' },
              { label: 'CO2', value: sensorData.co2, unit: 'ppm' },
              { label: 'TVOC', value: sensorData.tvoc, unit: 'ppb' },
              { label: '气体', value: sensorData.gasMic, unit: '' },
            ].map((item) => (
              <div key={item.label} className="bg-gray-50 rounded-lg p-2">
                <p className="text-xs text-gray-500">{item.label}</p>
                <p className="text-lg font-semibold text-gray-800">
                  {item.value != null ? `${item.value}${item.unit}` : '--'}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 状态消息 */}
      {statusMsg && (
        <div
          className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
            statusMsg.includes('成功') || statusMsg.includes('已连接') || statusMsg.includes('已开启')
              ? 'bg-green-50 text-green-700'
              : statusMsg.includes('失败') || statusMsg.includes('错误') || statusMsg.includes('未连接')
                ? 'bg-red-50 text-red-700'
                : 'bg-blue-50 text-blue-700'
          }`}
        >
          {statusMsg.includes('成功') || statusMsg.includes('已连接') || statusMsg.includes('已开启') ? (
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
          )}
          {statusMsg}
        </div>
      )}
    </div>
  )
}
