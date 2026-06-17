/**
 * localStorage 封装 - 替代微信小程序 wx.getStorageSync / wx.setStorageSync
 */

export const storage = {
  get<T>(key: string, defaultValue?: T): T | undefined {
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : defaultValue
    } catch {
      return defaultValue
    }
  },

  set(key: string, value: unknown): void {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch (e) {
      console.error('Storage set error:', e)
    }
  },

  remove(key: string): void {
    localStorage.removeItem(key)
  },

  clear(): void {
    localStorage.clear()
  }
}

// 配置存储键名
export const STORAGE_KEYS = {
  NETWORK_CONFIG: 'network_config',
  CONNECTION_CONFIG: 'connection_config',
  DEMO_MODE: 'demo_mode_enabled',
  THRESHOLDS: 'smart_car_thresholds',
  LINKAGE_CONFIG: 'smart_car_linkage_config',
  AUTO_CONTROL: 'auto_control_enabled',
  SAVED_PATHS: 'saved_paths',
  SAVED_FENCES: 'saved_fences',
  ERROR_LOG: 'error_log',
} as const
