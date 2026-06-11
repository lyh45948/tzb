// pages/smart_light/smart_light.js
const app = getApp();
const udpBackendManager = require('../../utils/udp-backend-manager');

Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 连接状态
    connected: false,

    // 当前季节
    currentSeason: '春季',

    // 环境光照
    envLux: 0,
    luxPercent: 0,
    luxLevelText: '未知',
    luxColor: '#969799',

    // 光照控制
    autoMode: true,
    targetBrightness: 0,
    currentBrightness: 0,
    timePeriod: 0,
    timePeriodName: '未知',

    // 光照等级映射
    luxLevelMap: {
      0: { text: '黑暗', color: '#323233' },
      1: { text: '昏暗', color: '#7d7e80' },
      2: { text: '偏暗', color: '#969799' },
      3: { text: '正常', color: '#07c160' },
      4: { text: '明亮', color: '#ff976a' },
      5: { text: '非常明亮', color: '#ee0a24' }
    }
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    this.updateSeason();
    this.initBackendListeners();
    this.loadData();
    this.getLightStatus();
  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    this.updateConnectionStatus();
    this.loadData();

    // 设置数据更新回调
    if (app.setDataUpdateCallback) {
      app.setDataUpdateCallback(() => {
        this.loadData();
      });
    }
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {
    if (app.setDataUpdateCallback) {
      app.setDataUpdateCallback(null);
    }
  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {
    this.cleanupBackendListeners();
    if (app.setDataUpdateCallback) {
      app.setDataUpdateCallback(null);
    }
  },

  /**
   * 初始化后端监听
   */
  initBackendListeners() {
    // 消息回调
    this._onBackendMessage = (data) => {
      console.log('[SmartLight] 收到消息:', data);

      // 处理光照状态
      if (data.type === 'smart_light_status' && data.data) {
        this.handleLightStatus(data.data);
      }

      // 处理实时传感器数据
      if (data.env) {
        this.updateLuxFromSensor(data.env.lux);
      }
    };

    // 连接状态回调
    this._onConnectionChange = (connected, message, data) => {
      this.updateConnectionStatus();
    };

    udpBackendManager.onMessage(this._onBackendMessage);
    udpBackendManager.onConnectionChange(this._onConnectionChange);
  },

  /**
   * 清理后端监听
   */
  cleanupBackendListeners() {
    if (this._onBackendMessage) {
      udpBackendManager.offMessage(this._onBackendMessage);
    }
    if (this._onConnectionChange) {
      udpBackendManager.offConnectionChange(this._onConnectionChange);
    }
  },

  /**
   * 更新季节信息
   */
  updateSeason() {
    const month = new Date().getMonth() + 1;
    let season = '春季';
    if (month >= 3 && month <= 5) {
      season = '春季';
    } else if (month >= 6 && month <= 8) {
      season = '夏季';
    } else if (month >= 9 && month <= 11) {
      season = '秋季';
    } else {
      season = '冬季';
    }
    this.setData({ currentSeason: season });
  },

  /**
   * 更新连接状态
   */
  updateConnectionStatus() {
    const status = udpBackendManager.getConnectionStatus();
    this.setData({
      connected: status.connected || status.demoMode
    });
  },

  /**
   * 加载数据
   */
  loadData() {
    const globalData = app.globalData || {};
    const sensorData = globalData.sensorData || {};

    // 获取环境光照
    const envLux = sensorData.light || globalData.envData?.lux || 0;
    this.updateLuxDisplay(envLux);
  },

  /**
   * 更新光照显示
   */
  updateLuxDisplay(lux) {
    const luxPercent = Math.min(100, Math.round((lux / 2000) * 100));
    const luxLevel = this.getLuxLevel(lux);

    this.setData({
      envLux: lux,
      luxPercent: luxPercent,
      luxLevelText: luxLevel.text,
      luxColor: luxLevel.color
    });
  },

  /**
   * 更新传感器数据
   */
  updateLuxFromSensor(lux) {
    if (lux !== undefined && lux !== null) {
      this.updateLuxDisplay(lux);

      // 如果是自动模式，请求后端重新计算亮度
      if (this.data.autoMode && this.data.connected) {
        this.getLightStatus();
      }
    }
  },

  /**
   * 根据光照值获取等级
   */
  getLuxLevel(lux) {
    if (lux < 50) return this.data.luxLevelMap[0];
    if (lux < 200) return this.data.luxLevelMap[1];
    if (lux < 500) return this.data.luxLevelMap[2];
    if (lux < 1000) return this.data.luxLevelMap[3];
    if (lux < 2000) return this.data.luxLevelMap[4];
    return this.data.luxLevelMap[5];
  },

  /**
   * 获取光照状态
   */
  getLightStatus() {
    if (!this.data.connected) {
      // 离线模式，使用本地计算
      this.calculateLocalBrightness();
      return;
    }

    // 请求后端获取状态
    udpBackendManager.send({
      type: 'smart_light_get',
      deviceId: udpBackendManager.carConfig.deviceId || 'car_001',
      lux: this.data.envLux
    });
  },

  /**
   * 处理光照状态
   */
  handleLightStatus(data) {
    if (!data) return;

    this.setData({
      autoMode: data.mode === 'auto',
      currentBrightness: data.brightness || 0,
      targetBrightness: data.targetBrightness || data.brightness || 0,
      timePeriod: data.timePeriod || 0,
      timePeriodName: data.timePeriodName || '未知'
    });
  },

  /**
   * 本地计算亮度（离线模式）
   */
  calculateLocalBrightness() {
    const { envLux } = this.data;
    const now = new Date();
    const hour = now.getHours();

    // 判断时间段
    let timePeriod = 6;
    let timePeriodName = '深夜';
    if (hour >= 5 && hour < 8) {
      timePeriod = 0;
      timePeriodName = '黎明';
    } else if (hour >= 8 && hour < 12) {
      timePeriod = 1;
      timePeriodName = '上午';
    } else if (hour >= 12 && hour < 14) {
      timePeriod = 2;
      timePeriodName = '中午';
    } else if (hour >= 14 && hour < 17) {
      timePeriod = 3;
      timePeriodName = '下午';
    } else if (hour >= 17 && hour < 19) {
      timePeriod = 4;
      timePeriodName = '黄昏';
    } else if (hour >= 19 && hour < 23) {
      timePeriod = 5;
      timePeriodName = '晚间';
    }

    // 计算亮度（自动模式）
    let brightness = 0;
    if (this.data.autoMode && timePeriod !== 6) {
      if (envLux < 50) {
        brightness = 100;
      } else if (envLux < 200) {
        brightness = 80;
      } else if (envLux < 500) {
        brightness = 50;
      } else if (envLux < 1000) {
        brightness = 20;
      }
    }

    this.setData({
      timePeriod,
      timePeriodName,
      currentBrightness: brightness,
      targetBrightness: this.data.autoMode ? brightness : this.data.targetBrightness
    });
  },

  /**
   * 设置自动模式
   */
  setAutoMode() {
    this.setData({ autoMode: true });

    if (this.data.connected) {
      udpBackendManager.send({
        type: 'smart_light_set_mode',
        deviceId: udpBackendManager.carConfig.deviceId || 'car_001',
        autoMode: true
      });
    } else {
      this.calculateLocalBrightness();
    }

    wx.showToast({ title: '已切换自动模式', icon: 'success' });
  },

  /**
   * 设置手动模式
   */
  setManualMode() {
    this.setData({ autoMode: false });

    if (this.data.connected) {
      udpBackendManager.send({
        type: 'smart_light_set_mode',
        deviceId: udpBackendManager.carConfig.deviceId || 'car_001',
        autoMode: false,
        brightness: this.data.targetBrightness
      });
    }

    wx.showToast({ title: '已切换手动模式', icon: 'none' });
  },

  /**
   * 亮度滑块拖动
   */
  onBrightnessDrag(e) {
    this.setData({ targetBrightness: e.detail });
  },

  /**
   * 亮度滑块改变
   */
  onBrightnessChange(e) {
    const brightness = e.detail;
    this.setData({ targetBrightness: brightness });

    if (this.data.connected) {
      // 关键修复：如果是自动模式，先切换到手动模式
      if (this.data.autoMode) {
        this.setData({ autoMode: false });
      }

      udpBackendManager.send({
        type: 'smart_light_set_brightness',
        deviceId: udpBackendManager.carConfig.deviceId || 'car_001',
        brightness: brightness
      });
    } else {
      this.setData({
        currentBrightness: brightness,
        autoMode: false  // 离线模式也切换到手动
      });
    }
  },

  /**
   * 预设亮度按钮
   */
  setPresetBrightness(e) {
    const value = parseInt(e.currentTarget.dataset.value);
    this.setData({
      targetBrightness: value,
      autoMode: false  // 预设按钮自动切换到手动模式
    });

    if (this.data.connected) {
      udpBackendManager.send({
        type: 'smart_light_set_brightness',
        deviceId: udpBackendManager.carConfig.deviceId || 'car_001',
        brightness: value
      });
    } else {
      this.setData({ currentBrightness: value });
    }
  },

  /**
   * 重置设置
   */
  resetSettings() {
    this.setData({
      autoMode: true,
      targetBrightness: 0
    });

    if (this.data.connected) {
      udpBackendManager.send({
        type: 'smart_light_set_mode',
        deviceId: udpBackendManager.carConfig.deviceId || 'car_001',
        autoMode: true
      });
    } else {
      this.calculateLocalBrightness();
    }

    wx.showToast({ title: '已重置', icon: 'success' });
  }
});
