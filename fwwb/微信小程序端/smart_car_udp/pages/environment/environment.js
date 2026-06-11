// pages/environment/environment.js
// 环境监控页面 - 通过后端连接接收环境监测数据

const app = getApp();
const udpBackendManager = require('../../utils/udp-backend-manager');

Page({
  data: {
    // Connection status (后端连接状态)
    connectionStatus: {
      connected: false,
      message: '未连接后端'
    },
    env: {
      temp: 0,
      humi: 0,
      lux: 0,
      fan: false,
      led: false
    },
    chartLabels: {
      temp: { max: 50, min: 0 },
      humi: { max: 100, min: 0 }
    },

    // 节流相关
    lastUpdateTime: 0,
    updateInterval: 3000  // 3秒更新一次
  },

  envHistory: [], // 用于存储历史数据绘制曲线
  canvas: null,
  ctx: null,

  onLoad: function() {
    // Initialize backend connection listeners
    this.initBackendListeners();
    this.updateConnectionStatus();
  },

  onReady: function() {
    // DOM 已准备好，现在初始化图表
    this.initChart();

    // 读取全局演示模式状态
    const appInstance = getApp();
    const isDemoMode = appInstance.getDemoMode ? appInstance.getDemoMode() : false;
    this.setData({ isDemoMode });

    // 如果演示模式开启，加载演示数据
    if (isDemoMode) {
      this.loadDemoData();
    }
  },

  onShow: function() {
    // 每次显示时检查演示模式状态
    const appInstance = getApp();
    const isDemoMode = appInstance.getDemoMode ? appInstance.getDemoMode() : false;
    if (this.data.isDemoMode !== isDemoMode) {
      this.setData({ isDemoMode });
      if (isDemoMode) {
        this.startDemoTimer();
      } else {
        this.stopDemoTimer();
      }
    }
    this.updateConnectionStatus();
  },

  /**
   * 监听全局演示模式切换（通过自定义事件）
   */
  onDemoModeChanged(e) {
    const isDemoMode = e.detail;
    this.setData({ isDemoMode });

    if (isDemoMode) {
      this.loadDemoData();
      this.startDemoTimer();
    } else {
      this.stopDemoTimer();
    }
  },

  /**
   * 页面卸载
   */
  onUnload: function() {
    this.stopDemoTimer();
    this.cleanupBackendListeners();
  },

  // Initialize backend connection listeners
  initBackendListeners() {
    // Message callback: receive realtime data from backend
    this._onMessage = (data) => {
      if (data) {
        this.handleRealtimeData(data);
      }
    };
    udpBackendManager.onMessage(this._onMessage);

    // Connection status callback
    this._onConnectionChange = (connected, message, data) => {
      this.updateConnectionStatus();
    };
    udpBackendManager.onConnectionChange(this._onConnectionChange);
  },

  cleanupBackendListeners() {
    if (this._onMessage) {
      udpBackendManager.offMessage(this._onMessage);
    }
    if (this._onConnectionChange) {
      udpBackendManager.offConnectionChange(this._onConnectionChange);
    }
  },

  // Update connection status from backend manager
  updateConnectionStatus() {
    const status = udpBackendManager.getConnectionStatus();
    const connected = status.connected && status.carConnected;
    const message = status.carConnected
      ? '已连接小车(经后端)'
      : (status.connected ? '已连接后端' : '未连接后端');
    this.setData({
      connectionStatus: { connected, message }
    });
  },

  // Handle realtime data from backend
  // Data format: { carStatus, carMode, L_spd, R_spd, carPower, distance, env: {temp, humi, lux, fan, led, ...} }
  handleRealtimeData(data) {
    if (!data.env) return;

    // 节流：检查是否达到更新间隔
    const now = Date.now();
    if (now - this.data.lastUpdateTime < this.data.updateInterval) {
      return;  // 未达到更新间隔，跳过
    }

    const env = data.env;
    // 确保数值类型，并提供默认值
    const temp = Number(env.temp) || 0;
    const humi = Number(env.humi) || 0;
    const lux = Number(env.lux) || 0;

    this.setData({
      lastUpdateTime: now,
      'env.temp': temp,
      'env.humi': humi,
      'env.lux': lux,
      'env.fan': env.fan === 1,
      'env.led': env.led === 1
    });

    // 只有当有历史数据或者收到有效数据时才更新图表
    this.updateChart({
      temp: temp,
      humi: humi
    });

    // 更新全局传感器数据
    if (app && app.updateSensorData) {
      app.updateSensorData({
        temperature: temp,
        humidity: humi,
        light: lux,
        co2: env.co2 || 0
      });
    }
  },

  // 初始化环境图表
  initChart: function() {
    const query = wx.createSelectorQuery();
    query.select('#envChart')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (!res[0]) return;
        const canvas = res[0].node;
        const ctx = canvas.getContext('2d');
        const dpr = wx.getSystemInfoSync().pixelRatio;
        canvas.width = res[0].width * dpr;
        canvas.height = res[0].height * dpr;
        ctx.scale(dpr, dpr);
        this.canvas = canvas;
        this.ctx = ctx;
      });
  },

  // 绘制多维环境曲线
  updateChart: function(newData) {
    if (!this.ctx) return;

    // 限制历史数据长度
    this.envHistory.push(newData);
    if (this.envHistory.length > 150) this.envHistory.shift();

    const ctx = this.ctx;
    const width = this.canvas.width / wx.getSystemInfoSync().pixelRatio;
    const height = this.canvas.height / wx.getSystemInfoSync().pixelRatio;

    ctx.clearRect(0, 0, width, height);

    if (this.envHistory.length < 2) return;

    // 计算动态量程
    let tempValues = this.envHistory.map(d => Number(d.temp) || 0);
    let humiValues = this.envHistory.map(d => Number(d.humi) || 0);

    const getRange = (values, buffer = 2, minRange = 5) => {
      let max = Math.max(...values);
      let min = Math.min(...values);

      if (!isFinite(max) || !isFinite(min)) return { max: 100, min: 0 };

      if (max - min < minRange) {
        let center = (max + min) / 2;
        max = center + minRange / 2;
        min = center - minRange / 2;
      } else {
        const diff = max - min;
        max += diff * 0.1;
        min -= diff * 0.1;
      }
      return { max: Math.ceil(max), min: Math.floor(min) };
    };

    const tRange = getRange(tempValues, 2, 10);
    const hRange = getRange(humiValues, 5, 20);

    // 只有量程变化较大时才更新界面
    if (Math.abs(this.data.chartLabels.temp.max - tRange.max) > 0.5 ||
        Math.abs(this.data.chartLabels.humi.max - hRange.max) > 0.5) {
      this.setData({
        'chartLabels.temp': tRange,
        'chartLabels.humi': hRange
      });
    }

    // 1. 绘制网格背景
    ctx.strokeStyle = '#f8f8f8';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    // 2. 准备绘制曲线
    const drawLine = (dataKey, color, range) => {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';

      const { max, min } = range;
      const span = (max - min) || 1;

      this.envHistory.forEach((item, index) => {
        const x = (index / (this.envHistory.length - 1)) * width;
        const val = Number(item[dataKey]) || 0;
        const y = height - ((val - min) / span) * height * 0.8 - height * 0.1;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    };

    // 分别绘制：温度(橙)、湿度(蓝)
    drawLine('temp', '#ff9d00', tRange);
    drawLine('humi', '#1989fa', hRange);
  },

  /**
   * 启动演示定时器
   */
  startDemoTimer: function() {
    if (this.demoTimer) return;

    // 每2秒更新一次模拟数据
    this.demoTimer = setInterval(() => {
      const now = this.envHistory.length;

      // 生成新的数据点
      const progress = now / 150;
      const tempBase = 24 + Math.sin(progress * Math.PI * 4) * 2;
      const tempNoise = (Math.random() - 0.5) * 0.5;
      const temp = Math.round((tempBase + tempNoise) * 10) / 10;

      const humiBase = 60 + Math.cos(progress * Math.PI * 3) * 15;
      const humiNoise = (Math.random() - 0.5) * 2;
      const humi = Math.round((humiBase + humiNoise) * 10) / 10;

      // 更新环境数据
      this.setData({
        'env.temp': temp,
        'env.humi': humi
      });

      // 更新图表
      this.updateChart({ temp, humi });

      // 更新光照数据
      const lux = Math.round(700 + Math.random() * 300);
      this.setData({ 'env.lux': lux });

    }, 2000);

    console.log('[Environment] 演示定时器已启动');
  },

  /**
   * 停止演示定时器
   */
  stopDemoTimer: function() {
    if (this.demoTimer) {
      clearInterval(this.demoTimer);
      this.demoTimer = null;
      console.log('[Environment] 演示定时器已停止');
    }
  },

  // 加载默认演示数据
  loadDemoData: function() {
    console.log('[Environment] 加载演示数据');

    // 模拟环境数据
    const demoEnvData = {
      temp: 26.5,
      humi: 65.3,
      lux: 850
    };

    this.setData({
      env: demoEnvData
    });

    // 生成模拟历史数据用于绘制曲线
    this.generateDemoHistory();
  },

  // 生成模拟历史数据
  generateDemoHistory: function() {
    this.envHistory = [];

    // 生成150个数据点（约5分钟数据，每2秒一个点）
    for (let i = 0; i < 150; i++) {
      const progress = i / 150;

      // 模拟温度变化：从24度开始，缓慢上升到28度，再缓慢下降
      const tempBase = 24 + Math.sin(progress * Math.PI * 4) * 2;
      const tempNoise = (Math.random() - 0.5) * 0.5;
      const temp = Math.round((tempBase + tempNoise) * 10) / 10;

      // 模拟湿度变化：从60%开始，与温度相反
      const humiBase = 60 + Math.cos(progress * Math.PI * 3) * 15;
      const humiNoise = (Math.random() - 0.5) * 2;
      const humi = Math.round((humiBase + humiNoise) * 10) / 10;

      this.envHistory.push({
        temp: temp,
        humi: humi
      });
    }

    // 延迟更新图表，确保canvas已初始化
    setTimeout(() => {
      if (this.envHistory.length > 0) {
        this.updateChart({
          temp: this.envHistory[this.envHistory.length - 1].temp,
          humi: this.envHistory[this.envHistory.length - 1].humi
        });
      }
    }, 500);

    console.log('[Environment] 已生成演示数据，数据点数:', this.envHistory.length);
  }
})
