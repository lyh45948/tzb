// pages/path_planning/path_planning.js
// 路径规划页面 - 通过后端连接控制小车

const udpBackendManager = require('../../utils/udp-backend-manager');
const errorHandler = require('../../utils/error-handler');

var drawCanvas = null;
var drawCtx = null;

// Constants
const WHEEL_BASELINE = 286; // mm (Calibrated for 2x rotation offset)
const CANVAS_SCALE = 0.5;    // 1mm = 0.5px
const CAMERA_PADDING = 50;   // Padding for dynamic viewport

Page({
  data: {
    connectionStatus: { connected: false, message: '未连接后端' },
    points: [], // Planned points (Input Canvas)
    canvasWidth: 0,
    canvasHeight: 0,
    isDemoMode: false // 是否为演示模式
  },


  onLoad: function () {
    this.initBackendListeners();
    this.initCanvas();

    // 读取全局演示模式状态
    const app = getApp();
    const isDemoMode = app.getDemoMode ? app.getDemoMode() : false;
    this.setData({ isDemoMode });

    // 如果演示模式开启，加载演示数据
    if (isDemoMode) {
      this.loadDemoData();
    }
  },

  onShow: function () {
    this.updateConnectionStatus();
  },

  /**
   * 页面初次渲染完成
   */
  onReady: function () {
    // DOM 已准备好，现在初始化 Canvas
    this.initCanvas();

    // 读取全局演示模式状态
    const app = getApp();
    const isDemoMode = app.getDemoMode ? app.getDemoMode() : false;
    this.setData({ isDemoMode });

    // 如果演示模式开启，加载演示数据
    if (isDemoMode) {
      this.loadDemoData();
    }
  },

  /**
   * 监听演示模式切换（通过自定义事件）
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

  onUnload: function () {
    // 清理演示定时器
    this.stopDemoTimer();

    // 清理后端监听
    this.cleanupBackendListeners();
  },

  // Initialize backend connection listeners
  initBackendListeners() {
    // Connection status callback
    this._onConnectionChange = (connected, message, data) => {
      this.updateConnectionStatus();
    };
    udpBackendManager.onConnectionChange(this._onConnectionChange);

    // Message callback (for future data reception if needed)
    this._onMessage = (data) => {
      if (data) {
        this.handleDeviceMessage(data);
      }
    };
    udpBackendManager.onMessage(this._onMessage);
  },

  cleanupBackendListeners() {
    if (this._onConnectionChange) {
      udpBackendManager.offConnectionChange(this._onConnectionChange);
    }
    if (this._onMessage) {
      udpBackendManager.offMessage(this._onMessage);
    }
  },

  updateConnectionStatus() {
    const status = udpBackendManager.getConnectionStatus();
    const connected = status.connected && status.carConnected;
    const message = status.carConnected
      ? '已连接小车(经后端)'
      : (status.connected ? '已连接后端' : '未连接后端');
    this.setData({ connectionStatus: { connected, message } });
  },

  initCanvas() {
    const query = wx.createSelectorQuery();

    // Init Input Canvas
    query.select('#drawCanvas').fields({ node: true, size: true }).exec((res) => {
      if (!res[0]) return;
      const canvas = res[0].node;
      const ctx = canvas.getContext('2d');
      const dpr = wx.getWindowInfo().pixelRatio;
      canvas.width = res[0].width * dpr;
      canvas.height = res[0].height * dpr;
      ctx.scale(dpr, dpr);
      drawCanvas = canvas;
      drawCtx = ctx;
      this.setData({ canvasWidth: res[0].width, canvasHeight: res[0].height });
      this.renderInput();
    });
  },

  handleDeviceMessage(json) {
    // Message handler kept for future use if needed, but trajectory logic removed.
  },

  renderInput() {
    if (!drawCtx) return;
    const ctx = drawCtx;
    ctx.clearRect(0, 0, this.data.canvasWidth, this.data.canvasHeight);
    const points = this.data.points;
    if (points.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
    ctx.strokeStyle = '#1989fa';
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();
  },


  clearCanvas() {
    this.setData({ points: [] });
    this.renderInput();
  },

  handleTouchStart(e) {
    const { x, y } = e.touches[0];
    this.addPoint(x, y);
    this.renderInput();
  },

  handleTouchMove(e) {
    const { x, y } = e.touches[0];
    this.addPoint(x, y);
    this.renderInput();
  },

  addPoint(x, y) {
    const points = this.data.points;
    if (points.length > 0) {
      const last = points[points.length - 1];
      if (Math.sqrt(Math.pow(x - last.x, 2) + Math.pow(y - last.y, 2)) < 5) return;
    }
    points.push({ x, y });
    this.setData({ points });
  },

  generateCircle() {
    const centerX = this.data.canvasWidth / 2, centerY = this.data.canvasHeight / 2;
    const radius = Math.min(centerX, centerY) * 0.6, steps = 32, points = [];
    for (let i = 0; i <= steps; i++) {
      const a = (i / steps) * Math.PI * 2;
      points.push({ x: centerX + Math.cos(a) * radius, y: centerY + Math.sin(a) * radius });
    }
    this.setData({ points }); this.renderInput();
  },

  generateSquare() {
    const centerX = this.data.canvasWidth / 2, centerY = this.data.canvasHeight / 2;
    const side = Math.min(centerX, centerY) * 0.8, points = [];
    const corners = [{ x: centerX - side / 2, y: centerY - side / 2 }, { x: centerX + side / 2, y: centerY - side / 2 }, { x: centerX + side / 2, y: centerY + side / 2 }, { x: centerX - side / 2, y: centerY + side / 2 }, { x: centerX - side / 2, y: centerY - side / 2 }];
    for (let i = 0; i < corners.length - 1; i++) {
      for (let j = 0; j < 10; j++) points.push({ x: corners[i].x + (corners[i + 1].x - corners[i].x) * j / 10, y: corners[i].y + (corners[i + 1].y - corners[i].y) * j / 10 });
    }
    points.push(corners[4]); this.setData({ points }); this.renderInput();
  },

  generateTriangle() {
    const centerX = this.data.canvasWidth / 2, centerY = this.data.canvasHeight / 2;
    const side = Math.min(centerX, centerY) * 0.9, height = side * (Math.sqrt(3) / 2), points = [];
    const corners = [{ x: centerX, y: centerY - height / 2 }, { x: centerX + side / 2, y: centerY + height / 2 }, { x: centerX - side / 2, y: centerY + height / 2 }, { x: centerX, y: centerY - height / 2 }];
    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 10; j++) points.push({ x: corners[i].x + (corners[i + 1].x - corners[i].x) * j / 10, y: corners[i].y + (corners[i + 1].y - corners[i].y) * j / 10 });
    }
    points.push(corners[3]); this.setData({ points }); this.renderInput();
  },

  generateFigure8() {
    const centerX = this.data.canvasWidth / 2, centerY = this.data.canvasHeight / 2, a = Math.min(centerX, centerY) * 0.7, points = [];
    for (let i = 0; i <= 60; i++) {
      const t = (i / 60) * Math.PI * 2, s = a / (1 + Math.pow(Math.sin(t), 2));
      points.push({ x: centerX + s * a * Math.cos(t), y: centerY + s * a * Math.sin(t) * Math.cos(t) });
    }
    this.setData({ points }); this.renderInput();
  },

  // Send command through backend
  _sendBackendCommand(cmd) {
    const status = udpBackendManager.getConnectionStatus();
    if (!status.connected || !status.carConnected) {
      wx.showToast({ title: '请先连接后端和小车', icon: 'none' });
      return false;
    }
    udpBackendManager.sendControl(cmd);
    return true;
  },

  stopCar() {
    if (this._sendBackendCommand({ carMode: 'manual', carStatus: 'stop' })) {
      wx.showToast({ title: '已停止', icon: 'none' });
    }
  },

  startPlan() {
    if (this.data.points.length < 2) return;
    if (this._sendBackendCommand({ carMode: 'path', path: this.simplifyPath(this.data.points) })) {
      wx.showToast({ title: '指令已发送', icon: 'success' });
    }
  },

  simplifyPath(pts) {
    const scale = 5.0, cmds = []; let angle = 0;
    for (let i = 1; i < pts.length; i += 5) {
      const p1 = pts[i - 1], p2 = pts[Math.min(i + 4, pts.length - 1)], dx = p2.x - p1.x, dy = p2.y - p1.y;
      const dist = Math.sqrt(dx * dx + dy * dy) * scale, aDeg = Math.atan2(dx, -dy) * (180 / Math.PI);
      let turn = aDeg - angle;
      while (turn > 180) turn -= 360; while (turn < -180) turn += 360;
      cmds.push({ d: Math.round(dist), a: Math.round(turn) });
      angle = aDeg; if (i + 4 >= pts.length - 1) break;
    }
    return cmds;
  },

  /**
   * 加载演示数据
   */
  loadDemoData: function() {
    console.log('[PathPlanning] 加载演示数据');

    // 延迟生成演示路径，确保canvas已初始化
    setTimeout(() => {
      if (this.data.canvasWidth > 0) {
        this.generateCircle(); // 默认生成圆形路径
      }
    }, 500);
  },

  /**
   * 启动演示定时器
   */
  startDemoTimer: function() {
    if (this.demoTimer) return;

    // 每3秒自动切换不同形状
    const shapes = [
      () => this.generateCircle(),
      () => this.generateSquare(),
      () => this.generateTriangle(),
      () => this.generateFigure8()
    ];

    let currentShape = 0;

    this.demoTimer = setInterval(() => {
      // 清空并生成新形状
      this.setData({ points: [] });
      setTimeout(() => {
        shapes[currentShape]();
        currentShape = (currentShape + 1) % shapes.length;
      }, 200);
    }, 4000);

    console.log('[PathPlanning] 演示定时器已启动');
  },

  /**
   * 停止演示定时器
   */
  stopDemoTimer: function() {
    if (this.demoTimer) {
      clearInterval(this.demoTimer);
      this.demoTimer = null;
      console.log('[PathPlanning] 演示定时器已停止');
    }
  }
});
