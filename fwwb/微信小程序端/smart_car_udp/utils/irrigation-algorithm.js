/**
 * 智能灌溉算法
 * 前端水量计算，用于离线计算或快速预览
 */

/**
 * 数据平滑器 - 使用滑动窗口平均值减少数据波动
 */
class DataSmoother {
  constructor(windowSize = 10) {
    this.windowSize = windowSize;
    this.buffers = {};
  }

  /**
   * 添加数据并获取平滑后的平均值
   * @param {string} key - 数据键名
   * @param {number} value - 新数据值
   * @returns {number} - 平滑后的平均值
   */
  addAndGetAverage(key, value) {
    if (!this.buffers[key]) {
      this.buffers[key] = [];
    }

    this.buffers[key].push(value);

    // 保持窗口大小
    if (this.buffers[key].length > this.windowSize) {
      this.buffers[key].shift();
    }

    // 计算平均值
    const buffer = this.buffers[key];
    if (buffer.length === 0) return value;

    const avg = buffer.reduce((sum, v) => sum + v, 0) / buffer.length;

    // 根据数据类型返回不同精度
    return Number.isInteger(value) ? Math.round(avg) : Math.round(avg * 10) / 10;
  }

  /**
   * 获取当前平均值（不添加新数据）
   */
  getAverage(key) {
    const buffer = this.buffers[key];
    if (!buffer || buffer.length === 0) return null;
    const avg = buffer.reduce((sum, v) => sum + v, 0) / buffer.length;
    return Math.round(avg * 10) / 10;
  }

  /**
   * 清除缓冲区
   */
  clear(key) {
    if (key) {
      delete this.buffers[key];
    } else {
      this.buffers = {};
    }
  }
}

// 全局数据平滑器实例（用于灌溉水量）
const irrigationSmoother = new DataSmoother(5);

// 季节因子配置
const SEASON_FACTORS = {
  spring: { factor: 1.1, name: '春季' },   // 万物生长，需水增加10%
  summer: { factor: 1.3, name: '夏季' },   // 高温蒸发，需水增加30%
  autumn: { factor: 1.0, name: '秋季' },   // 基准值
  winter: { factor: 0.7, name: '冬季' }    // 低温休眠，需水减少30%
};

/**
 * 获取当前季节
 * @param {number} month - 月份 (1-12)
 * @returns {Object} - 季节配置
 */
function getSeason(month) {
  if (month === null || month === undefined) {
    month = new Date().getMonth() + 1;
  }

  if (month >= 3 && month <= 5) {
    return { key: 'spring', ...SEASON_FACTORS.spring };
  } else if (month >= 6 && month <= 8) {
    return { key: 'summer', ...SEASON_FACTORS.summer };
  } else if (month >= 9 && month <= 11) {
    return { key: 'autumn', ...SEASON_FACTORS.autumn };
  } else {
    return { key: 'winter', ...SEASON_FACTORS.winter };
  }
}

/**
 * 计算灌溉水量（改用空气湿度）
 * @param {Object} sensorData - 传感器数据
 * @param {number} sensorData.temperature - 温度 (℃)
 * @param {number} sensorData.humidity - 湿度 (%)
 * @param {number} sensorData.light - 光照强度 (lux)
 * @param {Array} recentIrrigations - 最近灌溉记录
 * @param {number} baseAmount - 基础水量 (ml)
 * @returns {Object} - 计算结果
 */
function calculateWaterAmount(sensorData, recentIrrigations = [], baseAmount = 500) {
  let { temperature, humidity, light } = sensorData;

  // 计算各因子（湿度因子已包含灌溉需求判断）
  const tempFactor = calcTemperatureFactor(temperature);
  const humiFactor = calcHumidityFactor(humidity);
  const lightFactor = calcLightFactor(light);
  const historyFactor = calcHistoryFactor(recentIrrigations);
  const season = getSeason();
  const seasonFactor = season.factor;

  // 计算总水量（包含季节因子）
  let waterAmount = baseAmount * tempFactor * humiFactor * lightFactor * historyFactor * seasonFactor;
  waterAmount = Math.round(waterAmount * 10) / 10;

  // 对灌溉水量进行平滑处理，减少频繁变化
  waterAmount = irrigationSmoother.addAndGetAverage('waterAmount', waterAmount);

  // 限制范围
  waterAmount = Math.max(100, Math.min(2000, waterAmount));

  return {
    recommendedWater: waterAmount,
    baseAmount: baseAmount,
    season: season.name,
    factors: {
      temperature: Math.round(tempFactor * 1000) / 1000,
      humidity: Math.round(humiFactor * 1000) / 1000,
      light: Math.round(lightFactor * 1000) / 1000,
      history: Math.round(historyFactor * 1000) / 1000,
      season: Math.round(seasonFactor * 1000) / 1000
    }
  };
}

