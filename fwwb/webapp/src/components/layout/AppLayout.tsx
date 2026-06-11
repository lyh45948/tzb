import { ReactNode, useEffect } from 'react'
import Header from './Header'
import BottomNav from './BottomNav'
import { useAppStore } from '@/store/app-store'
import { wsManager } from '@/services/websocket-manager'

interface AppLayoutProps {
  children: ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  // 全局 WebSocket 消息监听 — 始终挂载，负责同步数据和状态
  useEffect(() => {
    const {
      setCars,
      setCarConnected,
      setActiveCarId,
      updateSensorData,
      updateCarStatus,
      updateDeviceStatus,
    } = useAppStore.getState()

    const handleMessage = (msg: Record<string, unknown>) => {
      // 同步小车列表
      if (msg.type === 'car_list') {
        const carList = (msg.cars as Array<{
          device_id: string
          car_ip: string
          car_port: number
          connected: boolean
        }>) || []
        setCars(carList)
        setCarConnected(carList.some((c) => c.connected))

        // 如果有已连接的小车但没有活跃小车，自动切换到第一辆
        const connectedCar = carList.find((c) => c.connected)
        if (connectedCar) {
          setActiveCarId(connectedCar.device_id)
          wsManager.switchCar(connectedCar.device_id)
        }
      }

      // 连接结果
      if (msg.type === 'connect_result') {
        const success = Boolean(msg.success)
        setCarConnected(success)
      }

      // 断开结果
      if (msg.type === 'disconnect_result') {
        setCarConnected(false)
        setActiveCarId(null)
      }

      // 同步传感器数据（所有页面共享）
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
      }
    }

    wsManager.onMessage(handleMessage)
    return () => wsManager.offMessage(handleMessage)
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 flex justify-center">
      <div className="w-full max-w-md min-h-screen bg-white shadow-xl relative flex flex-col">
        <Header />
        <main className="flex-1 overflow-y-auto pb-20">
          {children}
        </main>
        <BottomNav />
      </div>
    </div>
  )
}
