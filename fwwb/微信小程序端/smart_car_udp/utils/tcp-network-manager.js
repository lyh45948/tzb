/**
 * TCP网络管理器 - 连接后端服务
 * 用于与Python后端进行TCP通信
 */
const errorHandler = require('./error-handler');

class TCPNetworkManager {
  constructor() {
    this.tcp = null;
    this.isConnected = false;
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000;
    this.heartbeatTimer = null;
    this.lastReceiveTime = 0;
    this.heartbeatInterval = 5000;
    this.connectionTimeout = 15000;
    this.messageCallbacks = [];
    this.connectionCallbacks = [];
    this.receiveBuffer = '';

    // 后端配置
    this.backendConfig = {
      ip: '',
      port: 8888
    };

    // 小车配置
    this.carConfig = {
      ip: '',
      port: 7788,
      deviceId: ''
    };

    // 小车连接状态
    this.carConnected = false;
  }

  /**
   * 初始化
   */
  init(config) {
    if (config) {
      this.backendConfig = { ...this.backendConfig, ...config };
    }
    this.loadConfig();
  }

  /**
   * 加载配置
   */
  loadConfig() {
    try {
      const savedConfig = wx.getStorageSync('tcp_network_config');
      if (savedConfig) {
        this.backendConfig = { ...this.backendConfig, ...savedConfig.backend };
        this.carConfig = { ...this.carConfig, ...savedConfig.car };
      }
    } catch (error) {
      console.error('[TCPManager] 加载配置失败:', error);
    }
  }

  /**
   * 保存配置
   */
  saveConfig(backendConfig, carConfig) {
    try {
      if (backendConfig) {
        this.backendConfig = { ...this.backendConfig, ...backendConfig };
      }
      if (carConfig) {
        this.carConfig = { ...this.carConfig, ...carConfig };
      }
      wx.setStorageSync('tcp_network_config', {
        backend: this.backendConfig,
        car: this.carConfig
      });
    } catch (error) {
      console.error('[TCPManager] 保存配置失败:', error);
    }
  }

  /**
   * 连接到后端服务器
   */
  async connectToBackend() {
    if (this.isConnecting) {
      console.log('[TCPManager] 正在连接中');
      return false;
    }

    if (!this.backendConfig.ip) {
      console.error('[TCPManager] 后端IP未配置');
      this.notifyConnectionChange(false, '后端IP未配置');
      return false;
    }

    this.isConnecting = true;
    this.notifyConnectionChange(false, '正在连接后端...');

    try {
      // 关闭旧连接
      if (this.tcp) {
        try {
          this.tcp.offMessage();
          this.tcp.offError();
          this.tcp.offClose();
          this.tcp.close();
        } catch (e) {}
      }

      // 创建TCP Socket
      this.tcp = wx.createTCPSocket();

      // 监听消息
      this.tcp.onMessage(this.handleMessage.bind(this));

      // 监听错误
      this.tcp.onError(this.handleError.bind(this));

      // 监听关闭
      this.tcp.onClose(() => {
        console.log('[TCPManager] TCP连接已关闭');
        this.isConnected = false;
        this.isConnecting = false;
        this.carConnected = false;
        this.stopHeartbeat();
        this.notifyConnectionChange(false, '连接已断开');
        this.startReconnect();
      });

      // 监听连接成功
      this.tcp.onConnect(() => {
        console.log('[TCPManager] TCP连接成功');
        this.isConnected = true;
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.receiveBuffer = '';
        this.startHeartbeat();
        this.notifyConnectionChange(true, '已连接到后端');
      });

      // 连接到后端
      this.tcp.connect({
        address: this.backendConfig.ip,
        port: this.backendConfig.port
      });

      return true;
    } catch (error) {
      this.isConnecting = false;
      console.error('[TCPManager] 连接失败:', error);
      this.notifyConnectionChange(false, '连接失败: ' + error.message);
      this.startReconnect();
      return false;
    }
  }

  /**
   * 连接到小车 (通过后端)
   */
  connectToCar(carIp, carPort, deviceId) {
    if (!this.isConnected) {
      console.error('[TCPManager] 未连接到后端');
      return false;
    }

    // 保存小车配置
    this.carConfig = {
      ip: carIp,
      port: carPort || 7788,
      deviceId: deviceId || `car_${carIp.replace(/\./g, '_')}`
    };
    this.saveConfig();

    // 发送连接请求
    const message = {
      type: 'connect',
      carIp: carIp,
      carPort: this.carConfig.port,
      deviceId: this.carConfig.deviceId
    };

    console.log('[TCPManager] 请求连接小车:', message);
    return this.send(message);
  }

  /**
   * 断开小车连接
   */
  disconnectFromCar() {
    if (!this.isConnected) return;

    const message = { type: 'disconnect' };
    this.send(message);
    this.carConnected = false;
  }

  /**
   * 断开所有连接
   */
  disconnect() {
    console.log('[TCPManager] 断开连接');

    this.stopHeartbeat();
    this.stopReconnect();

    if (this.tcp) {
      try {
        this.tcp.offMessage();
        this.tcp.offError();
        this.tcp.offClose();
        this.tcp.close();
      } catch (e) {}
      this.tcp = null;
    }

    this.isConnected = false;
    this.isConnecting = false;
    this.carConnected = false;
    this.notifyConnectionChange(false, '已断开');
  }

  /**
   * 发送数据
   */
  send(message) {
    if (!this.isConnected || !this.tcp) {
      console.warn('[TCPManager] 未连接，无法发送');
      return false;
    }

    try {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
      // 添加换行符作为消息分隔符
      const data = (messageStr + '\n').trim() + '\n';

      this.tcp.write({
        address: this.backendConfig.ip,
        port: this.backendConfig.port,
        data: data
      });
      return true;
    } catch (error) {
      console.error('[TCPManager] 发送失败:', error);
      return false;
    }
  }

