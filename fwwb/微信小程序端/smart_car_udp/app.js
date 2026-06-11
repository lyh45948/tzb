// app.js - 融合 smart_agriculture 功能
const networkManager = require('./utils/network-manager');
const udpBackendManager = require('./utils/udp-backend-manager');
const errorHandler = require('./utils/error-handler');
const configManager = require('./utils/config-manager');

App({
  onLaunch() {
    // 初始化配置管理器
    configManager.init();

    // 初始化错误处理器
    errorHandler.init({
      logLevel: configManager.get('logLevel')
    });

    // 初始化网络管理器
    networkManager.init({
      ip: configManager.get('ip'),
      port: configManager.get('port'),
      heartbeatInterval: configManager.get('heartbeatInterval'),
      connectionTimeout: configManager.get('connectionTimeout')
    });

    // 从本地存储加载演示模式状态
    const demoModeEnabled = wx.getStorageSync('demo_mode_enabled') || false;
    this.globalData.demoMode = demoModeEnabled;
    
    // 加载自动控制模式
    this.globalData.autoControl = configManager.get('autoControl') || false;

    // 启动节流定时器
    this.startNotifyTimer();

    console.log('[App] 应用初始化完成，演示模式:', demoModeEnabled);
  },

  globalData: {
    userInfo: null,
    demoMode: false, // 全局演示模式开关
    autoControl: false, // 自动控制模式
    
    // 传感器数据（融合 smart_agriculture）
    sensorData: {
      temperature: 25,
      humidity: 60,
      light: 1200,
      co2: 600,
      tvoc: 0,
      gasMic: 0
    },
    
    // 设备状态（融合 smart_agriculture）
    deviceStatus: {
      pump: false,      // 水泵
      valve: false,     // 电磁阀
      led: false,       // LED 灯
      fan: false,       // 风扇
      buzzer: false     // 蜂鸣器
    },
    
    // 告警状态
    alerts: [],
    
    // 历史数据
    historyData: [],
    
    // 更新定时器
    updateTimer: null,

    // 数据更新回调
    dataUpdateCallback: null,

    // 节流相关
    lastNotifyTime: 0,
    notifyInterval: 3000,  // 3秒
    pendingSensorData: null,
    notifyTimer: null
  },

  /**
   * 设置演示模式
   * @param enabled 是否启用
   * @param useBackend 是否使用后端数据（与数据库同步）
   */
  setDemoMode(enabled, useBackend = false) {
    this.globalData.demoMode = enabled;
    wx.setStorageSync('demo_mode_enabled', enabled);
    console.log('[App] 演示模式已设置为:', enabled, ', 使用后端数据:', useBackend);

    if (enabled && !useBackend) {
      // 本地演示模式（数据不与数据库同步）
      this.startDemoData();
    } else {
      this.stopDemoData();
    }
  },

  /**
   * 设置数据更新回调
   */
  setDataUpdateCallback(callback) {
    this.globalData.dataUpdateCallback = callback;
  },

  /**
   * 通知数据更新
   */
  notifyDataUpdate() {
    if (this.globalData.dataUpdateCallback) {
      this.globalData.dataUpdateCallback();
    }
  },

  /**
   * 更新传感器数据（由后端推送调用）- 带节流
   */
  updateSensorData(data) {
    if (!data) return;

    // 处理agri数据（农业安防传感器）
    const agri = data.agri || {};

    // 缓存最新数据
    this.globalData.pendingSensorData = {
      temperature: data.temp ?? data.temperature ?? this.globalData.sensorData.temperature,
      humidity: data.humi ?? data.humidity ?? this.globalData.sensorData.humidity,
      light: data.lux ?? data.light ?? this.globalData.sensorData.light,
      co2: agri.co2 ?? data.co2 ?? this.globalData.sensorData.co2,
      tvoc: agri.tvoc ?? this.globalData.sensorData.tvoc,
      gasMic: agri.gasMic ?? this.globalData.sensorData.gasMic
    };

    // 检查是否达到更新间隔
    const now = Date.now();
    if (now - this.globalData.lastNotifyTime >= this.globalData.notifyInterval) {
      this._doNotifyUpdate();
    }
  },

  /**
   * 实际执行数据更新通知
   */
  _doNotifyUpdate() {
    if (!this.globalData.pendingSensorData) return;

    // 应用缓存数据
    this.globalData.sensorData = this.globalData.pendingSensorData;
    this.globalData.lastNotifyTime = Date.now();

    this.saveHistoryData();
    this.checkThresholds();
    this.notifyDataUpdate();
  },

  /**
   * 启动节流定时器
   */
  startNotifyTimer() {
    this.stopNotifyTimer();
    this.globalData.notifyTimer = setInterval(() => {
      if (this.globalData.pendingSensorData) {
        this._doNotifyUpdate();
      }
    }, this.globalData.notifyInterval);
    console.log('[App] 节流定时器已启动，间隔:', this.globalData.notifyInterval, 'ms');
  },

  /**
   * 停止节流定时器
   */
  stopNotifyTimer() {
    if (this.globalData.notifyTimer) {
      clearInterval(this.globalData.notifyTimer);
      this.globalData.notifyTimer = null;
    }
  },

  /**
   * 处理设备数据（融合 smart_agriculture）
   */
  handleDeviceData(data) {
    const globalData = this.globalData;
    let dataChanged = false;
    
    // 更新传感器数据
    if (data.sensors) {
      globalData.sensorData = {
        ...globalData.sensorData,
        ...data.sensors
      };
      dataChanged = true;
    }
    
    // 更新设备状态
    if (data.status) {
      globalData.deviceStatus = {
        ...globalData.deviceStatus,
        ...data.status
      };
      dataChanged = true;
    }
    
    // 更新环境数据（兼容旧格式）
    if (data.env) {
      if (data.env.temp !== undefined) globalData.sensorData.temperature = data.env.temp;
      if (data.env.humi !== undefined) globalData.sensorData.humidity = data.env.humi;
      if (data.env.lux !== undefined) globalData.sensorData.light = data.env.lux;
      if (data.env.fan !== undefined) globalData.deviceStatus.fan = data.env.fan;
      if (data.env.led !== undefined) globalData.deviceStatus.led = data.env.led;
      // 处理农业安防传感器数据（CO2/TVOC/燃气）
      const agri = data.env.agri || {};
      if (agri.co2 !== undefined) globalData.sensorData.co2 = agri.co2;
      if (agri.tvoc !== undefined) globalData.sensorData.tvoc = agri.tvoc;
      if (agri.gasMic !== undefined) globalData.sensorData.gasMic = agri.gasMic;
      dataChanged = true;
    }
    
    // 保存历史数据
    if (dataChanged) {
      this.saveHistoryData();
      this.checkThresholds();
      this.notifyDataUpdate();
    }
  },
  
  /**
   * 检查阈值告警
   */
  checkThresholds() {
    const thresholds = configManager.getThresholds();
    const alerts = [];
    
    for (const [key, threshold] of Object.entries(thresholds)) {
      const value = this.globalData.sensorData[key];
      if (value !== undefined) {
        const result = configManager.checkThreshold(key, value);
        if (!result.normal) {
          alerts.push({
            type: key,
            level: result.level,
            message: result.message,
            timestamp: new Date().toISOString()
          });
        }
      }
    }
    
    this.globalData.alerts = alerts;
    
    // 自动控制
    if (this.globalData.autoControl) {
      this.autoControl(alerts);
    }
  },
  
  /**
   * 自动控制逻辑（融合 smart_agriculture）
   */
  autoControl(alerts) {
    alerts.forEach(alert => {
      switch (alert.type) {
        case 'temperature':
          if (alert.level === 'high') {
            this.sendControl('fan', true);
          } else {
            this.sendControl('fan', false);
          }
          break;
        case 'humidity':
          // 空气湿度低时开启水泵（灌溉）
          if (alert.level === 'low') {
            this.sendControl('pump', true);
          } else {
            this.sendControl('pump', false);
          }
          break;
        case 'light':
          if (alert.level === 'low') {
            this.sendControl('led', true);
          } else {
            this.sendControl('led', false);
          }
          break;
      }
    });
  },
  
  /**
   * 发送控制命令
   */
  sendControl(device, status) {
    // 演示模式：只更新本地状态
    if (this.globalData.demoMode) {
      this.globalData.deviceStatus[device] = status;
      this.notifyDataUpdate();
      return;
    }

    // Hi3861 期望的格式是整数 (0/1)，不是字符串 ("on"/"off")
    const command = {};
    command[device] = status ? 1 : 0;

    // 关键修复：根据连接方式选择正确的网络通道
    const backendStatus = udpBackendManager.getConnectionStatus();

    if (backendStatus.connected || backendStatus.demoMode) {
      // 通过后端发送命令
      console.log('[App] 通过后端发送控制命令:', command);
      udpBackendManager.sendControl(command);
    } else if (networkManager.isConnected) {
      // 直连小车发送命令
      console.log('[App] 直连小车发送控制命令:', command);
      networkManager.send(command);
    } else {
      console.warn('[App] 未连接到任何设备，无法发送控制命令');
    }

    this.globalData.deviceStatus[device] = status;
    this.notifyDataUpdate();
  },
  
  /**
   * 保存历史数据
   */
  saveHistoryData() {
    const now = new Date();
    const dataPoint = {
      time: `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`,
      ...this.globalData.sensorData
    };
    
    this.globalData.historyData.push(dataPoint);
    
    // 只保留最近 60 条记录
    if (this.globalData.historyData.length > 60) {
      this.globalData.historyData.shift();
    }
  },
  
  /**
   * 启动演示数据
   * 注意：此方法仅用于离线演示
   * 要与数据库数据一致，请通过 backend_connect 页面连接后端
   */
  startDemoData() {
    this.stopDemoData();

    console.log('[App] 本地演示模式已启动（数据不会与数据库同步）');
    console.log('[App] 如需与数据库同步，请通过 backend_connect 页面连接后端');

    // 设置初始数据
    this.globalData.sensorData = {
      temperature: 25,
      humidity: 60,
      light: 800,
      co2: 450
    };

    this.notifyDataUpdate();
  },
  
  /**
   * 停止演示数据
   */
  stopDemoData() {
    if (this.globalData.updateTimer) {
      clearInterval(this.globalData.updateTimer);
      this.globalData.updateTimer = null;
      console.log('[App] 演示数据定时器已停止');
    }
  },
  
  /**
   * 切换自动控制模式
   */
  toggleAutoControl(enabled) {
    this.globalData.autoControl = enabled;
    configManager.set('autoControl', enabled);
    console.log('[App] 自动控制模式已设置为:', enabled);
  }
})
