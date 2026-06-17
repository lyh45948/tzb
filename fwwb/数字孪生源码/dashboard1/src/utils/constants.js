// Robot status mapping
export const ROBOT_STATUS_MAP = {
  idle: { label: '待机', color: '#94a3b8' },
  patrolling: { label: '巡检中', color: '#2563eb' },
  avoiding: { label: '避障中', color: '#f59e0b' },
  lineTracking: { label: '巡线中', color: '#06b6d4' },
  pathExecuting: { label: '路径执行', color: '#22c55e' },
  warning: { label: '告警', color: '#ef4444' },
  offline: { label: '离线', color: '#64748b' },
  charging: { label: '充电中', color: '#8b5cf6' }
}

export const ROBOT_TASK_MAP = {
  patrol: { label: '区域巡检', color: '#2563eb' },
  gasMonitor: { label: '危气监测', color: '#ef4444' },
  goodsCount: { label: '货物计数', color: '#22c55e' },
  smartLighting: { label: '智能照明', color: '#f59e0b' },
  obstacleAvoidance: { label: 'AGV调度', color: '#06b6d4' },
  materialTransfer: { label: '物料转运', color: '#ff6f00' },
  idle: { label: '空闲待命', color: '#94a3b8' }
}

export const SPEED_GEAR_MAP = {
  low: { label: '低速', value: 500 },
  middle: { label: '中速', value: 800 },
  high: { label: '高速', value: 1100 }
}

export const ALERT_LEVEL_MAP = {
  normal: { label: '正常', color: '#22c55e' },
  warning: { label: '警告', color: '#f59e0b' },
  danger: { label: '危险', color: '#ef4444' },
  critical: { label: '紧急', color: '#7f1d1d' }
}

export const TIME_PERIOD_MAP = {
  0: '黎明巡检',
  1: '上午生产',
  2: '中午稳态',
  3: '下午生产',
  4: '黄昏补光',
  5: '晚间安全',
  6: '深夜休眠'
}

export const LIGHT_LEVEL_MAP = {
  0: '黑暗',
  1: '昏暗',
  2: '偏暗',
  3: '正常',
  4: '明亮',
  5: '强光'
}

export const COMMAND_SOURCE_MAP = {
  system: '系统联动',
  webapp: 'Web演示',
  miniapp: '小程序',
  mock: '模拟数据'
}

// ECharts light theme base
export const ECHART_THEME = {
  backgroundColor: 'transparent',
  textStyle: { color: '#64748b' },
  title: { textStyle: { color: '#1e293b' } },
  legend: { textStyle: { color: '#64748b' } },
  grid: {
    left: 40,
    right: 15,
    top: 30,
    bottom: 25
  }
}

// Sensor normal ranges for smart factory safety monitoring
export const SENSOR_RANGES = {
  temperature: { min: 0, max: 60, warnHigh: 30, dangerHigh: 35, unit: '℃' },
  humidity: { min: 0, max: 100, warnHigh: 75, dangerHigh: 80, unit: '%' },
  lux: { min: 0, max: 2000, warnLow: 100, warnHigh: 1600, unit: 'lux' },
  co2: { min: 0, max: 100, warnHigh: 35, dangerHigh: 50, unit: 'ppm' },
  tvoc: { min: 0, max: 1200, warnHigh: 600, dangerHigh: 900, unit: 'ppb' },
  // 当前前端仍按演示模拟值 300/500 触发；未来接真实后端前需再次确认接口文档量程
  gasMic: { min: 0, max: 1000, warnHigh: 300, dangerHigh: 500, unit: '' },
  distanceCm: { min: 0, max: 200, warnLow: 30, dangerLow: 15, unit: 'cm' },
  distanceMm: { min: 0, max: 2000, warnLow: 300, dangerLow: 150, unit: 'mm' },
  goodsCount: { min: 0, max: 9999, unit: '件' }
}
