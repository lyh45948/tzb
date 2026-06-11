// network-manager.js - UDP网络通信管理
const errorHandler = require('./error-handler');

class NetworkManager {
  constructor() {
    this.udp = null;
    this.deviceIP = '192.168.1.100'; // 默认设备IP
    this.devicePort = 7788;          // 默认设备端口
    this.localPort = 7789;           // 本地端口
    this.connected = false;
    this.onDataCallback = null;
    this.reconnectTimer = null;
  }

  // 初始化UDP连接
  init(callback) {
    this.onDataCallback = callback;

    try {
      this.udp = wx.createUDPSocket();

      if (!this.udp) {
        errorHandler.handleError('NETWORK_ERROR', '无法创建UDP Socket');
        return false;
      }

      // 绑定本地端口
      this.udp.bind(this.localPort);

      // 监听消息
      this.udp.onMessage((res) => {
        this.handleMessage(res);
      });

      // 监听错误
      this.udp.onError((err) => {
        console.error('UDP错误:', err);
        this.connected = false;
        errorHandler.handleError('NETWORK_ERROR', err.errMsg);
      });

      // 监听关闭
      this.udp.onClose(() => {
        console.log('UDP连接关闭');
        this.connected = false;
      });

      this.connected = true;
      console.log('UDP初始化成功, 本地端口:', this.localPort);
      return true;

    } catch (e) {
      console.error('UDP初始化异常:', e);
      errorHandler.handleError('NETWORK_ERROR', e.message);
      return false;
    }
  }

  // 处理接收的消息
  handleMessage(res) {
    try {
      const message = String.fromCharCode.apply(null, new Uint8Array(res.message));
      console.log('收到消息:', message);

      const data = JSON.parse(message);

      if (this.onDataCallback) {
        this.onDataCallback(data);
      }
    } catch (e) {
      console.error('解析消息失败:', e);
    }
  }

  // 发送命令
  sendCommand(command) {
    if (!this.udp || !this.connected) {
      console.error('UDP未连接');
      return false;
    }

    try {
      const message = JSON.stringify(command);
      this.udp.send({
        address: this.deviceIP,
        port: this.devicePort,
        message: message
      });
      console.log('发送命令:', message);
      return true;
    } catch (e) {
      console.error('发送命令失败:', e);
      errorHandler.handleError('NETWORK_ERROR', '发送命令失败');
      return false;
    }
  }

  // 发送控制命令
  sendControl(device, status) {
    return this.sendCommand({
      action: device,
      value: status
    });
  }

  // 设置设备地址
  setDeviceAddress(ip, port) {
    this.deviceIP = ip;
    this.devicePort = port || 7788;
    console.log('设备地址设置为:', this.deviceIP, ':', this.devicePort);
  }

  // 关闭连接
  close() {
    if (this.udp) {
      this.udp.close();
      this.udp = null;
    }
    this.connected = false;
    if (this.reconnectTimer) {
      clearInterval(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  // 获取连接状态
  isConnected() {
    return this.connected;
  }
}

// 单例模式
let instance = null;

function getNetworkManager() {
  if (!instance) {
    instance = new NetworkManager();
  }
  return instance;
}

module.exports = {
  NetworkManager,
  getNetworkManager
};
