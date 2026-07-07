import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import HomePage from '@/pages/HomePage'
import ControlPage from '@/pages/ControlPage'
import BackendConnectPage from '@/pages/BackendConnectPage'
import EnvironmentPage from '@/pages/EnvironmentPage'
import FactoryDashboardPage from '@/pages/FactoryDashboardPage'
import EquipmentControlPage from '@/pages/EquipmentControlPage'
import AlertCenterPage from '@/pages/AlertCenterPage'
import MonitorPage from '@/pages/MonitorPage'
import PathPlanningPage from '@/pages/PathPlanningPage'
import RecordPlaybackPage from '@/pages/RecordPlaybackPage'
import VirtualFencePage from '@/pages/VirtualFencePage'
import SettingsPage from '@/pages/SettingsPage'
import NfcPage from '@/pages/NfcPage'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'
import type { LinkageConfig, WSMessage } from '@/types'

function App() {
  // 页面加载时自动恢复 WebSocket 连接
  useEffect(() => {
    const config = useAppStore.getState().connectionConfig
    if (config.backendHost && config.backendPort) {
      const wsUrl = `ws://${config.backendHost}:${config.backendPort}`
      console.log('[App] 自动恢复 WebSocket 连接:', wsUrl)
      wsManager.connect(wsUrl)
    }
  }, [])

  // 注册全局消息处理：linkage_config 响应（获取/广播）写入 store
  useEffect(() => {
    const handleMessage = (msg: WSMessage) => {
      if (msg.type === 'linkage_config' && msg.success && msg.config) {
        useAppStore.getState().setLinkageConfig(msg.config as LinkageConfig)
      }
    }
    wsManager.onMessage(handleMessage)
    return () => wsManager.offMessage(handleMessage)
  }, [])

  // 连接成功后拉一次最新配置（覆盖 localStorage 中可能过期的本地副本）
  useEffect(() => {
    const handleConnectionChange = (connected: boolean) => {
      if (connected) {
        // 略延迟一下，给后端 ping 握手时间
        setTimeout(() => wsManager.getLinkageConfig(), 200)
      }
    }
    wsManager.onConnectionChange(handleConnectionChange)
    return () => wsManager.offConnectionChange(handleConnectionChange)
  }, [])

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/control" element={<ControlPage />} />
        <Route path="/connect" element={<BackendConnectPage />} />
        <Route path="/environment" element={<EnvironmentPage />} />
        <Route path="/factory" element={<FactoryDashboardPage />} />
        <Route path="/equipment" element={<EquipmentControlPage />} />
        <Route path="/alerts" element={<AlertCenterPage />} />
        <Route path="/monitor" element={<MonitorPage />} />
        <Route path="/path" element={<PathPlanningPage />} />
        <Route path="/record" element={<RecordPlaybackPage />} />
        <Route path="/fence" element={<VirtualFencePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/nfc" element={<NfcPage />} />
      </Routes>
    </AppLayout>
  )
}

export default App