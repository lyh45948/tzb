// pages/backend_connect/backend_connect.js
const udpBackendManager = require('../../utils/udp-backend-manager');
const app = getApp();

Page({
  data: {
    // 连接状态
    backendConnected: false,  // 后端连接状态
    connected: false,         // 小车连接状态
    connecting: false,
    statusText: '未连接',

    // 后端配置
    backendIp: '192.168.31.140',
    backendPort: '8888',

    // 小车配置 (可选)
    carIp: '',
    carPort: '7788',

    // 传感器数据
    sensorData: null
  },

  onLoad() {
    this.loadConfig();
    this.initCallbacks();
  },

  onShow() {
    this.updateStatus();
  },

  onUnload() {
    // 移除回调
    udpBackendManager.offMessage(this._onMessage);
    udpBackendManager.offConnectionChange(this._onConnectionChange);
  },

  loadConfig() {
    try {
      udpBackendManager.loadConfig();
      const status = udpBackendManager.getConnectionStatus();
      this.setData({
        backendIp: status.backendIp || '192.168.31.140',
        backendPort: String(status.backendPort || 8888),
        carIp: status.carIp || '',
        carPort: String(status.carPort || 7788)
      });
    } catch (e) {
      console.error('加载配置失败:', e);
    }
  },

  saveConfig() {
    try {
      wx.setStorageSync('backend_config', {
        backendIp: this.data.backendIp,
        backendPort: this.data.backendPort,
        carIp: this.data.carIp,
        carPort: this.data.carPort
      });
    } catch (e) {
      console.error('保存配置失败:', e);
    }
  },

  initCallbacks() {
    // 连接状态回调
    this._onConnectionChange = (connected, message, data) => {
      console.log('[BackendConnect] 连接状态:', connected, message, data);

      // 处理小车连接结果
      if (data && data.type === 'connect_result') {
        if (data.success) {
          this.setData({
            connected: true,
            connecting: false,
            statusText: '已连接小车'
          });
          wx.showToast({ title: '小车连接成功', icon: 'success' });
        } else {
          this.setData({ connecting: false });
          wx.showToast({ title: data.message || '小车连接失败', icon: 'none' });
        }
        return;
      }

      // 处理演示模式结果
      if (data && data.type === 'demo_mode_result') {
        if (data.success) {
          this.setData({
            connected: data.enabled,
            connecting: false,
            statusText: data.enabled ? '演示模式' : '未连接小车'
          });
          wx.showToast({
            title: data.enabled ? '演示模式已开启' : '演示模式已关闭',
            icon: 'success'
          });
        } else {
          this.setData({ connecting: false });
          wx.showToast({ title: data.message || '设置失败', icon: 'none' });
        }
        return;
      }

      // 处理后端连接状态变化
      this.setData({
        backendConnected: connected,
        connecting: false,
        statusText: connected ? '已连接后端' : message
      });

      if (connected) {
        wx.showToast({ title: '后端连接成功', icon: 'success' });
      } else if (message && message.includes('超时')) {
        wx.showToast({ title: message, icon: 'none', duration: 3000 });
      }
    };

    // 消息回调
    this._onMessage = (data) => {
      console.log('[BackendConnect] 收到数据:', data);
      if (data && data.env) {
        // 实时数据
        const envData = data.env || {};
        this.setData({
          sensorData: {
            temperature: envData.temp,
            humidity: envData.humi,
            light: envData.lux,
            co2: envData.co2
          }
        });

        // 更新全局数据
        if (app.updateSensorData) {
          app.updateSensorData(envData);
        } else if (app.globalData) {
          app.globalData.sensorData = {
            temperature: envData.temp,
            humidity: envData.humi,
            light: envData.lux,
            co2: envData.co2 || '--'
          };
          app.globalData.envData = envData;
          if (app.notifyDataUpdate) {
            app.notifyDataUpdate();
          }
        }
      }
    };

    udpBackendManager.onConnectionChange(this._onConnectionChange);
    udpBackendManager.onMessage(this._onMessage);
  },

  updateStatus() {
    const status = udpBackendManager.getConnectionStatus();
    this.setData({
      backendConnected: status.connected,
      connected: status.carConnected,
      statusText: this._getStatusText(status)
    });
  },

  _getStatusText(status) {
    if (status.carConnected) return '已连接小车';
    if (status.connected) return '已连接后端';
    return '未连接';
  },

  // 输入处理
  onBackendIpInput(e) {
    this.setData({ backendIp: e.detail.value });
  },

  onBackendPortInput(e) {
    this.setData({ backendPort: e.detail.value });
  },

  onCarIpInput(e) {
    this.setData({ carIp: e.detail.value });
  },

  onCarPortInput(e) {
    this.setData({ carPort: e.detail.value });
  },

  // 连接后端
  onConnectBackend() {
    if (this.data.connecting || this.data.backendConnected) return;

    if (!this.data.backendIp) {
      wx.showToast({ title: '请输入后端IP', icon: 'none' });
      return;
    }

    this.setData({ connecting: true, statusText: '正在连接后端...' });

    // 保存配置
    this.saveConfig();

    // 配置后端地址
    udpBackendManager.saveConfig(
      { ip: this.data.backendIp, port: parseInt(this.data.backendPort) },
      null
    );

    // 连接到后端（异步验证，通过回调获取结果）
    udpBackendManager.connect();
    // 不再立即显示成功，等待 _onConnectionChange 回调
  },

  // 连接小车
  onConnect() {
    if (this.data.connecting || this.data.connected) return;

    if (!this.data.backendConnected) {
      wx.showToast({ title: '请先连接后端', icon: 'none' });
      return;
    }

    if (!this.data.carIp) {
      wx.showToast({ title: '请输入小车IP', icon: 'none' });
      return;
    }

    this.setData({ connecting: true, statusText: '正在连接小车...' });

    // 连接小车
    udpBackendManager.connectToCar(
      this.data.carIp,
      parseInt(this.data.carPort),
      null
    );
  },

  // 断开连接
  onDisconnect() {
    // 断开小车
    if (this.data.connected) {
      udpBackendManager.disconnectFromCar();
    }

    // 断开后端
    udpBackendManager.disconnect();

    this.setData({
      backendConnected: false,
      connected: false,
      statusText: '未连接',
      sensorData: null
    });

    wx.showToast({ title: '已断开连接', icon: 'none' });
  }
});
