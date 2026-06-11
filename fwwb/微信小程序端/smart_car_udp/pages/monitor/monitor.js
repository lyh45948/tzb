// pages/monitor/monitor.js
// Smart Agriculture Monitor Page - 通过后端连接接收环境监测数据

const app = getApp();
const udpBackendManager = require('../../utils/udp-backend-manager');

Page({
  data: {
    // Connection status (后端连接状态)
    connectionStatus: {
      connected: false,
      message: '未连接后端'
    },

    // Demo mode
    isDemoMode: false,

    // Current sensor data
    sensorData: {
      temperature: 25.0,
      humidity: 60.0,
      lightIntensity: 800,
      co2: 450
    },

    // Time range selection
    timeRange: '1h', // '1h', '6h', '24h'
    timeRangeOptions: ['1h', '6h', '24h'],

    // Chart labels (dynamic range)
    chartLabels: {
      temp: { max: 35, min: 15 },
      humi: { max: 100, min: 0 }
    },

    // Alert history
    alerts: [],

    // Device controls
    controls: {
      irrigation: false,
      ventilation: false,
      growLight: false,
      alertEnabled: true
    },

    // Thresholds for alerts
    thresholds: {
      tempHigh: 35,
      tempLow: 10,
      humiHigh: 85,
      humiLow: 30
    },

    // Gauge colors
    tempColor: '#07c160',
    humiColor: '#1989fa',
    lightColor: '#ff9d00',
    co2Color: '#7232dd'
  },

  // History data for chart
  dataHistory: [],
  canvas: null,
  ctx: null,
  demoTimer: null,

  onLoad: function() {
    // Initialize backend connection listeners
    this.initBackendListeners();
    this.updateConnectionStatus();
  },

  onReady: function() {
    this.initChart();

    // Read global demo mode state
    const appInstance = getApp();
    const isDemoMode = appInstance.getDemoMode ? appInstance.getDemoMode() : false;
    this.setData({ isDemoMode });

    // Load demo data if in demo mode
    if (isDemoMode) {
      this.loadDemoData();
      this.startDemoTimer();
    }
  },

  onShow: function() {
    // Check demo mode status
    const appInstance = getApp();
    const isDemoMode = appInstance.getDemoMode ? appInstance.getDemoMode() : false;
    if (this.data.isDemoMode !== isDemoMode) {
      this.setData({ isDemoMode });
      if (isDemoMode) {
        this.loadDemoData();
        this.startDemoTimer();
      } else {
        this.stopDemoTimer();
      }
    }
    this.updateConnectionStatus();
  },

  onUnload: function() {
    this.stopDemoTimer();
    this.cleanupBackendListeners();
  },

  // Initialize backend message and connection listeners
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
  // Data format: { carStatus, carMode, L_spd, R_spd, carPower, distance, env: {temp, humi, lux, co2, ...} }
  handleRealtimeData(data) {
    if (!data.env) return;

    const env = data.env;
    const temperature = env.temp !== undefined ? Number(env.temp) : this.data.sensorData.temperature;
    const humidity = env.humi !== undefined ? Number(env.humi) : this.data.sensorData.humidity;
    const lightIntensity = env.lux !== undefined ? Number(env.lux) : this.data.sensorData.lightIntensity;
    const co2 = env.co2 !== undefined ? Number(env.co2) : this.data.sensorData.co2;

    // Update current data
    this.setData({
      'sensorData.temperature': temperature,
      'sensorData.humidity': humidity,
      'sensorData.lightIntensity': lightIntensity,
      'sensorData.co2': co2
    });

    // Add to history
    this.dataHistory.push({
      timestamp: Date.now(),
      temperature,
      humidity,
      lightIntensity,
      co2
    });

    // Limit history length (keep 24 hours of data at 2-second intervals = 43200 points max)
    if (this.dataHistory.length > 43200) {
      this.dataHistory = this.dataHistory.slice(-10000);
    }

    // Update chart
    this.updateChart();

    // Check alerts
    this.checkAlerts(temperature, humidity);

    // Update global sensor data
    if (app && app.updateSensorData) {
      app.updateSensorData({
        temperature: temperature,
        humidity: humidity,
        light: lightIntensity,
        co2: co2
      });
    }
  },

  // Initialize chart
  initChart: function() {
    const query = wx.createSelectorQuery();
    query.select('#trendChart')
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

        // Initial chart draw
        if (this.dataHistory.length > 0) {
          this.updateChart();
        }
      });
  },

  // Update chart with history data
  updateChart: function() {
    if (!this.ctx || this.dataHistory.length < 2) return;

    const ctx = this.ctx;
    const width = this.canvas.width / wx.getSystemInfoSync().pixelRatio;
    const height = this.canvas.height / wx.getSystemInfoSync().pixelRatio;

    ctx.clearRect(0, 0, width, height);

    // Filter data based on time range
    const now = Date.now();
    let timeWindow;
    switch (this.data.timeRange) {
      case '1h': timeWindow = 60 * 60 * 1000; break;
      case '6h': timeWindow = 6 * 60 * 60 * 1000; break;
      case '24h': timeWindow = 24 * 60 * 60 * 1000; break;
      default: timeWindow = 60 * 60 * 1000;
    }

    const filteredData = this.dataHistory.filter(d => now - d.timestamp <= timeWindow);
    if (filteredData.length < 2) return;

    // Calculate dynamic range
    const tempValues = filteredData.map(d => d.temperature);
    const humiValues = filteredData.map(d => d.humidity);

    const getRange = (values, buffer = 5, minRange = 10) => {
      let max = Math.max(...values);
      let min = Math.min(...values);
      if (!isFinite(max) || !isFinite(min)) return { max: 100, min: 0 };
      if (max - min < minRange) {
        const center = (max + min) / 2;
        max = center + minRange / 2;
        min = center - minRange / 2;
      } else {
        const diff = max - min;
        max += diff * 0.1;
        min -= diff * 0.1;
      }
      return { max: Math.ceil(max), min: Math.floor(min) };
    };

    const tRange = getRange(tempValues, 2, 8);
    const hRange = getRange(humiValues, 5, 20);

    // Update labels if changed significantly
    if (Math.abs(this.data.chartLabels.temp.max - tRange.max) > 1 ||
        Math.abs(this.data.chartLabels.humi.max - hRange.max) > 2) {
      this.setData({
        'chartLabels.temp': tRange,
        'chartLabels.humi': hRange
      });
    }

    // Draw grid
    ctx.strokeStyle = '#e8f5e9';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = (height / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Draw lines function
    const drawLine = (dataKey, color, range) => {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';

      const { max, min } = range;
      const span = (max - min) || 1;

      filteredData.forEach((item, index) => {
        const x = (index / (filteredData.length - 1)) * width;
        const val = Number(item[dataKey]) || 0;
        const y = height - ((val - min) / span) * height * 0.85 - height * 0.075;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    };

    // Draw temperature (green) and humidity (blue)
    drawLine('temperature', '#07c160', tRange);
    drawLine('humidity', '#1989fa', hRange);
  },

  // Time range change handler
  onTimeRangeChange: function(e) {
    const range = e.currentTarget.dataset.range;
    this.setData({ timeRange: range });
    this.updateChart();
  },

  // Send command through backend
  sendCommand: function(msg) {
    const status = udpBackendManager.getConnectionStatus();
    if (!status.connected || !status.carConnected) {
      wx.showToast({ title: '请先连接后端和小车', icon: 'none' });
      return;
    }
    udpBackendManager.sendControl(msg);
  },

  // Control handlers
  onIrrigationChange: function(e) {
    const status = e.detail ? 1 : 0;
    this.setData({ 'controls.irrigation': e.detail });
    this.sendCommand({ irrigation: status });
  },

  onVentilationChange: function(e) {
    const status = e.detail ? 1 : 0;
    this.setData({ 'controls.ventilation': e.detail });
    this.sendCommand({ ventilation: status });
  },

  onGrowLightChange: function(e) {
    const status = e.detail ? 1 : 0;
    this.setData({ 'controls.growLight': e.detail });
    this.sendCommand({ growLight: status });
  },

  onAlertToggle: function(e) {
    this.setData({ 'controls.alertEnabled': e.detail });
  },

  // Clear alerts
  onClearAlerts: function() {
    this.setData({ alerts: [] });
    wx.showToast({ title: 'Alerts cleared', icon: 'success' });
  },

  // Check and generate alerts
  checkAlerts: function(temp, humi) {
    const { thresholds, alerts } = this.data;
    const newAlerts = [];

    if (temp > thresholds.tempHigh) {
      newAlerts.push({
        type: 'warning',
        icon: 'warning-o',
        message: `High temperature: ${temp}C exceeds ${thresholds.tempHigh}C`,
        time: this.formatTime(new Date())
      });
    }

    if (temp < thresholds.tempLow) {
      newAlerts.push({
        type: 'warning',
        icon: 'info-o',
        message: `Low temperature: ${temp}C below ${thresholds.tempLow}C`,
        time: this.formatTime(new Date())
      });
    }

    if (humi > thresholds.humiHigh) {
      newAlerts.push({
        type: 'warning',
        icon: 'warning-o',
        message: `High humidity: ${humi}% exceeds ${thresholds.humiHigh}%`,
        time: this.formatTime(new Date())
      });
    }

    if (humi < thresholds.humiLow) {
      newAlerts.push({
        type: 'info',
        icon: 'info-o',
        message: `Low humidity: ${humi}% below ${thresholds.humiLow}%`,
        time: this.formatTime(new Date())
      });
    }

    // Add new alerts to history (keep last 20)
    if (newAlerts.length > 0 && this.data.controls.alertEnabled) {
      const updatedAlerts = [...newAlerts, ...alerts].slice(0, 20);
      this.setData({ alerts: updatedAlerts });
    }
  },

  // Format time
  formatTime: function(date) {
    const h = date.getHours().toString().padStart(2, '0');
    const m = date.getMinutes().toString().padStart(2, '0');
    const s = date.getSeconds().toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
  },

  // Demo mode functions
  loadDemoData: function() {
    console.log('[Monitor] Loading demo data');

    // Initial demo data
    this.setData({
      sensorData: {
        temperature: 26.5,
        humidity: 65.0,
        lightIntensity: 850,
        co2: 450
      },
      controls: {
        irrigation: false,
        ventilation: true,
        growLight: false,
        alertEnabled: true
      }
    });

    // Generate demo history
    this.generateDemoHistory();
  },

  generateDemoHistory: function() {
    this.dataHistory = [];
    const now = Date.now();

    // Generate 180 data points (6 minutes at 2-second intervals for demo)
    for (let i = 180; i >= 0; i--) {
      const progress = i / 180;
      const tempBase = 25 + Math.sin(progress * Math.PI * 6) * 3;
      const tempNoise = (Math.random() - 0.5) * 0.5;
      const temperature = Math.round((tempBase + tempNoise) * 10) / 10;

      const humiBase = 60 + Math.cos(progress * Math.PI * 4) * 10;
      const humiNoise = (Math.random() - 0.5) * 2;
      const humidity = Math.round((humiBase + humiNoise) * 10) / 10;

      const lightBase = 800 + Math.sin(progress * Math.PI * 2) * 200;
      const lightNoise = (Math.random() - 0.5) * 50;
      const lightIntensity = Math.round(lightBase + lightNoise);

      const co2Base = 450 + Math.sin(progress * Math.PI * 3) * 50;
      const co2Noise = (Math.random() - 0.5) * 20;
      const co2 = Math.round(co2Base + co2Noise);

      this.dataHistory.push({
        timestamp: now - i * 2000,
        temperature,
        humidity,
        lightIntensity,
        co2
      });
    }

    // Add some demo alerts
    this.setData({
      alerts: [
        { type: 'info', icon: 'info-o', message: 'System started in demo mode', time: this.formatTime(new Date(now - 300000)) },
        { type: 'warning', icon: 'warning-o', message: 'Humidity slightly low', time: this.formatTime(new Date(now - 120000)) }
      ]
    });

    // Update chart after a delay
    setTimeout(() => {
      this.updateChart();
    }, 500);

    console.log('[Monitor] Generated demo history, points:', this.dataHistory.length);
  },

  startDemoTimer: function() {
    if (this.demoTimer) return;

    this.demoTimer = setInterval(() => {
      // Generate new data point
      const progress = this.dataHistory.length / 500;
      const tempBase = 25 + Math.sin(progress * Math.PI * 6) * 3;
      const tempNoise = (Math.random() - 0.5) * 0.5;
      const temperature = Math.round((tempBase + tempNoise) * 10) / 10;

      const humiBase = 60 + Math.cos(progress * Math.PI * 4) * 10;
      const humiNoise = (Math.random() - 0.5) * 2;
      const humidity = Math.round((humiBase + humiNoise) * 10) / 10;

      const lightBase = 800 + Math.sin(progress * Math.PI * 2) * 200;
      const lightNoise = (Math.random() - 0.5) * 50;
      const lightIntensity = Math.round(lightBase + lightNoise);

      const co2Base = 450 + Math.sin(progress * Math.PI * 3) * 50;
      const co2Noise = (Math.random() - 0.5) * 20;
      const co2 = Math.round(co2Base + co2Noise);

      // Update current data
      this.setData({
        'sensorData.temperature': temperature,
        'sensorData.humidity': humidity,
        'sensorData.lightIntensity': lightIntensity,
        'sensorData.co2': co2
      });

      // Add to history
      this.dataHistory.push({
        timestamp: Date.now(),
        temperature,
        humidity,
        lightIntensity,
        co2
      });

      // Limit history
      if (this.dataHistory.length > 1000) {
        this.dataHistory.shift();
      }

      // Update chart
      this.updateChart();

      // Check for alerts
      this.checkAlerts(temperature, humidity);

    }, 2000);

    console.log('[Monitor] Demo timer started');
  },

  stopDemoTimer: function() {
    if (this.demoTimer) {
      clearInterval(this.demoTimer);
      this.demoTimer = null;
      console.log('[Monitor] Demo timer stopped');
    }
  },

  // Get gauge color based on value
  getTempColor: function(temp) {
    if (temp > 35 || temp < 10) return '#ee0a24';
    if (temp > 30 || temp < 15) return '#ff976a';
    return '#07c160';
  },

  getHumiColor: function(humi) {
    if (humi > 85 || humi < 30) return '#ee0a24';
    if (humi > 75 || humi < 40) return '#ff976a';
    return '#1989fa';
  },

  getSoilColor: function(soil) {
    if (soil < 25) return '#ee0a24';
    if (soil < 35) return '#ff976a';
    return '#8B4513';
  }
});
