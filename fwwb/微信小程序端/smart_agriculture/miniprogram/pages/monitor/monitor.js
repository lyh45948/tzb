// pages/monitor/monitor.js
const app = getApp();

Page({
  data: {
    sensorData: {
      temperature: 25,
      humidity: 60,
      light: 1200,
      soilMoisture: 55,
      co2: 600
    },
    historyData: [],
    timeRange: '1h', // 1h, 6h, 24h
    alerts: []
  },

  onLoad() {
    this.loadData();
  },

  onShow() {
    this.loadData();
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
      sensorData: app.globalData.sensorData,
      historyData: app.globalData.historyData.slice(-30), // 最近30条
      alerts: app.globalData.alerts
    });
  },

  // 切换时间范围
  onTimeRangeChange(e) {
    this.setData({
      timeRange: e.currentTarget.dataset.range
    });
  },

  // 获取图表数据
  getChartData() {
    const { historyData, timeRange } = this.data;
    let filteredData = historyData;

    // 根据时间范围过滤
    const now = new Date();
    let cutoffTime;

    switch (timeRange) {
      case '1h':
        cutoffTime = new Date(now - 60 * 60 * 1000);
        break;
      case '6h':
        cutoffTime = new Date(now - 6 * 60 * 60 * 1000);
        break;
      case '24h':
        cutoffTime = new Date(now - 24 * 60 * 60 * 1000);
        break;
      default:
        cutoffTime = new Date(now - 60 * 60 * 1000);
    }

    return filteredData;
  }
});
