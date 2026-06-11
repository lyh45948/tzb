/**
 * 配置管理器 - 统一管理应用配置
 */
const errorHandler = require('./error-handler');

const CONFIG_KEY = 'smart_car_config';
const THRESHOLD_KEY = 'smart_car_thresholds';

const DEFAULT_CONFIG = {
  ip: '',
  port: 7788,
  autoReconnect: true,
  heartbeatInterval: 3000,
  maxReconnectAttempts: 10,
  connectionTimeout: 10000,
  logLevel: 'info',
  // 农业相关配置
  autoControl: false,
  demoMode: false
};

// 默认阈值配置（融合 smart_agriculture 的阈值管理）
const DEFAULT_THRESHOLDS = {
  temperature: {
    min: 15,
    max: 35,
    unit: '°C',
    name: '温度'
  },
  humidity: {
    min: 40,
    max: 80,
    unit: '%',
    name: '湿度'
  },
  light: {
    min: 500,
    max: 5000,
    unit: 'lux',
    name: '光照'
  },
  co2: {
    min: 400,
    max: 1000,
    unit: 'ppm',
    name: 'CO2'
  }
};

class ConfigManager {
  constructor() {
    this.config = { ...DEFAULT_CONFIG };
  }

  /**
   * 初始化配置管理器
   */
  init() {
    this.load();
    console.log('[ConfigManager] 配置管理器已初始化:', this.config);
  }

  /**
   * 从本地存储加载配置
   */
  load() {
    try {
      const savedConfig = wx.getStorageSync(CONFIG_KEY);
      if (savedConfig) {
        this.config = { ...DEFAULT_CONFIG, ...savedConfig };
        console.log('[ConfigManager] 已加载保存的配置:', this.config);
      }
    } catch (error) {
      console.error('[ConfigManager] 加载配置失败:', error);
      this.config = { ...DEFAULT_CONFIG };
    }
  }

  /**
   * 保存配置
   */
  save(config = {}) {
    try {
      this.config = { ...this.config, ...config };
      wx.setStorageSync(CONFIG_KEY, this.config);
      console.log('[ConfigManager] 配置已保存:', this.config);
      return true;
    } catch (error) {
      console.error('[ConfigManager] 保存配置失败:', error);
      errorHandler.handle('config_error', '保存配置失败: ' + error.message);
      return false;
    }
  }

  /**
   * 获取配置
   */
  get(key) {
    if (key) {
      return this.config[key];
    }
    return this.config;
  }

  /**
   * 设置配置
   */
  set(key, value) {
    this.config[key] = value;
    return this.save({ [key]: value });
  }

  /**
   * 重置配置为默认值
   */
  reset() {
    this.config = { ...DEFAULT_CONFIG };
    return this.save();
  }

  /**
   * 获取阈值配置
   */
  getThresholds() {
    try {
      const thresholds = wx.getStorageSync(THRESHOLD_KEY);
      if (thresholds) {
        return { ...DEFAULT_THRESHOLDS, ...thresholds };
      }
    } catch (error) {
      console.error('[ConfigManager] 加载阈值配置失败:', error);
    }
    return { ...DEFAULT_THRESHOLDS };
  }

  /**
   * 保存阈值配置
   */
  saveThresholds(thresholds) {
    try {
      const oldThresholds = this.getThresholds();
      const newThresholds = { ...oldThresholds };
      
      // 合并阈值
      for (const key in thresholds) {
        if (newThresholds[key]) {
          newThresholds[key] = { ...newThresholds[key], ...thresholds[key] };
        }
      }
      
      wx.setStorageSync(THRESHOLD_KEY, newThresholds);
      console.log('[ConfigManager] 阈值配置已保存:', newThresholds);
      return true;
    } catch (error) {
      console.error('[ConfigManager] 保存阈值配置失败:', error);
      errorHandler.handle('config_error', '保存阈值配置失败：' + error.message);
      return false;
    }
  }

  /**
   * 检查阈值
   */
  checkThreshold(type, value) {
    const thresholds = this.getThresholds();
    const threshold = thresholds[type];
    
    if (!threshold) {
      return { normal: true };
    }
    
    if (value < threshold.min) {
      return {
        normal: false,
        level: 'low',
        message: threshold.name + '过低：' + value + threshold.unit
      };
    }
    
    if (value > threshold.max) {
      return {
        normal: false,
        level: 'high',
        message: threshold.name + '过高：' + value + threshold.unit
      };
    }
    
    return { normal: true };
  }

  /**
   * 重置阈值配置
   */
  resetThresholds() {
    try {
      wx.removeStorageSync(THRESHOLD_KEY);
      console.log('[ConfigManager] 阈值配置已重置');
      return true;
    } catch (error) {
      console.error('[ConfigManager] 重置阈值配置失败:', error);
      return false;
    }
  }

  /**
   * 验证IP地址
   */
  validateIP(ip) {
    const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipPattern.test(ip)) {
      return { valid: false, message: 'IP地址格式错误' };
    }
    
    const parts = ip.split('.');
    for (const part of parts) {
      const num = parseInt(part, 10);
      if (isNaN(num) || num < 0 || num > 255) {
        return { valid: false, message: 'IP地址数值范围错误(0-255)' };
      }
    }
    
    return { valid: true };
  }

  /**
   * 验证端口号
   */
  validatePort(port) {
    const num = parseInt(port, 10);
    if (isNaN(num) || num < 1 || num > 65535) {
      return { valid: false, message: '端口号范围错误(1-65535)' };
    }
    return { valid: true };
  }
}

// 创建单例
const configManager = new ConfigManager();

module.exports = configManager;

