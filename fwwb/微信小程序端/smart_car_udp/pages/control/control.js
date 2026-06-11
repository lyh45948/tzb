// pages/control/control.js
// Smart Car Control Page - 通过后端连接控制小车

const app = getApp();
const configManager = require('../../utils/config-manager');
const udpBackendManager = require('../../utils/udp-backend-manager');
const errorHandler = require('../../utils/error-handler');
const g_value = require('../../utils/g_value');

Page({
  data: {
    // Connection status (后端连接状态)
    connectionStatus: {
      connected: false,
      message: '未连接后端'
    },

    // Demo mode
    isDemoMode: false,

    // Car status values
    Value: {
      power: 100,
      mode: 'manual',
      distance: 999,
      speed: 0,
      gears: 1
    },

    // Joystick position
    handleLeft: 50,
    handleTop: 50,
    joystickCenterX: 0,
    joystickCenterY: 0,
    joystickRadius: 0
  },

  // Data history for chart
  dataHistory: [],
  ctx: null,

  onLoad: function() {
    // Initialize backend connection listeners
    this.initBackendListeners();
    this.updateConnectionStatus();
  },

  onReady: function() {
    this.initJoystick();
    this.initChart();
  },

  onShow: function() {
    this.setData({
      isDemoMode: app.getDemoMode ? app.getDemoMode() : false
    });

    // Set data update callback
    if (app.setDataUpdateCallback) {
      app.setDataUpdateCallback(() => {
        this.updateFromGlobal();
      });
    }

    this.updateFromGlobal();
    this.updateConnectionStatus();
  },

  onUnload: function() {
    // Clean up backend listeners
    this.cleanupBackendListeners();
  },

  // Initialize backend message and connection listeners
  initBackendListeners() {
    // Message callback: receive realtime data from backend
    this._onMessage = (data) => {
      if (data) {
        this.handleReceivedData(data);
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

  // Update from global data
  updateFromGlobal: function() {
    if (g_value && g_value.Value) {
      this.setData({
        Value: { ...this.data.Value, ...g_value.Value }
      });
    }
  },

  // Handle received data from backend (realtime data format)
  handleReceivedData: function(data) {
    // data format: { carStatus, carMode, L_spd, R_spd, carPower, distance, env: {...} }
    if (data.carPower !== undefined) {
      // carPower is in mV, convert to approximate percentage
      const voltage = data.carPower / 1000; // V
      const maxVoltage = 12.6; // 3S LiPo max
      const minVoltage = 10.5; // 3S LiPo min
      let percent = Math.round(((voltage - minVoltage) / (maxVoltage - minVoltage)) * 100);
      percent = Math.max(0, Math.min(100, percent));
      this.setData({ 'Value.power': percent });
      g_value.Value.power = percent;
    }
    if (data.distance !== undefined) {
      this.setData({ 'Value.distance': data.distance });
      g_value.Value.distance = data.distance;
    }
    if (data.L_spd !== undefined && data.R_spd !== undefined) {
      const avgSpeed = Math.round((Math.abs(data.L_spd) + Math.abs(data.R_spd)) / 2);
      this.setData({ 'Value.speed': avgSpeed });
      g_value.Value.speed = avgSpeed;
      this.addToHistory(avgSpeed);
    }
    if (data.carMode !== undefined) {
      this.setData({ 'Value.mode': data.carMode });
      g_value.Value.mode = data.carMode;
    }
  },

  // Send command through backend
  sendCommand: function(cmd) {
    const status = udpBackendManager.getConnectionStatus();
    if (!status.connected || !status.carConnected) {
      wx.showToast({ title: '请先连接后端和小车', icon: 'none' });
      return;
    }

    udpBackendManager.sendControl(cmd);
  },

  // Power switch
  onbutton_startCar: function(e) {
    const isOn = e.detail.value;
    this.sendCommand({ carStatus: isOn ? 'on' : 'off' });
  },

  // Mode toggles
  toggleAvoid: function() {
    const newMode = this.data.Value.mode === 'avoid' ? 'manual' : 'avoid';
    this.setData({ 'Value.mode': newMode });
    this.sendCommand({ carMode: newMode });
  },

  toggleLine: function() {
    const newMode = this.data.Value.mode === 'line' ? 'manual' : 'line';
    this.setData({ 'Value.mode': newMode });
    this.sendCommand({ carMode: newMode });
  },

  // Speed gear control
  onSpeedBtnTap: function(e) {
    const gear = parseInt(e.currentTarget.dataset.gear);
    const speeds = ['low', 'middle', 'high'];
    this.setData({ 'Value.gears': gear });
    this.sendCommand({ carSpeed: speeds[gear] });
  },

  // Rotation buttons
  onbutton_trunLeft_start: function() {
    this.sendCommand({ carStatus: 'left' });
  },

  onbutton_trunLeft_end: function() {
    this.sendCommand({ carStatus: 'stop' });
  },

  onbutton_trunRight_start: function() {
    this.sendCommand({ carStatus: 'right' });
  },

  onbutton_trunRight_end: function() {
    this.sendCommand({ carStatus: 'stop' });
  },

  // Joystick initialization
  initJoystick: function() {
    const query = wx.createSelectorQuery();
    query.select('.joystick-container-mini').boundingClientRect((rect) => {
      if (rect) {
        const radius = rect.width / 2 - 15;
        this.setData({
          joystickCenterX: rect.width / 2,
          joystickCenterY: rect.height / 2,
          joystickRadius: radius,
          handleLeft: rect.width / 2 - 15,
          handleTop: rect.height / 2 - 15
        });
      }
    }).exec();
  },

  // Joystick touch handlers
  onTouchStart: function(e) {
    this.handleJoystickMove(e.touches[0]);
  },

  onTouchMove: function(e) {
    this.handleJoystickMove(e.touches[0]);
  },

  onTouchEnd: function(e) {
    // Reset to center
    this.setData({
      handleLeft: this.data.joystickCenterX - 15,
      handleTop: this.data.joystickCenterY - 15
    });

    // Send stop command
    this.sendCommand({ carStatus: 'stop', joyX: 0, joyY: 0 });
  },

  handleJoystickMove: function(touch) {
    const { joystickCenterX, joystickCenterY, joystickRadius } = this.data;
    let dx = touch.clientX - (this.data.joystickCenterX || 0);
    let dy = touch.clientY - (this.data.joystickCenterY || 0);

    // Clamp to radius
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance > joystickRadius) {
      dx = (dx / distance) * joystickRadius;
      dy = (dy / distance) * joystickRadius;
    }

    // Update handle position
    this.setData({
      handleLeft: joystickCenterX + dx - 15,
      handleTop: joystickCenterY + dy - 15
    });

    // Calculate joystick values (-100 to 100)
    const joyX = Math.round((dx / joystickRadius) * 100);
    const joyY = Math.round((dy / joystickRadius) * 100);

    // Determine direction
    let carStatus = 'stop';
    if (Math.abs(joyY) > Math.abs(joyX)) {
      carStatus = joyY < 0 ? 'run' : 'back';
    } else if (Math.abs(joyX) > 10) {
      carStatus = joyX < 0 ? 'left' : 'right';
    }

    // Throttled send
    this.throttledSend({ carStatus, joyX, joyY });
  },

  // Throttle for joystick
  lastSendTime: 0,
  throttledSend: function(cmd) {
    const now = Date.now();
    if (now - this.lastSendTime > 50) {
      this.sendCommand(cmd);
      this.lastSendTime = now;
    }
  },

  // Chart initialization
  initChart: function() {
    const query = wx.createSelectorQuery();
    query.select('#speedChart')
      .fields({ node: true, size: true })
      .exec((res) => {
        if (res[0]) {
          const canvas = res[0].node;
          this.ctx = canvas.getContext('2d');
          canvas.width = res[0].width * 2;
          canvas.height = res[0].height * 2;
          this.drawChart();
        }
      });
  },

  // Add to history
  addToHistory: function(speed) {
    this.dataHistory.push({
      time: Date.now(),
      value: speed
    });

    // Keep last 60 points
    if (this.dataHistory.length > 60) {
      this.dataHistory.shift();
    }

    this.drawChart();
  },

  // Draw chart
  drawChart: function() {
    if (!this.ctx || this.dataHistory.length < 2) return;

    const ctx = this.ctx;
    const w = 300;
    const h = 80;
    const history = this.dataHistory;

    // Clear
    ctx.fillStyle = '#f8f8f8';
    ctx.fillRect(0, 0, w, h);

    // Get min/max
    const values = history.map(d => d.value);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values, minVal + 1);
    const range = maxVal - minVal || 1;

    // Draw line
    ctx.beginPath();
    ctx.strokeStyle = '#07c160';
    ctx.lineWidth = 2;

    history.forEach((point, i) => {
      const x = (i / (history.length - 1)) * (w - 20) + 10;
      const y = h - 10 - ((point.value - minVal) / range) * (h - 20);

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();
  }
});
