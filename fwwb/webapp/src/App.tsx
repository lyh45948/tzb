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