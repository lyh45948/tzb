/**
 * UDP后端网络管理器
 * 使用UDP与Python后端通信
 */
const errorHandler = require('./error-handler');

class UDPBackendManager {
  constructor() {
    this.udp = null;
    this.isConnected = false;
    this.receiveBuffer = '';
    this.messageCallbacks = [];
    this.connectionCallbacks = [];
    this.heartbeatTimer = null;
    this.lastReceiveTime = 0;

    // 连接验证相关
    this.connectionVerified = false;
    this.connectionTimer = null;
    this.connectionAttempts = 0;
    this.maxConnectionAttempts = 3;

    // 后端配置 (默认IP)
    this.backendConfig = {
      ip: '192.168.31.140',
      port: 8888  // 与后端 TCP_PORT 配置一致
    };

    // 小车配置
    this.carConfig = {
      ip: '',
      port: 7788,
      deviceId: ''
    };

    // 小车连接状态
    this.carConnected = false;

    // 演示模式
    this.demoMode = false;
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
      wx.setStorageSync('udp_backend_config', {
        backend: this.backendConfig,
        car: this.carConfig
      });
    } catch (error) {
      console.error('[UDPBackend] 保存配置失败:', error);
    }
  }

  /**
   * 加载配置
   */
  loadConfig() {
    try {
      const savedConfig = wx.getStorageSync('udp_backend_config');
      if (savedConfig) {
        this.backendConfig = { ...this.backendConfig, ...savedConfig.backend };
        this.carConfig = { ...this.carConfig, ...savedConfig.car };
      }
    } catch (error) {
      console.error('[UDPBackend] 加载配置失败:', error);
    }
  }

  /**
   * 连接到后端
   */
  connect() {
    if (!this.backendConfig.ip) {
      console.error('[UDPBackend] 后端IP未配置');
      this.notifyConnectionChange(false, '后端IP未配置');
      return false;
    }

    try {
      // 关闭旧连接
      if (this.udp) {
        try {
          this.udp.offMessage();
          this.udp.close();
        } catch (e) {}
      }

      // 清除之前的连接计时器
      this.clearConnectionTimer();

      // 创建UDP Socket
      this.udp = wx.createUDPSocket();

      // 监听消息
      this.udp.onMessage(this.handleMessage.bind(this));

      // 监听错误
      this.udp.onError((error) => {
        console.error('[UDPBackend] UDP错误:', error);
        this.isConnected = false;
        this.connectionVerified = false;
        this.clearConnectionTimer();
        this.notifyConnectionChange(false, '连接错误');
      });

      // 监听关闭
      this.udp.onClose(() => {
        console.log('[UDPBackend] UDP已关闭');
        this.isConnected = false;
        this.connectionVerified = false;
        this.stopHeartbeat();
        this.clearConnectionTimer();
        this.notifyConnectionChange(false, '连接已关闭');
      });

      // 绑定本地端口
      this.udp.bind();
      this.lastReceiveTime = Date.now();

      // 标记为"正在连接"状态（不是已连接）
      this.isConnected = false;
      this.connectionVerified = false;
      this.connectionAttempts = 0;

      console.log('[UDPBackend] UDP Socket已创建，正在验证连接...');
      this.notifyConnectionChange(false, '正在连接后端...');

      // 发送ping消息验证连接
      this.sendPing();

      // 设置连接超时 (3秒)
      this.connectionTimer = setTimeout(() => {
        if (!this.connectionVerified) {
          console.error('[UDPBackend] 连接超时，后端无响应');
          this.handleConnectionTimeout();
        }
      }, 3000);

      return true;
    } catch (error) {
      console.error('[UDPBackend] 连接失败:', error);
      this.notifyConnectionChange(false, '连接失败');
      return false;
    }
  }

  /**
   * 发送ping消息
   */
  sendPing() {
    if (!this.udp) return;

    this.connectionAttempts++;
    console.log(`[UDPBackend] 发送ping (尝试 ${this.connectionAttempts}/${this.maxConnectionAttempts})`);

    try {
      const pingMsg = JSON.stringify({ type: 'ping' }) + '\n';
      this.udp.send({
        address: this.backendConfig.ip,
        port: this.backendConfig.port,
        message: pingMsg
      });
    } catch (error) {
      console.error('[UDPBackend] 发送ping失败:', error);
    }
  }

  /**
   * 处理pong响应
   */
  handlePong(message) {
    console.log('[UDPBackend] 收到pong响应，连接验证成功');
    this.connectionVerified = true;
    this.clearConnectionTimer();
    this.isConnected = true;
    this.connectionAttempts = 0;

    // 启动心跳
    this.startHeartbeat();

    this.notifyConnectionChange(true, '已连接到后端');
  }

  /**
   * 处理连接超时
   */
  handleConnectionTimeout() {
    this.clearConnectionTimer();

    // 如果还有重试次数，则重试
    if (this.connectionAttempts < this.maxConnectionAttempts) {
      console.log('[UDPBackend] 重试连接...');
      this.sendPing();

      // 重新设置超时
      this.connectionTimer = setTimeout(() => {
        if (!this.connectionVerified) {
          this.handleConnectionTimeout();
        }
      }, 3000);
    } else {
      // 超过最大重试次数，连接失败
      console.error('[UDPBackend] 连接失败：后端无响应');
      this.isConnected = false;
      this.connectionVerified = false;
      this.notifyConnectionChange(false, '连接超时，请检查后端是否运行');
    }
  }

  /**
   * 清除连接计时器
   */
  clearConnectionTimer() {
    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer);
      this.connectionTimer = null;
    }
  }

  /**
   * 连接到小车 (通过后端)
   */
  connectToCar(carIp, carPort, deviceId) {
    if (!this.isConnected) {
      console.error('[UDPBackend] 未连接到后端');
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

    console.log('[UDPBackend] 请求连接小车:', message);
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
   * 设置演示模式
   */
  setDemoMode(enabled, deviceId) {
    if (!this.isConnected) {
      console.error('[UDPBackend] 未连接到后端');
      return false;
    }

    const message = {
      type: 'demo_mode',
      enabled: enabled,
      deviceId: deviceId || 'demo_car'
    };

    this.demoMode = enabled;
    console.log('[UDPBackend] 设置演示模式:', enabled);
    return this.send(message);
  }

  /**
   * 断开所有连接
   */
  disconnect() {
    console.log('[UDPBackend] 断开连接');

    this.stopHeartbeat();
    this.clearConnectionTimer();

    if (this.udp) {
      try {
        this.udp.offMessage();
        this.udp.close();
      } catch (e) {}
      this.udp = null;
    }

    this.isConnected = false;
    this.connectionVerified = false;
    this.carConnected = false;
    this.notifyConnectionChange(false, '已断开');
  }

  /**
   * 发送数据
   */
  send(message) {
    // 只检查udp是否存在，允许在连接验证阶段发送
    if (!this.udp) {
      console.warn('[UDPBackend] UDP未初始化，无法发送');
      return false;
    }

    try {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
      const data = messageStr + '\n';

      this.udp.send({
        address: this.backendConfig.ip,
        port: this.backendConfig.port,
        message: data
      });
      return true;
    } catch (error) {
      console.error('[UDPBackend] 发送失败:', error);
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
   * 计算灌溉水量
   */
  calculateIrrigation(sensorData) {
    const message = {
      type: 'irrigation_calc',
      deviceId: this.carConfig.deviceId || 'car_001',
      data: sensorData
    };
    console.log('[UDPBackend] 请求灌溉计算:', sensorData);
    return this.send(message);
  }

  /**
   * 执行灌溉
   */
  executeIrrigation(waterAmount, duration, sensorData, factors) {
    const message = {
      type: 'irrigation_execute',
      deviceId: this.carConfig.deviceId || 'car_001',
      data: {
        waterAmount: waterAmount,
        duration: duration,
        triggerType: 'manual',
        sensorData: sensorData,
        factors: factors
      }
    };
    console.log('[UDPBackend] 执行灌溉:', waterAmount, 'ml');
    return this.send(message);
  }

  /**
   * 查询灌溉历史
   */
  queryIrrigationHistory(limit = 10) {
    const message = {
      type: 'irrigation_query',
      deviceId: this.carConfig.deviceId || 'car_001',
      limit: limit
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
          console.error('[UDPBackend] JSON解析失败:', e, line);
        }
      }
    } catch (error) {
      console.error('[UDPBackend] 处理消息失败:', error);
    }
  }

  /**
   * 处理解析后的消息
   */
  processMessage(message) {
    const msgType = message.type;

    switch (msgType) {
      case 'pong':
        // 连接验证响应 - 最高优先级
        this.handlePong(message);
        break;

      case 'connect_result':
        // 连接小车结果
        if (message.success) {
          this.carConnected = true;
          console.log('[UDPBackend] 小车连接成功:', message.message);
        } else {
          this.carConnected = false;
          console.error('[UDPBackend] 小车连接失败:', message.message);
        }
        this.notifyConnectionChange(this.isConnected, message.message, message);
        break;

      case 'disconnect_result':
        this.carConnected = false;
        console.log('[UDPBackend] 小车已断开');
        break;

      case 'realtime':
        // 实时数据
        console.log('[UDPBackend] 收到realtime数据:', message.data);
        this.notifyMessageCallbacks(message.data);
        break;

      case 'query_result':
        // 查询结果
        this.notifyMessageCallbacks(message);
        break;

      case 'demo_mode_result':
        // 演示模式结果
        if (message.success) {
          this.demoMode = message.enabled;
          this.carConnected = message.enabled; // 演示模式下也认为已连接
          console.log('[UDPBackend] 演示模式:', message.enabled ? '已开启' : '已关闭');
        } else {
          console.error('[UDPBackend] 演示模式设置失败:', message.message);
        }
        this.notifyConnectionChange(this.isConnected, message.message, message);
        break;

      case 'status':
        // 状态消息
        console.log('[UDPBackend] 状态:', message.message);
        break;

      case 'irrigation_calc_result':
        // 灌溉计算结果
        console.log('[UDPBackend] 灌溉计算结果:', message.data);
        this.notifyMessageCallbacks(message);
        break;

      case 'irrigation_status':
        // 灌溉状态更新
        console.log('[UDPBackend] 灌溉状态:', message.data);
        this.notifyMessageCallbacks(message);
        break;

      case 'irrigation_query_result':
        // 灌溉历史查询结果
        console.log('[UDPBackend] 灌溉历史:', message.data);
        this.notifyMessageCallbacks(message);
        break;

      case 'smart_light_status':
        // 智能光照状态
        console.log('[UDPBackend] 智能光照状态:', message.data);
        this.notifyMessageCallbacks(message);
        break;

      case 'error':
        console.error('[UDPBackend] 服务器错误:', message.message);
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
        console.error('[UDPBackend] 消息回调执行失败:', error);
      }
    });
  }

  /**
   * 启动心跳
   */
  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected && this.carConnected) {
        // 发送心跳保持连接
        this.send({ type: 'heartbeat' });
      }
    }, 5000);
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
        console.error('[UDPBackend] 状态回调执行失败:', error);
      }
    });
  }

  /**
   * 获取连接状态
   */
  getConnectionStatus() {
    return {
      connected: this.isConnected,
      carConnected: this.carConnected,
      demoMode: this.demoMode,
      backendIp: this.backendConfig.ip,
      backendPort: this.backendConfig.port,
      carIp: this.carConfig.ip,
      carPort: this.carConfig.port,
      deviceId: this.carConfig.deviceId
    };
  }
}

// 创建单例
const udpBackendManager = new UDPBackendManager();

module.exports = udpBackendManager;
