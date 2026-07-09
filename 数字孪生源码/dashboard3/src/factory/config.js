// System configuration — 数字孪生 factory 模块配置
//
// 本文件是 factory 模块的配置单一来源。factory/services 与 stores 中的代码通过
// `import config from '../config'`（相对 factory/ 内的文件）或 `'../../config'`
// （相对 factory/components/three/ 内的文件）引用本文件。
//
// 迁移自旧 dashboard3 的 src/config-factory.js（原为孤儿文件，未被正确引用）。
const env = typeof import.meta !== 'undefined' ? import.meta.env || {} : {}

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
  apiBaseUrl: env.VITE_FACTORY_API_URL || 'http://localhost:5000',

  // 是否启用真实数据接入（false = 启动后立即走本地模拟，不连后端）
  enableLiveData: (env.VITE_ENABLE_LIVE_DATA ?? 'true').toString().toLowerCase() !== 'false',

  // SSE 失败降级为轮询时的间隔（ms）
  pollIntervalMs: 2000,

  // 轮询连续失败到达此次数后，回退到前端本地模拟
  pollFailFallbackCount: 3
}

export default config
