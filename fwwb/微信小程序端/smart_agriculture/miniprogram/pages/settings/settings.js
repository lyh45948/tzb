// pages/settings/settings.js
const configManager = require('../../utils/config-manager');

Page({
  data: {
    thresholds: {
      temperature: { min: 15, max: 35 },
      humidity: { min: 40, max: 80 },
      light: { min: 500, max: 5000 },
      soilMoisture: { min: 30, max: 70 },
      co2: { min: 400, max: 1000 }
    },
    demoMode: false,
    autoControl: false
  },

  onLoad() {
    this.loadConfig();
  },

  onShow() {
    this.loadConfig();
  },

  // 加载配置
  loadConfig() {
    const config = configManager.getConfig();
    const thresholds = configManager.getThresholds();

    this.setData({
      demoMode: config.demoMode,
      autoControl: config.autoControl,
      thresholds: {
        temperature: thresholds.temperature,
        humidity: thresholds.humidity,
        light: thresholds.light,
        soilMoisture: thresholds.soilMoisture,
        co2: thresholds.co2
      }
    });
  },

  // 保存配置
  saveConfig() {
    configManager.saveConfig({
      demoMode: this.data.demoMode,
      autoControl: this.data.autoControl
    });

    configManager.saveThresholds(this.data.thresholds);

    wx.showToast({
      title: '保存成功',
      icon: 'success'
    });
  },

  // 重置配置
  resetConfig() {
    wx.showModal({
      title: '确认重置',
      content: '确定要重置所有配置到默认值吗？',
      success: (res) => {
        if (res.confirm) {
          configManager.resetConfig();
          this.loadConfig();
          wx.showToast({
            title: '已重置',
            icon: 'success'
          });
        }
      }
    });
  },

  // 温度阈值变化
  onTempMinChange(e) {
    this.setData({
      'thresholds.temperature.min': e.detail
    });
  },
  onTempMaxChange(e) {
    this.setData({
      'thresholds.temperature.max': e.detail
    });
  },

  // 湿度阈值变化
  onHumidityMinChange(e) {
    this.setData({
      'thresholds.humidity.min': e.detail
    });
  },
  onHumidityMaxChange(e) {
    this.setData({
      'thresholds.humidity.max': e.detail
    });
  },

  // 光照阈值变化
  onLightMinChange(e) {
    this.setData({
      'thresholds.light.min': e.detail
    });
  },
  onLightMaxChange(e) {
    this.setData({
      'thresholds.light.max': e.detail
    });
  },

  // 土壤湿度阈值变化
  onSoilMinChange(e) {
    this.setData({
      'thresholds.soilMoisture.min': e.detail
    });
  },
  onSoilMaxChange(e) {
    this.setData({
      'thresholds.soilMoisture.max': e.detail
    });
  },

  // CO2阈值变化
  onCo2MinChange(e) {
    this.setData({
      'thresholds.co2.min': e.detail
    });
  },
  onCo2MaxChange(e) {
    this.setData({
      'thresholds.co2.max': e.detail
    });
  },

  // 切换演示模式
  onDemoModeChange(e) {
    this.setData({
      demoMode: e.detail
    });
  },

  // 切换自动控制
  onAutoControlChange(e) {
    this.setData({
      autoControl: e.detail
    });
  },

  // 返回上一页
  goBack() {
    wx.navigateBack();
  }
});
