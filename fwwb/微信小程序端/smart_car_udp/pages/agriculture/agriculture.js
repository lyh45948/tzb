// pages/agriculture/agriculture.js
// 农业监测页面 - 融合 smart_agriculture 功能
const app = getApp();
const configManager = require('../../utils/config-manager');

Page({
  data: {
    // 传感器数据
    sensorData: {
      temperature: 25,
      humidity: 60,
      light: 1200,
      co2: 600
    },
    // 设备状态
    deviceStatus: {
      pump: false,
      valve: false,
      led: false,
      fan: false
    },
    // 告警列表
    alerts: [],
    // 历史数据
    historyData: [],
    // 时间范围
    timeRange: '1h',
    // 演示模式
    isDemoMode: false,
    // 自动控制模式
    autoControl: false
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
    
    // 读取演示模式状态
    this.setData({
      isDemoMode: app.getDemoMode(),
      autoControl: app.globalData.autoControl
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
    const globalData = app.globalData;
    this.setData({
      sensorData: { ...globalData.sensorData },
      deviceStatus: { ...globalData.deviceStatus },
      alerts: [...globalData.alerts],
      historyData: globalData.historyData.slice(-30)
    });
  },

  // 切换演示模式
  onDemoModeChange(e) {
    const enabled = e.detail;
    app.setDemoMode(enabled);
    this.setData({ isDemoMode: enabled });
  },

  // 切换自动控制
  onAutoControlChange(e) {
    const enabled = e.detail;
    app.toggleAutoControl(enabled);
    this.setData({ autoControl: enabled });
  },

  // 控制水泵
  onPumpChange(e) {
    const status = e.detail;
    app.sendControl('pump', status);
  },

  // 控制电磁阀
  onValveChange(e) {
    const status = e.detail;
    app.sendControl('valve', status);
  },

  // 控制 LED 灯
  onLedChange(e) {
    const status = e.detail;
    app.sendControl('led', status);
  },

  // 控制风扇
  onFanChange(e) {
    const status = e.detail;
    app.sendControl('fan', status);
  },

  // 获取传感器状态颜色
  getSensorColor(type, value) {
    const thresholds = configManager.getThresholds();
    const threshold = thresholds[type];
    
    if (!threshold) return '#4CAF50';
    
    if (value < threshold.min || value > threshold.max) {
      return '#F44336';
    }
    return '#4CAF50';
  },

  // 获取告警级别样式
  getAlertStyle(level) {
    return level === 'high' ? 'high-alert' : 'low-alert';
  },

  // 跳转设置页面
  goToSettings() {
    wx.navigateTo({
      url: '../settings/settings'
    });
  }
});