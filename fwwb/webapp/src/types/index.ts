// 传感器数据
export interface SensorData {
  temperature: number | null
  humidity: number | null
  light: number | null
  co2: number | null
  tvoc: number | null
  gasMic: number | null
  ps?: number | null
  ir?: number | null
  fan?: number
  led?: number
  buzzer?: number
}

// 设备状态
export interface DeviceStatus {
  pump: boolean
  valve: boolean
  led: boolean
  fan: boolean
  buzzer: boolean
}

// 小车状态
export interface CarStatus {
  status: string      // on/off/run/back/left/right/stop
  mode: string        // manual/avoid/line/path
  L_spd: number
  R_spd: number
  carPower: number | null
  distance: number | null
}

// 告警
export interface Alert {
  id: string
  level: 'warning' | 'danger' | 'critical'
  type: string
  message: string
  timestamp: number
  acknowledged: boolean
}

// 环境数据（来自小车）
export interface EnvData {
  temp: number | null
  humi: number | null
  lux: number | null
  co2: number | null
  tvoc: number | null
  gasStatus: number | null
  gasMic: number | null
  ps: number | null
  ir: number | null
  fan: number
  led: number
  buzzer: number
  agri?: {
    co2: number
    tvoc: number
    gasStatus: number
    gasMic: number
    flameStatus: number
  }
}

// 实时数据消息
export interface RealtimeData {
  carStatus: string
  carMode: string
  L_spd: number
  R_spd: number
  carPower: number | null
  distance: number | null
  env: EnvData
  imu?: {
    tid: number
    accel: { x: number; y: number; z: number }
    gyro: { x: number; y: number; z: number }
    euler: { pitch: number; roll: number; yaw: number }
  }
  lidar?: {
    speed: number
    points: number[]
  }
  timestamp?: number
}

// WebSocket消息类型
export interface WSMessage {
  type: string
  [key: string]: unknown
}

// 历史数据点
export interface HistoryPoint {
  timestamp: number
  temperature: number
  humidity: number
  light: number
  co2: number
}

// 连接配置
export interface ConnectionConfig {
  backendHost: string
  backendPort: number
  carIp: string
  carPort: number
}

// 阈值配置
// 注意：tempWarning/humiWarning/coWarning 等仅 webapp 本地用于显示告色（橙/红）；
// 后端实际告警分级用 co2/tvoc/smoke/distance 这几路。tvocWarning/tvocDanger 字段虽是新增，
// 在 SettingsPage 上不一定显示，主要供后端联动使用。
export interface ThresholdConfig {
  tempWarning: number
  tempDanger: number
  humiWarning: number
  humiDanger: number
  co2Warning: number
  co2Danger: number
  smokeWarning: number
  smokeDanger: number
  tvocWarning: number
  tvocDanger: number
  coWarning: number
  coDanger: number
  distanceWarning: number
  distanceDanger: number
}

// 联动控制器配置（与后端 LinkageController.get_config 一一对应）
// 字段命名 camelCase；除 tvoc/distance 复用 ThresholdConfig 外，其余仅在此结构内
export interface LinkageConfig {
  // 风扇联动（双门限回滞）
  fanTempOn: number
  fanTempOff: number
  fanHumiOn: number
  fanHumiOff: number
  // 人体感应联动（PIR/AP3216C）
  irPs: number
  irIr: number
  irDebounceOn: number
  irDebounceOff: number
  // 联动控制器节奏
  tickSeconds: number
  manualOverrideTtl: number
  rgbBlinkHz: number
  // 告警阈值（与 ThresholdConfig 部分字段重叠，后端是唯一可信源）
  co2Warning: number
  co2Danger: number
  tvocWarning: number
  tvocDanger: number
  gasMicWarning: number
  gasMicDanger: number
  distanceWarning: number
  distanceDanger: number
}

// 已连接小车
export interface Car {
  device_id: string
  car_ip: string
  car_port: number
  connected: boolean
  last_receive_time?: string
}

// 导航项
export interface NavItem {
  path: string
  label: string
  icon: string
}
