// pages/factory_dashboard/factory_dashboard.js
// 智慧工厂安全监测控制平台 - 主监控界面
const udpBackendManager = require('../../utils/udp-backend-manager');
const app = getApp();

Page({
  data: {
    // 连接状态
    connected: false,
    currentTime: '--:--:--',

    // 传感器数据
    sensorData: {
      temperature: '--',
      humidity: '--',
      co2: '--',
      tvoc: '--',
      gasMic: '--',
      lux: '--',
      pir_detected: false
    },

    // 警报状态
    alertLevel: 0,
    alertType: 0,
    alertCount: 0,
    alertMessage: '',

    // 气体警报标志
    co2Alert: false,
    gasMicAlert: false,
    tempAlert: false,
    humiAlert: false,

    // 温湿度进度
    tempRate: 0,
    humiRate: 0,

    // 人体感应
    pirDetected: false,

    // 货物计数
    goodsCount: 0,
    goodsCountDelta: 0,

    // AGV状态
    agvDistance: 999,
    agvObstacle: false,

    // 设备状态
    deviceStatus: {
      fan: false,
      led: false,
      buzzer: false
    }
  },

  // 阈值配置
  thresholds: {
    temperature: { warning: 30, danger: 35 },
    humidity: { warning: 75, danger: 80 },
    co2: { warning: 800, danger: 1000 },
    gasMic: { warning: 2000, danger: 4000 },
    agv_distance: { warning: 30, danger: 15 }
  },

  onLoad(options) {
    this.initAppData();
    this.initBackendMessageListener();
    this.startTimeUpdate();
  },

  onShow() {
    this.updateConnectionStatus();
    if (app.setDataUpdateCallback) {
      app.setDataUpdateCallback(() => {
        this.refreshSensorData();
      });
    }
  },

  onHide() {
    if (app.setDataUpdateCallback) {
      app.setDataUpdateCallback(null);
    }
  },

  onUnload() {
    this.cleanupBackendListeners();
    if (this.timeInterval) {
      clearInterval(this.timeInterval);
    }
  },

  // 初始化应用数据
  initAppData() {
    this.setData({
      isDemoMode: app.getDemoMode ? app.getDemoMode() : false,
    });
  },

  // 初始化后端消息监听
  initBackendMessageListener() {
    this._onBackendMessage = (data) => {
      console.log('[DEBUG] 收到消息:', data);
      if (data && data.env) {
        this.processSensorData(data.env);
      } else if (data && data.data && data.data.env) {
        this.processSensorData(data.data.env);
      }
    };

    udpBackendManager.onMessage(this._onBackendMessage);
  },

  // 清理后端监听
  cleanupBackendListeners() {
    if (this._onBackendMessage) {
      udpBackendManager.offMessage(this._onBackendMessage);
    }
  },

  // 更新连接状态
  updateConnectionStatus() {
    const status = udpBackendManager.getConnectionStatus();
    this.setData({
      connected: status.connected || status.demoMode || false
    });
  },

  // 开始时间更新
  startTimeUpdate() {
    const updateTime = () => {
      const now = new Date();
      const timeStr = now.toTimeString().split(' ')[0];
      this.setData({ currentTime: timeStr });
    };
    updateTime();
    this.timeInterval = setInterval(updateTime, 1000);
  },

  // 处理传感器数据
  processSensorData(env) {
    // 从agri对象获取农业安防数据
    const agri = env.agri || {};
    console.log('[DEBUG] env.agri:', agri);

    const sensorData = {
      temperature: env.temp !== undefined ? env.temp : this.data.sensorData.temperature,
      humidity: env.humi !== undefined ? env.humi : this.data.sensorData.humidity,
      co2: agri.co2 !== undefined ? agri.co2 : (env.co2 !== undefined ? env.co2 : this.data.sensorData.co2),
      tvoc: agri.tvoc !== undefined ? agri.tvoc : this.data.sensorData.tvoc,
      gasMic: agri.gasMic !== undefined ? agri.gasMic : this.data.sensorData.gasMic,
      lux: env.lux !== undefined ? env.lux : this.data.sensorData.lux,
      pir_detected: env.pir_detected !== undefined ? env.pir_detected : this.data.sensorData.pir_detected
    };

    // 确保数值类型正确显示
    if (typeof sensorData.co2 === 'number') sensorData.co2 = sensorData.co2;
    if (typeof sensorData.tvoc === 'number') sensorData.tvoc = sensorData.tvoc;
    if (typeof sensorData.gasMic === 'number') sensorData.gasMic = sensorData.gasMic;

    console.log('[DEBUG] sensorData:', sensorData);

    // 处理工厂警报数据
    const factoryAlert = env.factoryAlert || {};
    const goodsCount = factoryAlert.goodsCount || this.data.goodsCount;
    const goodsCountDelta = factoryAlert.goodsCountDelta || 0;
    const agvDistance = factoryAlert.agvDistance || this.data.agvDistance;
    const agvObstacle = factoryAlert.agvObstacleFlag || false;
    const alertLevel = factoryAlert.level || 0;
    const alertCount = factoryAlert.count || 0;

    // 检查阈值
    const tempAlert = sensorData.temperature > this.thresholds.temperature.danger;
    const humiAlert = sensorData.humidity > this.thresholds.humidity.danger;
    const co2Alert = sensorData.co2 > this.thresholds.co2.danger;
    const gasMicAlert = sensorData.gasMic > this.thresholds.gasMic.danger;

    // 计算温湿度进度
    const tempRate = Math.min(100, (sensorData.temperature / 50) * 100);
    const humiRate = Math.min(100, sensorData.humidity);

    // 生成警报消息
    let alertMessage = '';
    if (alertLevel >= 3) {
      alertMessage = '紧急警报：检测到危险气体或火焰！';
    } else if (alertLevel >= 2) {
      alertMessage = '危险警报：环境参数超标！';
    } else if (alertLevel >= 1) {
      alertMessage = '警告：环境参数接近阈值';
    }

    // 更新设备状态
    const deviceStatus = {
      fan: env.fan || false,
      led: env.led || false,
      buzzer: env.buzzer || false
    };

    this.setData({
      sensorData,
      goodsCount,
      goodsCountDelta,
      agvDistance,
      agvObstacle,
      alertLevel,
      alertCount,
      alertMessage,
      co2Alert,
      gasMicAlert,
      tempAlert,
      humiAlert,
      pirDetected: sensorData.pir_detected,
      tempRate,
      humiRate,
      deviceStatus
    });
  },

  // 刷新传感器数据
  refreshSensorData() {
    const globalData = app.globalData || {};
    const sensorData = globalData.sensorData || this.data.sensorData;
    this.setData({ sensorData });
  },

  // 设备控制
  onFanChange(e) {
    this.toggleDevice('fan', e.detail);
  },

  onLedChange(e) {
    this.toggleDevice('led', e.detail);
  },

  onBuzzerChange(e) {
    this.toggleDevice('buzzer', e.detail);
  },

  toggleDevice(device, enabled) {
    this.setData({
      [`deviceStatus.${device}`]: enabled
    });

    const command = {};
    command[device] = enabled ? 1 : 0;

    if (this.data.connected || this.data.isDemoMode) {
      udpBackendManager.sendControl(command);
    }
  },

  // 导航
  gotoEquipment() {
    wx.navigateTo({
      url: '../equipment_control/equipment_control'
    });
  },

  gotoAlertCenter() {
    wx.navigateTo({
      url: '../alert_center/alert_center'
    });
  }
});