  /**
   * 发送控制命令
   */
  sendControl(command) {
    const message = {
      type: 'control',
      command: command
    };
    return this.send(message);
  }

  /**
   * 查询历史数据
   */
  queryHistory(action, params) {
    const message = {
      type: 'query',
      action: action,
      params: params
    };
    return this.send(message);
  }

  /**
   * 处理接收到的消息
   */
  handleMessage(res) {
    this.lastReceiveTime = Date.now();

    try {
      // 将接收到的数据添加到缓冲区
      const data = String.fromCharCode.apply(null, new Uint8Array(res.message));
      this.receiveBuffer += data;

      // 按换行符分割消息
      let lines = this.receiveBuffer.split('\n');

      // 最后一个可能是不完整的消息，保留在缓冲区
      this.receiveBuffer = lines.pop();

      // 处理完整的消息
      for (let line of lines) {
        line = line.trim();
        if (!line) continue;

        try {
          const json = JSON.parse(line);
          this.processMessage(json);
        } catch (e) {
          console.error('[TCPManager] JSON解析失败:', e, line);
        }
      }
    } catch (error) {
      console.error('[TCPManager] 处理消息失败:', error);
    }
  }

  /**
   * 处理解析后的消息
   */
  processMessage(message) {
    const msgType = message.type;

    switch (msgType) {
      case 'connect_result':
        // 连接小车结果
        if (message.success) {
          this.carConnected = true;
          console.log('[TCPManager] 小车连接成功:', message.message);
        } else {
          this.carConnected = false;
          console.error('[TCPManager] 小车连接失败:', message.message);
        }
        this.notifyConnectionChange(this.isConnected, message.message, message);
        break;

      case 'disconnect_result':
        this.carConnected = false;
        console.log('[TCPManager] 小车已断开');
        break;

      case 'realtime':
        // 实时数据
        this.notifyMessageCallbacks(message.data);
        break;

      case 'query_result':
        // 查询结果
        this.notifyMessageCallbacks(message);
        break;

      case 'status':
        // 状态消息
        console.log('[TCPManager] 状态:', message.message);
        break;

      case 'error':
        console.error('[TCPManager] 服务器错误:', message.message);
        break;

      default:
        // 其他消息直接传递给回调
        this.notifyMessageCallbacks(message);
    }
  }

  /**
   * 通知消息回调
   */
  notifyMessageCallbacks(data) {
    this.messageCallbacks.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error('[TCPManager] 消息回调执行失败:', error);
      }
    });
  }

  /**
   * 处理错误
   */
  handleError(error) {
    console.error('[TCPManager] 发生错误:', error);
    this.isConnected = false;
    this.isConnecting = false;
    this.carConnected = false;
    this.notifyConnectionChange(false, '连接错误');
    this.startReconnect();
  }

  /**
   * 启动心跳
   */
  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.checkConnectionTimeout();
    }, this.heartbeatInterval);
  }

  /**
   * 停止心跳
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 检查连接超时
   */
  checkConnectionTimeout() {
    if (this.isConnected) {
      const timeSinceLastReceive = Date.now() - this.lastReceiveTime;
      if (timeSinceLastReceive > this.connectionTimeout) {
        console.warn('[TCPManager] 连接超时');
        this.isConnected = false;
        this.carConnected = false;
        this.notifyConnectionChange(false, '连接超时');
        this.startReconnect();
      }
    }
  }

  /**
   * 启动重连
   */
  startReconnect() {
    this.stopReconnect();

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[TCPManager] 达到最大重连次数');
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    console.log('[TCPManager] 将在', delay, 'ms后重连');

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.connectToBackend();
    }, delay);
  }

  /**
   * 停止重连
   */
  stopReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * 注册消息回调
   */
  onMessage(callback) {
    if (typeof callback === 'function') {
      this.messageCallbacks.push(callback);
    }
  }

  /**
   * 移除消息回调
   */
  offMessage(callback) {
    const index = this.messageCallbacks.indexOf(callback);
    if (index > -1) {
      this.messageCallbacks.splice(index, 1);
    }
  }

  /**
   * 注册连接状态回调
   */
  onConnectionChange(callback) {
    if (typeof callback === 'function') {
      this.connectionCallbacks.push(callback);
    }
  }

  /**
   * 移除连接状态回调
   */
  offConnectionChange(callback) {
    const index = this.connectionCallbacks.indexOf(callback);
    if (index > -1) {
      this.connectionCallbacks.splice(index, 1);
    }
  }

  /**
   * 通知连接状态变化
   */
  notifyConnectionChange(connected, message, data) {
    this.connectionCallbacks.forEach(callback => {
      try {
        callback(connected, message, data);
      } catch (error) {
        console.error('[TCPManager] 状态回调执行失败:', error);
      }
    });
  }

  /**
   * 获取连接状态
   */
  getConnectionStatus() {
    return {
      connected: this.isConnected,
      connecting: this.isConnecting,
      carConnected: this.carConnected,
      backendIp: this.backendConfig.ip,
      backendPort: this.backendConfig.port,
      carIp: this.carConfig.ip,
      carPort: this.carConfig.port,
      deviceId: this.carConfig.deviceId,
      reconnectAttempts: this.reconnectAttempts
    };
  }
}

// 创建单例
const tcpNetworkManager = new TCPNetworkManager();

module.exports = tcpNetworkManager;
