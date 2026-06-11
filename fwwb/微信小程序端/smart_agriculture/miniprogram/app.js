// app.js - 智慧农业小程序入口
const { getNetworkManager } = require('./utils/network-manager');
const configManager = require('./utils/config-manager');

App({
  globalData: {
    // 设备连接状态
    connected: false,
    // 演示模式
    demoMode: false,
    // 自动控制模式
    autoControl: false,
    // 传感器数据
    sensorData: {
      temperature: 25,
      humidity: 60,
      light: 1200,
      soilMoisture: 55,
      co2: 600
    },
    // 设备状态
    deviceStatus: {
      pump: false,      // 水泵
      valve: false,     // 电磁阀
      led: false,       // LED灯
      fan: false        // 风扇
    },
    // 告警状态
    alerts: [],
    // 历史数据
    historyData: [],
    // 更新定时器
    updateTimer: null
  },

  onLaunch() {
    console.log('智慧农业小程序启动');

    // 加载配置
    this.loadConfig();

    // 初始化网络
    this.initNetwork();
  },

  onShow() {
    console.log('小程序显示');
  },

  onHide() {
    console.log('小程序隐藏');
    this.stopDataUpdate();
  },

  // 加载配置
  loadConfig() {
    const config = configManager.getConfig();
    this.globalData.demoMode = config.demoMode;
    this.globalData.autoControl = config.autoControl;
    console.log('加载配置:', config);
  },

  // 初始化网络
  initNetwork() {
    if (this.globalData.demoMode) {
      console.log('演示模式，跳过网络初始化');
      this.startDemoData();
      return;
    }

    const networkManager = getNetworkManager();
    const success = networkManager.init((data) => {
      this.handleDeviceData(data);
    });

    if (success) {
      console.log('网络初始化成功');
    } else {
      console.error('网络初始化失败');
      // 自动切换到演示模式
      this.globalData.demoMode = true;
      this.startDemoData();
    }
  },

  // 处理设备数据
  handleDeviceData(data) {
    if (data.sensors) {
      // 更新传感器数据
      this.globalData.sensorData = {
        ...this.globalData.sensorData,
        ...data.sensors
      };
      this.checkThresholds();
    }

    if (data.status) {
      // 更新设备状态
      this.globalData.deviceStatus = {
        ...this.globalData.deviceStatus,
        ...data.status
      };
    }

    // 保存历史数据
    this.saveHistoryData();

    // 通知页面更新
    this.notifyDataUpdate();
  },

  // 检查阈值告警
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

  // 自动控制逻辑
  autoControl(alerts) {
    const networkManager = getNetworkManager();

    alerts.forEach(alert => {
      switch (alert.type) {
        case 'temperature':
          if (alert.level === 'high') {
            // 温度过高，开启风扇
            this.sendControl('fan', true);
          } else {
            this.sendControl('fan', false);
          }
          break;
        case 'soilMoisture':
          if (alert.level === 'low') {
            // 土壤过干，开启水泵
            this.sendControl('pump', true);
          } else {
            this.sendControl('pump', false);
          }
          break;
        case 'light':
          if (alert.level === 'low') {
            // 光照不足，开启LED
            this.sendControl('led', true);
          } else {
            this.sendControl('led', false);
          }
          break;
      }
    });
  },

  // 发送控制命令
  sendControl(device, status) {
    if (this.globalData.demoMode) {
      this.globalData.deviceStatus[device] = status;
      return;
    }

    const networkManager = getNetworkManager();
    const command = {
      [device]: status ? 'on' : 'off'
    };
    networkManager.sendCommand(command);
    this.globalData.deviceStatus[device] = status;
  },

  // 保存历史数据
  saveHistoryData() {
    const now = new Date();
    const dataPoint = {
      time: `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`,
      ...this.globalData.sensorData
    };

    this.globalData.historyData.push(dataPoint);

    // 只保留最近60条记录
    if (this.globalData.historyData.length > 60) {
      this.globalData.historyData.shift();
    }
  },

  // 通知页面更新
  notifyDataUpdate() {
    // 使用事件机制通知页面
    if (this.dataUpdateCallback) {
      this.dataUpdateCallback();
    }
  },

  // 设置数据更新回调
  setDataUpdateCallback(callback) {
    this.dataUpdateCallback = callback;
  },

  // 启动演示数据
  startDemoData() {
    this.stopDataUpdate();

    let time = 0;
    this.globalData.updateTimer = setInterval(() => {
      time += 1;

      // 使用正弦波模拟数据变化
      this.globalData.sensorData = {
        temperature: Math.round(25 + 5 * Math.sin(time * 0.1)),
        humidity: Math.round(60 + 10 * Math.sin(time * 0.08)),
        light: Math.round(1200 + 300 * Math.sin(time * 0.05)),
        soilMoisture: Math.round(55 + 15 * Math.sin(time * 0.03)),
        co2: Math.round(600 + 200 * Math.sin(time * 0.06))
      };

      this.saveHistoryData();
      this.checkThresholds();
      this.notifyDataUpdate();
    }, 1000);
  },

  // 停止数据更新
  stopDataUpdate() {
    if (this.globalData.updateTimer) {
      clearInterval(this.globalData.updateTimer);
      this.globalData.updateTimer = null;
    }
  },

  // 切换演示模式
  toggleDemoMode(enabled) {
    this.globalData.demoMode = enabled;
    configManager.saveConfig({ demoMode: enabled });

    if (enabled) {
      this.startDemoData();
    } else {
      this.stopDataUpdate();
      this.initNetwork();
    }
  }
});