/**
 * 计算温度因子
 * 25°C为基准，每高1°C增加2%
 */
function calcTemperatureFactor(temperature) {
  if (temperature === null || temperature === undefined) return 1.0;
  return 1 + (temperature - 25) * 0.02;
}

/**
 * 计算湿度因子（用于灌溉需求判断）
 * 60%为基准，每低1%增加1.5%（增强湿度对灌溉的影响）
 * 湿度越低越需要灌溉
 */
function calcHumidityFactor(humidity) {
  if (humidity === null || humidity === undefined) return 1.0;
  return 1 + (60 - humidity) * 0.015;
}

/**
 * 计算光照因子
 * 光照越强需水越多
 */
function calcLightFactor(light) {
  if (light === null || light === undefined) return 1.0;
  return 1 + (light / 10000) * 0.1;
}

/**
 * 计算历史因子
 * 根据最近灌溉记录调整水量
 */
function calcHistoryFactor(recentIrrigations) {
  if (!recentIrrigations || recentIrrigations.length === 0) {
    return 1.0;
  }

  // 最近1小时内灌溉过 → 降低水量
  const now = new Date();
  const lastIrrigation = recentIrrigations[0];
  if (lastIrrigation && lastIrrigation.time) {
    const lastTime = new Date(lastIrrigation.time);
    const hoursDiff = (now - lastTime) / (1000 * 60 * 60);
    if (hoursDiff < 1) {
      return 0.5;
    }
  }

  // 3小时内灌溉总量超过2000ml → 降低水量
  let totalWater = 0;
  for (let i = 0; i < Math.min(3, recentIrrigations.length); i++) {
    if (recentIrrigations[i] && recentIrrigations[i].amount) {
      totalWater += recentIrrigations[i].amount;
    }
  }
  if (totalWater > 2000) {
    return 0.7;
  }

  return 1.0;
}

/**
 * 计算灌溉持续时间 (基于水量)
 * @param {number} waterAmount - 水量 (ml)
 * @param {number} flowRate - 流速 (ml/s)，默认20ml/s
 * @returns {number} - 持续时间 (秒)
 */
function calculateDuration(waterAmount, flowRate = 20) {
  return Math.ceil(waterAmount / flowRate);
}

/**
 * 评估灌溉建议（改用空气湿度）
 * @param {Object} sensorData - 传感器数据
 * @returns {Object} - 灌溉建议
 */
function evaluateIrrigationNeed(sensorData) {
  const { temperature, humidity, light } = sensorData;
  const recommendations = [];
  let needIrrigation = false;

  // 空气湿度检查（替代土壤湿度）
  if (humidity !== null && humidity !== undefined) {
    if (humidity < 40) {
      recommendations.push('空气干燥，强烈建议灌溉');
      needIrrigation = true;
    } else if (humidity < 50) {
      recommendations.push('空气略干，建议灌溉');
      needIrrigation = true;
    } else if (humidity > 70) {
      recommendations.push('空气湿润，暂不需要灌溉');
    }
  }

  // 温度检查
  if (temperature !== null && temperature !== undefined) {
    if (temperature > 35) {
      recommendations.push('温度过高，注意增加灌溉量');
    } else if (temperature < 10) {
      recommendations.push('温度较低，可适当减少灌溉量');
    }
  }

  // 光照检查
  if (light !== null && light !== undefined) {
    if (light > 50000) {
      recommendations.push('光照强烈，水分蒸发快，建议增加灌溉');
    }
  }

  return {
    needIrrigation,
    recommendations,
    urgency: needIrrigation ? (humidity < 40 ? 'high' : 'medium') : 'low'
  };
}

module.exports = {
  calculateWaterAmount,
  calculateDuration,
  evaluateIrrigationNeed,
  getSeason,
  calcTemperatureFactor,
  calcHumidityFactor,
  calcLightFactor,
  calcHistoryFactor,
  DataSmoother,
  irrigationSmoother
};
