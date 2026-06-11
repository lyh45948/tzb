// pages/index/index.js
const app = getApp();

Page({
  data: {
    connected: false,
    demoMode: false,
    sensorData: {
      temperature: 25,
      humidity: 60,
      light: 1200,
      soilMoisture: 55,
      co2: 600
    },
    alerts: []
  },

  onLoad() {
    this.loadData();
  },

  onShow() {
    this.loadData();
    // 设置数据更新回调
    app.setDataUpdateCallback(() => {
      this.loadData();
    });
  },

  onHide() {
    app.setDataUpdateCallback(null);
  },

  onUnload() {
    app.setDataUpdateCallback(null);
  },

  // 加载数据
  loadData() {
    const app = getApp();
    this.setData({
      connected: app.globalData.connected,
      demoMode: app.globalData.demoMode,
      sensorData: app.globalData.sensorData,
      alerts: app.globalData.alerts
    });
  },

  // 切换演示模式
  onDemoModeChange(e) {
    const app = getApp();
    app.toggleDemoMode(e.detail);
    this.setData({
      demoMode: e.detail
    });
  },

  // 跳转设置页面
  goToSettings() {
    wx.navigateTo({
      url: '/pages/settings/settings'
    });
  },

  // 获取传感器颜色
  getSensorColor(type, value) {
    const thresholds = {
      temperature: { min: 15, max: 35 },
      humidity: { min: 40, max: 80 },
      light: { min: 500, max: 5000 },
      soilMoisture: { min: 30, max: 70 },
      co2: { min: 400, max: 1000 }
    };

    const threshold = thresholds[type];
    if (!threshold) return '#4CAF50';

    if (value < threshold.min || value > threshold.max) {
      return '#F44336';
    }
    return '#4CAF50';
  }
});
