// System configuration
const env = typeof import.meta !== 'undefined' ? (import.meta.env || {}) : {}

const config = {
  // Demo mode is always on - generates simulated data
  demoMode: true,

  // Data update interval (ms)
  chartUpdateInterval: 1000,

  // Max data points in realtime charts
  maxDataPoints: 60,

  // Number of factory mobile devices in the scene
  robotCount: 4,

  // Factory device names
  robotNames: ['AGV-01', '巡检车-01', '物料车-01', '安防巡检-02'],

  // Device colors (hex)
  robotColors: [0x1a73e8, 0x00a86b, 0xff6f00, 0x7c3aed],

  // Factory floor size
  factorySize: 24,

  // ─── 后端数据接入配置 ───
  // 后端 REST + SSE 的 base URL（开发期默认指向本地 backend Flask）
  apiBaseUrl: env.VITE_API_BASE_URL || 'http://localhost:5000',

  // 是否启用真实数据接入（false = 启动后立即走本地模拟，不连后端）
  enableLiveData: (env.VITE_ENABLE_LIVE_DATA ?? 'true').toString().toLowerCase() !== 'false',

  // SSE 失败降级为轮询时的间隔（ms）
  pollIntervalMs: 2000,

  // 轮询连续失败到达此次数后，回退到前端本地模拟
  pollFailFallbackCount: 3
}

export default config
