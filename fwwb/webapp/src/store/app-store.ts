import { create } from 'zustand'
import type {
  SensorData,
  DeviceStatus,
  CarStatus,
  Alert,
  HistoryPoint,
  ThresholdConfig,
  ConnectionConfig,
  Car,
} from '@/types'
import { storage, STORAGE_KEYS } from '@/utils/local-storage'

interface AppState {
  // 连接状态
  wsConnected: boolean
  backendConnected: boolean
  carConnected: boolean
  demoMode: boolean
  autoControl: boolean

  // 传感器数据
  sensorData: SensorData

  // 设备状态
  deviceStatus: DeviceStatus

  // 小车状态
  carStatus: CarStatus

  // 告警
  alerts: Alert[]

  // 历史数据
  historyData: HistoryPoint[]

  // 连接配置
  connectionConfig: ConnectionConfig

  // 阈值配置
  thresholds: ThresholdConfig

  // 多车管理
  cars: Car[]
  activeCarId: string | null

  // Actions
  setWsConnected: (connected: boolean) => void
  setBackendConnected: (connected: boolean) => void
  setCarConnected: (connected: boolean) => void
  setDemoMode: (enabled: boolean) => void
  setAutoControl: (enabled: boolean) => void
  updateSensorData: (data: Partial<SensorData>) => void
  updateDeviceStatus: (data: Partial<DeviceStatus>) => void
  updateCarStatus: (data: Partial<CarStatus>) => void
  setSensorData: (data: SensorData) => void
  setDeviceStatus: (status: DeviceStatus) => void
  setCarStatus: (status: CarStatus) => void
  addAlert: (alert: Alert) => void
  acknowledgeAlert: (id: string) => void
  clearAlerts: () => void
  addHistoryPoint: (point: HistoryPoint) => void
  setConnectionConfig: (config: Partial<ConnectionConfig>) => void
  setThresholds: (thresholds: Partial<ThresholdConfig>) => void
  setCars: (cars: Car[]) => void
  setActiveCarId: (id: string | null) => void
  addCar: (car: Car) => void
  removeCar: (deviceId: string) => void
  updateCar: (deviceId: string, updates: Partial<Car>) => void
}

const defaultSensorData: SensorData = {
  temperature: null,
  humidity: null,
  light: null,
  co2: null,
  tvoc: null,
  gasMic: null,
  ps: null,
  ir: null,
  fan: 0,
  led: 0,
  buzzer: 0,
}

const defaultDeviceStatus: DeviceStatus = {
  pump: false,
  valve: false,
  led: false,
  fan: false,
  buzzer: false,
}

const defaultCarStatus: CarStatus = {
  status: 'off',
  mode: 'manual',
  L_spd: 0,
  R_spd: 0,
  carPower: null,
  distance: null,
}

const defaultThresholds: ThresholdConfig = {
  tempWarning: 30,
  tempDanger: 35,
  humiWarning: 75,
  humiDanger: 80,
  co2Warning: 800,
  co2Danger: 1000,
  smokeWarning: 300,
  smokeDanger: 500,
  coWarning: 35,
  coDanger: 50,
  distanceWarning: 30,
  distanceDanger: 15,
}

const defaultConnectionConfig: ConnectionConfig = {
  backendHost: 'localhost',
  backendPort: 8889,
  carIp: '',
  carPort: 7788,
}

// 从 localStorage 加载持久化配置
function loadPersistedConfig(): {
  connectionConfig: ConnectionConfig
  thresholds: ThresholdConfig
  demoMode: boolean
  autoControl: boolean
} {
  const savedConfig = storage.get<ConnectionConfig>(STORAGE_KEYS.CONNECTION_CONFIG)
  const savedThresholds = storage.get<ThresholdConfig>(STORAGE_KEYS.THRESHOLDS)
  const savedDemoMode = storage.get<boolean>(STORAGE_KEYS.DEMO_MODE)
  const savedAutoControl = storage.get<boolean>(STORAGE_KEYS.AUTO_CONTROL)

  return {
    connectionConfig: savedConfig || { ...defaultConnectionConfig },
    thresholds: savedThresholds || { ...defaultThresholds },
    demoMode: savedDemoMode || false,
    autoControl: savedAutoControl || false,
  }
}

const persisted = loadPersistedConfig()

export const useAppStore = create<AppState>((set, get) => ({
  // 运行时状态（不持久化）
  wsConnected: false,
  backendConnected: false,
  carConnected: false,

  // 持久化状态（从 localStorage 加载）
  demoMode: persisted.demoMode,
  autoControl: persisted.autoControl,
  connectionConfig: persisted.connectionConfig,
  thresholds: persisted.thresholds,

  // 其他运行时状态
  sensorData: { ...defaultSensorData },
  deviceStatus: { ...defaultDeviceStatus },
  carStatus: { ...defaultCarStatus },
  alerts: [],
  historyData: [],
  cars: [],
  activeCarId: null,

  setWsConnected: (connected) => set({ wsConnected: connected }),
  setBackendConnected: (connected) => set({ backendConnected: connected }),
  setCarConnected: (connected) => set({ carConnected: connected }),

  setDemoMode: (enabled) => {
    storage.set(STORAGE_KEYS.DEMO_MODE, enabled)
    set({ demoMode: enabled })
  },

  setAutoControl: (enabled) => {
    storage.set(STORAGE_KEYS.AUTO_CONTROL, enabled)
    set({ autoControl: enabled })
  },

  updateSensorData: (data) =>
    set((state) => ({
      sensorData: { ...state.sensorData, ...data },
    })),

  updateDeviceStatus: (data) =>
    set((state) => ({
      deviceStatus: { ...state.deviceStatus, ...data },
    })),

  updateCarStatus: (data) =>
    set((state) => ({
      carStatus: { ...state.carStatus, ...data },
    })),

  setSensorData: (data) => set({ sensorData: data }),
  setDeviceStatus: (status) => set({ deviceStatus: status }),
  setCarStatus: (status) => set({ carStatus: status }),

  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts].slice(0, 100),
    })),

  acknowledgeAlert: (id) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.id === id ? { ...a, acknowledged: true } : a
      ),
    })),

  clearAlerts: () => set({ alerts: [] }),

  addHistoryPoint: (point) =>
    set((state) => ({
      historyData: [...state.historyData, point].slice(-60),
    })),

  setConnectionConfig: (config) => {
    const newConfig = { ...get().connectionConfig, ...config }
    storage.set(STORAGE_KEYS.CONNECTION_CONFIG, newConfig)
    set({ connectionConfig: newConfig })
  },

  setThresholds: (thresholds) => {
    const newThresholds = { ...get().thresholds, ...thresholds }
    storage.set(STORAGE_KEYS.THRESHOLDS, newThresholds)
    set({ thresholds: newThresholds })
  },

  setCars: (cars) => set({ cars }),
  setActiveCarId: (id) => set({ activeCarId: id }),

  addCar: (car) =>
    set((state) => ({
      cars: [...state.cars.filter(c => c.device_id !== car.device_id), car],
      carConnected: true,
    })),

  removeCar: (deviceId) =>
    set((state) => {
      const newCars = state.cars.filter(c => c.device_id !== deviceId)
      return {
        cars: newCars,
        carConnected: newCars.some(c => c.connected),
        activeCarId: state.activeCarId === deviceId
          ? (newCars.length > 0 ? newCars[0].device_id : null)
          : state.activeCarId,
      }
    }),

  updateCar: (deviceId, updates) =>
    set((state) => ({
      cars: state.cars.map(c =>
        c.device_id === deviceId ? { ...c, ...updates } : c
      ),
    })),
}))
