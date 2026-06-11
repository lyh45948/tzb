// config-manager.js - 配置管理（含阈值配置）
const STORAGE_KEY = 'smart_agriculture_config';

// 默认配置
const defaultConfig = {
  demoMode: false,
  autoControl: false,
  deviceIP: '192.168.1.100',
  devicePort: 7788
};

// 默认阈值配置
const defaultThresholds = {
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
  soilMoisture: {
    min: 30,
    max: 70,
    unit: '%',
    name: '土壤湿度'
  },
  co2: {
    min: 400,
    max: 1000,
    unit: 'ppm',
    name: 'CO2'
  }
};

// 获取配置
function getConfig() {
  try {
    const config = wx.getStorageSync(STORAGE_KEY);
    return { ...defaultConfig, ...config };
  } catch (e) {
    console.error('读取配置失败:', e);
    return { ...defaultConfig };
  }
}

// 保存配置
function saveConfig(config) {
  try {
    const oldConfig = getConfig();
    const newConfig = { ...oldConfig, ...config };
    wx.setStorageSync(STORAGE_KEY, newConfig);
    console.log('配置已保存:', newConfig);
    return true;
  } catch (e) {
    console.error('保存配置失败:', e);
    return false;
  }
}

// 获取阈值配置
function getThresholds() {
  try {
    const thresholds = wx.getStorageSync(STORAGE_KEY + '_thresholds');
    return { ...defaultThresholds, ...thresholds };
  } catch (e) {
    console.error('读取阈值失败:', e);
    return { ...defaultThresholds };
  }
}

// 保存阈值配置
function saveThresholds(thresholds) {
  try {
    const oldThresholds = getThresholds();
    const newThresholds = { ...oldThresholds };

    // 合并阈值
    for (const key in thresholds) {
      if (newThresholds[key]) {
        newThresholds[key] = { ...newThresholds[key], ...thresholds[key] };
      }
    }

    wx.setStorageSync(STORAGE_KEY + '_thresholds', newThresholds);
    console.log('阈值已保存:', newThresholds);
    return true;
  } catch (e) {
    console.error('保存阈值失败:', e);
    return false;
  }
}

// 检查单个阈值
function checkThreshold(type, value) {
  const thresholds = getThresholds();
  const threshold = thresholds[type];

  if (!threshold) {
    return { normal: true };
  }

  if (value < threshold.min) {
    return {
      normal: false,
      level: 'low',
      message: threshold.name + '过低: ' + value + threshold.unit
    };
  }

  if (value > threshold.max) {
    return {
      normal: false,
      level: 'high',
      message: threshold.name + '过高: ' + value + threshold.unit
    };
  }

  return { normal: true };
}

// 重置配置
function resetConfig() {
  try {
    wx.removeStorageSync(STORAGE_KEY);
    wx.removeStorageSync(STORAGE_KEY + '_thresholds');
    console.log('配置已重置');
    return true;
  } catch (e) {
    console.error('重置配置失败:', e);
    return false;
  }
}

module.exports = {
  getConfig,
  saveConfig,
  getThresholds,
  saveThresholds,
  checkThreshold,
  resetConfig,
  defaultConfig,
  defaultThresholds
};
