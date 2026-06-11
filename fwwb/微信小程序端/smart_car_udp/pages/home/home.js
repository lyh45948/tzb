// pages/home/home.js
// 智慧农业监控主界面
const udpBackendManager = require('../../utils/udp-backend-manager');
const app = getApp();

Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 连接状态（用于顶部状态显示）
    connected: false,

    // 演示模式
    isDemoMode: false,

    // 自动控制
    autoControl: false,

    // 传感器数据
    sensorData: {
      temperature: '--',
      humidity: '--',
      light: '--',
      co2: '--'
    },

    // 设备状态
    deviceStatus: {
      pump: false,
      valve: false,
      led: false,
      fan: false
    },

    // 灌溉数据
    irrigationData: {
      recommendedWater: 0,
      needIrrigation: false,
      factors: null
    },

    // 告警列表
    alerts: [],

    // 抽屉菜单显示状态
    showActionSheet: false,

    // 智能光照开关（默认关闭，避免与RGB氛围灯冲突）
    smartLightEnabled: false,

    // RGB氛围灯
    rgb: {
      r: 128,
      g: 200,
      b: 150
    },
    rgbMode: ''  // 当前预设模式: read, sleep, party, off
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad: function (options) {
    this.initAppData();
    this.initBackendMessageListener();
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow: function () {
    this.loadData();
    this.updateConnectionStatus();
    this.updateDemoModeStatus();

    // 设置数据更新回调（接收后端推送的数据）
    if (app.setDataUpdateCallback) {
      app.setDataUpdateCallback(() => {
        this.refreshSensorData();
      });
    }

    // 获取灌溉数据
    this.getIrrigationData();
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide: function () {
    if (app.setDataUpdateCallback) {
      app.setDataUpdateCallback(null);
    }
  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload: function () {
    this.cleanupBackendListeners();
    if (app.setDataUpdateCallback) {
      app.setDataUpdateCallback(null);
    }
  },

  /**
   * 初始化应用数据
   */
  initAppData() {
    this.setData({
      isDemoMode: app.getDemoMode ? app.getDemoMode() : false,
      autoControl: app.globalData.autoControl || false
    });
  },

  /**
   * 加载数据
   */
  loadData() {
    const globalData = app.globalData || {};

    // 传感器数据
    const sensorData = globalData.sensorData || globalData.agricultureData || {
      temperature: '--',
      humidity: '--',
      light: '--',
      co2: '--'
    };

    // 设备状态
    const deviceStatus = globalData.deviceStatus || {
      pump: false,
      valve: false,
      led: false,
      fan: false
    };

    // 告警
    const alerts = globalData.alerts || [];

    // 演示模式和自动控制
    const isDemoMode = app.getDemoMode ? app.getDemoMode() : false;
    const autoControl = globalData.autoControl || false;

    this.setData({
      sensorData,
      deviceStatus,
      alerts,
      isDemoMode,
      autoControl
    });
  },

  /**
   * 更新传感器数据显示
   * 从全局数据刷新界面
   */
  refreshSensorData() {
    const globalData = app.globalData || {};
    const sensorData = globalData.sensorData || this.data.sensorData;
    const deviceStatus = globalData.deviceStatus || this.data.deviceStatus;

    this.setData({
      sensorData,
      deviceStatus
    });

    // 传感器数据更新后重新计算灌溉
    this.getIrrigationData();
  },

  // ==================== 后端消息监听（用于演示模式数据接收）====================

  /**
   * 初始化后端消息监听（仅用于接收演示模式数据）
   */
  initBackendMessageListener() {
    // 消息回调 - 只更新 app.globalData，不直接更新页面
    this._onBackendMessage = (data) => {
      if (data && data.env) {
        // 通过 app.js 的节流机制更新数据
        if (app.updateSensorData) {
          app.updateSensorData(data.env);
        }
      }

      // 处理灌溉计算结果
      if (data && data.type === 'irrigation_calc_result') {
        this.handleIrrigationResult(data.data);
      }
    };

    // 连接状态回调（处理演示模式结果）
    this._onBackendConnectionChange = (connected, message, data) => {
      console.log('[Home] 后端连接状态变化:', connected, message, data);

      // 处理演示模式结果
      if (data && data.type === 'demo_mode_result') {
        if (data.success) {
          this.setData({ isDemoMode: data.enabled });
          wx.showToast({
            title: data.enabled ? '演示模式已开启' : '演示模式已关闭',
            icon: 'success'
          });
        } else {
          this.setData({ isDemoMode: false });
          wx.showToast({ title: data.message || '设置失败', icon: 'none' });
        }
      }
    };

    udpBackendManager.onMessage(this._onBackendMessage);
    udpBackendManager.onConnectionChange(this._onBackendConnectionChange);
  },

  /**
   * 清理后端监听
   */
  cleanupBackendListeners() {
    if (this._onBackendConnectionChange) {
      udpBackendManager.offConnectionChange(this._onBackendConnectionChange);
    }
    if (this._onBackendMessage) {
      udpBackendManager.offMessage(this._onBackendMessage);
    }
  },

  /**
   * 更新连接状态（从后端管理器获取）
   */
  updateConnectionStatus() {
    const status = udpBackendManager.getConnectionStatus();
    this.setData({
      connected: status.connected || status.demoMode || false
    });
  },

  /**
   * 更新演示模式状态
   */
  updateDemoModeStatus() {
    const status = udpBackendManager.getConnectionStatus();
    this.setData({
      isDemoMode: status.demoMode || false
    });
  },

  // ==================== 灌溉功能 ====================

  /**
   * 获取灌溉数据
   */
  getIrrigationData() {
    const { temperature, humidity, light } = this.data.sensorData;

    // 确保传感器数据有效
    if (temperature === '--' || humidity === '--' || light === '--') {
      // 数据无效时显示默认值
      this.setData({
        irrigationData: {
          recommendedWater: 0,
          needIrrigation: false,
          factors: null
        }
      });
      return;
    }

    const temp = parseFloat(temperature) || 25;
    const humi = parseFloat(humidity) || 60;
    const lux = parseFloat(light) || 500;

    // 如果连接了后端，发送请求到后端计算
    if (this.data.connected || this.data.isDemoMode) {
      udpBackendManager.send({
        type: 'irrigation_calc',
        deviceId: udpBackendManager.carConfig.deviceId || 'car_001',
        data: {
          temperature: temp,
          humidity: humi,
          light: lux
        }
      });
    } else {
      // 离线模式：使用本地简化算法
      this.calculateLocalIrrigation(temp, humi, lux);
    }
  },

  /**
   * 本地计算灌溉水量（离线模式）
   */
  calculateLocalIrrigation(temperature, humidity, light) {
    // 简化的本地灌溉算法
    let recommendedWater = 0;
    const factors = {
      temperature: 1.0,
      humidity: 1.0,
      light: 1.0
    };

    // 温度因子：温度越高，蒸发越快，需要更多水
    if (temperature > 30) {
      factors.temperature = 1.2;
    } else if (temperature > 25) {
      factors.temperature = 1.1;
    } else if (temperature < 15) {
      factors.temperature = 0.8;
    }

    // 湿度因子：湿度越低，越需要灌溉
    if (humidity < 40) {
      factors.humidity = 1.5;
      recommendedWater = 500;
    } else if (humidity < 50) {
      factors.humidity = 1.2;
      recommendedWater = 300;
    } else if (humidity < 60) {
      factors.humidity = 1.0;
      recommendedWater = 100;
    } else {
      factors.humidity = 0.8;
      recommendedWater = 0;
    }

    // 光照因子：光照强时蒸发快
    if (light > 1000) {
      factors.light = 1.2;
    } else if (light > 500) {
      factors.light = 1.0;
    } else {
      factors.light = 0.9;
    }

    // 综合计算
    recommendedWater = Math.round(recommendedWater * factors.temperature * factors.light);

    this.setData({
      irrigationData: {
        recommendedWater: recommendedWater,
        needIrrigation: recommendedWater > 0,
        factors: factors
      }
    });
  },

  /**
   * 处理灌溉计算结果
   */
  handleIrrigationResult(data) {
    if (!data) return;
    console.log('[Home] 收到灌溉计算结果:', data);
    this.setData({
      irrigationData: {
        recommendedWater: data.recommendedWater || 0,
        needIrrigation: (data.recommendedWater || 0) > 0,
        factors: data.factors
      }
    });
  },

  /**
   * 执行灌溉
   */
  executeIrrigation() {
    if (!this.data.irrigationData.needIrrigation) return;

    udpBackendManager.send({
      type: 'irrigation_execute',
      deviceId: udpBackendManager.carConfig.deviceId || 'car_001',
      data: {
        waterAmount: this.data.irrigationData.recommendedWater,
        duration: 30,
        triggerType: 'manual',
        sensorData: this.data.sensorData,
        factors: this.data.irrigationData.factors
      }
    });

    wx.showToast({ title: '灌溉已启动', icon: 'success' });
  },

  // ==================== 演示模式和自动控制 ====================

  /**
   * 切换演示模式
   */
  onDemoModeChange(e) {
    const enabled = e.detail;

    // 检查是否已连接后端
    const status = udpBackendManager.getConnectionStatus();
    if (!status.connected) {
      wx.showModal({
        title: '提示',
        content: '演示模式需要先连接后端服务，请点击"更多功能" -> "后端连接"进行连接',
        showCancel: true,
        cancelText: '取消',
        confirmText: '去连接',
        success: (res) => {
          if (res.confirm) {
            // 跳转到后端连接页面
            wx.navigateTo({
              url: '../backend_connect/backend_connect'
            });
          }
        }
      });
      // 重置开关状态
      this.setData({ isDemoMode: false });
      return;
    }

    // 通过后端设置演示模式
    console.log('[Home] 设置演示模式:', enabled);
    udpBackendManager.setDemoMode(enabled, 'demo_car');

    // 先更新本地状态，实际结果由回调处理
    this.setData({ isDemoMode: enabled });
  },

  /**
   * 切换自动控制
   */
  onAutoControlChange(e) {
    const enabled = e.detail;

    if (app.toggleAutoControl) {
      app.toggleAutoControl(enabled);
    } else {
      app.globalData.autoControl = enabled;
    }
  },

  /**
   * 控制水泵
   */
  onPumpChange(e) {
    this.toggleDevice('pump', e.detail);
  },

  /**
   * 控制电磁阀
   */
  onValveChange(e) {
    this.toggleDevice('valve', e.detail);
  },

  /**
   * 控制 LED 灯
   */
  onLedChange(e) {
    this.toggleDevice('led', e.detail);
  },

  /**
   * 控制风扇
   */
  onFanChange(e) {
    this.toggleDevice('fan', e.detail);
  },

  /**
   * 切换设备状态
   * 参考环境监测页面的实现，直接发送UDP命令到Hi3861
   */
  toggleDevice(device, enabled) {
    // 更新本地状态
    this.setData({
      [`deviceStatus.${device}`]: enabled
    });

    // 更新全局状态
    if (app.globalData) {
      if (!app.globalData.deviceStatus) {
        app.globalData.deviceStatus = {};
      }
      app.globalData.deviceStatus[device] = enabled;
    }

    // 构造命令 - Hi3861期望的格式: {fan: 1} 或 {led: 0}
    const command = {};
    command[device] = enabled ? 1 : 0;

    // 通过后端发送
    if (app.sendControl) {
      app.sendControl(device, enabled);
    } else {
      console.log(`[Home] Device ${device}: ${enabled} (未连接)`);
      wx.showToast({
        title: '请先连接小车',
        icon: 'none'
      });
    }
  },

  // ==================== 智能光照控制 ====================

  /**
   * 切换智能光照开关
   * 规则：智能光照和RGB互斥
   * - 开启智能光照时自动关闭RGB（设为黑色）
   * - 智能光照优先级更高
   */
  onSmartLightToggle(e) {
    const enabled = e.detail;
    this.setData({ smartLightEnabled: enabled });

    // 注意：不再发送RGB关闭命令，因为智能光照需要RGB颜色来显示
    // 智能光照会使用保存的RGB颜色（默认暖白光 255,200,150）

    // Hi3861期望的格式: {smartLight: {mode: "auto/manual", brightness: 0-100}}
    const command = {
      smartLight: {
        mode: enabled ? 'auto' : 'manual',
        brightness: enabled ? 50 : 0  // 开启时默认亮度50，关闭时亮度0
      }
    };

    // 通过后端发送
    if (this.data.connected || this.data.isDemoMode) {
      udpBackendManager.sendControl(command);
    }

    wx.showToast({
      title: enabled ? '智能光照已开启' : '智能光照已关闭',
      icon: 'none'
    });
  },

  // ==================== RGB氛围灯控制 ====================

  /**
   * 设置RGB预设模式
   */
  setRgbPreset(e) {
    const mode = e.currentTarget.dataset.mode;
    let r = 0, g = 0, b = 0;

    switch (mode) {
      case 'read': // 阅读模式 - 暖黄光
        r = 255; g = 200; b = 150;
        break;
      case 'sleep': // 睡眠模式 - 微弱蓝光
        r = 10; g = 10; b = 40;
        break;
      case 'party': // 聚会模式 - 紫色
        r = 255; g = 0; b = 255;
        break;
      case 'off': // 关闭
        r = 0; g = 0; b = 0;
        break;
    }

    this.setData({
      'rgb.r': r,
      'rgb.g': g,
      'rgb.b': b,
      rgbMode: mode
    });

    this.sendRgbCommand(r, g, b);
  },

  /**
   * 设置RGB颜色
   */
  setRgbColor(e) {
    const { r, g, b } = e.currentTarget.dataset;
    this.setData({
      'rgb.r': parseInt(r),
      'rgb.g': parseInt(g),
      'rgb.b': parseInt(b),
      rgbMode: ''  // 清除预设模式
    });
    this.sendRgbCommand(parseInt(r), parseInt(g), parseInt(b));
  },

  /**
   * 发送RGB命令
   * 规则：RGB和智能光照互斥
   * - 开启RGB时自动关闭智能光照
   * - 智能灯光优先级更高
   */
  sendRgbCommand(r, g, b) {
    // RGB和智能光照互斥：开启RGB时关闭智能光照
    if (this.data.smartLightEnabled) {
      this.setData({ smartLightEnabled: false });
      if (this.data.connected || this.data.isDemoMode) {
        udpBackendManager.sendControl({ smartLight: { mode: 'manual', brightness: 0 } });
      }
    }

    // Hi3861期望的格式: {rgb: {r: 255, g: 0, b: 0}}
    const command = { rgb: { r, g, b } };

    // 通过后端发送
    if (this.data.connected || this.data.isDemoMode) {
      udpBackendManager.sendControl(command);
    }
    console.log('[Home] RGB:', r, g, b);
  },

  /**
   * 跳转设置页面
   */
  goToSettings() {
    wx.navigateTo({
      url: '../settings/settings'
    });
  },

  /**
   * 显示更多功能菜单
   */
  showMoreMenu() {
    this.setData({ showActionSheet: true });
  },

  /**
   * 隐藏更多功能菜单
   */
  hideMoreMenu() {
    this.setData({ showActionSheet: false });
  },

  /**
   * 导航方法
   */
  gotoNfc() {
    this.hideMoreMenu();
    wx.navigateTo({
      url: '../nfc/nfc'
    });
  },

  gotoControl() {
    this.hideMoreMenu();
    wx.navigateTo({
      url: '../control/control'
    });
  },

  gotoPath() {
    this.hideMoreMenu();
    wx.navigateTo({
      url: '../path_planning/path_planning'
    });
  },

  gotoEnv() {
    this.hideMoreMenu();
    wx.navigateTo({
      url: '../environment/environment'
    });
  },

  gotoRecord() {
    this.hideMoreMenu();
    wx.navigateTo({
      url: '../record_playback/record_playback'
    });
  },

  gotoFence() {
    this.hideMoreMenu();
    wx.navigateTo({
      url: '../virtual_fence/virtual_fence'
    });
  },

  gotoSmartLight() {
    this.hideMoreMenu();
    wx.navigateTo({
      url: '../smart_light/smart_light'
    });
  },

  gotoSmartIrrigation() {
    this.hideMoreMenu();
    wx.navigateTo({
      url: '../smart_irrigation/smart_irrigation'
    });
  },

  gotoBackendConnect() {
    this.hideMoreMenu();
    wx.navigateTo({
      url: '../backend_connect/backend_connect'
    });
  }
});
