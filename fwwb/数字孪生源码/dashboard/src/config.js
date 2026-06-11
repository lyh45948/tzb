// System configuration
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
  factorySize: 24
}

export default config
