/**
 * 网络管理器 - 实现断线重连、心跳保活、连接状态管理
 */
const errorHandler = require('./error-handler');

class NetworkManager {
  constructor() {
    this.udp = null;
    this.isConnected = false;
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000;
    this.heartbeatTimer = null;
    this.connectionVerifyTimer = null; // 新增：连接验证定时器
    this.lastHeartbeatTime = 0;
    this.lastReceiveTime = 0;
    this.heartbeatInterval = 3000; // 3秒心跳
    this.connectionTimeout = 10000; // 10秒无响应视为断线
    this.connectionVerifyTimeout = 5000; // 5秒连接验证超时
    this.messageCallbacks = [];
    this.connectionCallbacks = [];
    this.config = {
      ip: '',
      port: 7788
    };
  }

  /**
   * 初始化网络管理器
   */
  init(config) {
    if (config) {
      this.config = { ...this.config, ...config };
    }
    
    // 尝试从本地存储加载配置
    this.loadConfig();
  }

  /**
   * 从本地存储加载配置
   */
  loadConfig() {
    try {
      const savedConfig = wx.getStorageSync('network_config');
      if (savedConfig) {
        this.config = { ...this.config, ...savedConfig };
        console.log('[NetworkManager] 已加载保存的配置:', this.config);
      }
    } catch (error) {
      console.error('[NetworkManager] 加载配置失败:', error);
    }
  }

  /**
   * 保存配置到本地存储
   */
  saveConfig(config) {
    try {
      // 停止所有定时器
      this.stopHeartbeat();
      this.stopReconnect();
      this.stopConnectionVerify();
      
      // 关闭现有连接
      if (this.udp) {
        try {
          this.udp.offMessage();
          this.udp.offError();
          this.udp.offClose();
          this.udp.close();
          this.udp = null;
        } catch (e) {
          console.error('[NetworkManager] 关旧连接失败:', e);
        }
      }
      
      // 重置连接状态
      this.isConnected = false;
      this.isConnecting = false;
      this.reconnectAttempts = 0; // 重置重连次数
      
      // 更新配置
      this.config = { ...this.config, ...config };
      wx.setStorageSync('network_config', this.config);
      console.log('[NetworkManager] 配置已更新:', this.config);
      
      // 通知配置已更新
      this.notifyConnectionChange(false, '配置已更新，准备重新连接');
      
      // 自动尝试新配置连接（延迟500ms，确保配置保存完成）
      setTimeout(() => {
        if (this.config.ip) {
          console.log('[NetworkManager] 自动尝试连接新配置');
          this.connect();
        }
      }, 500);
    } catch (error) {
      console.error('[NetworkManager] 保存配置失败:', error);
    }
  }

  /**
   * 建立连接
   */
  async connect() {
    if (this.isConnecting) {
      console.log('[NetworkManager] 正在连接中，请稍候...');
      return false;
    }

    if (!this.config.ip) {
      console.error('[NetworkManager] IP地址未配置');
      this.notifyConnectionChange(false, 'IP地址未配置');
      return false;
    }

    this.isConnecting = true;
      this.notifyConnectionChange(false, '正在验证连接...');

    try {
      // 创建UDP Socket
      this.udp = wx.createUDPSocket();
      this.udp.bind();

      // 监听消息
      this.udp.onMessage(this.handleMessage.bind(this));

      // 监听错误
      this.udp.onError(this.handleError.bind(this));

      // 监听关闭
      this.udp.onClose(() => {
        console.log('[NetworkManager] UDP连接已关闭');
        this.isConnected = false;
        this.isConnecting = false;
        this.stopConnectionVerify(); // 停止连接验证
        this.notifyConnectionChange(false, '连接已关闭');
        this.startHeartbeat(); // 继续心跳，等待重连
      });

      // 发送心跳包测试连接
      this.sendHeartbeat();
      
      // 启动连接验证定时器（5秒超时）
      this.startConnectionVerify();

      console.log('[NetworkManager] 正在验证连接:', this.config.ip);
      return true;
    } catch (error) {
      this.isConnecting = false;
      this.isConnected = false;
      console.error('[NetworkManager] 连接失败:', error);
      this.notifyConnectionChange(false, '连接失败: ' + error.message);
      
      // 启动重连机制
      this.startReconnect();
      return false;
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    console.log('[NetworkManager] 请求断开连接');
    
    // 停止所有定时器
    this.stopHeartbeat();
    this.stopReconnect();
    this.stopConnectionVerify();
    
    // 关闭socket
    if (this.udp) {
      try {
        this.udp.offMessage();
        this.udp.offError();
        this.udp.offClose();
        this.udp.close();
        console.log('[NetworkManager] Socket已关闭');
      } catch (error) {
        console.error('[NetworkManager] 关闭连接失败:', error);
      }
      this.udp = null;
    }

    // 重置所有连接状态
    this.isConnected = false;
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    
    // 通知状态变化
    this.notifyConnectionChange(false, '已断开');
  }

  /**
   * 发送数据
   */
  send(message) {
    if (!this.isConnected || !this.udp) {
      console.warn('[NetworkManager] 未连接，无法发送数据');
      return false;
    }

    try {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
      this.udp.send({
        address: this.config.ip,
        port: this.config.port,
        message: messageStr
      });
      return true;
    } catch (error) {
      console.error('[NetworkManager] 发送数据失败:', error);
      this.handleError(error);
      return false;
    }
  }

  /**
   * 处理接收到的消息（修改版：只有在验证期间收到消息才确认连接成功）
   */
  handleMessage(res) {
    this.lastReceiveTime = Date.now();
    
    // 如果在连接验证期间收到任何消息，说明设备真正存在，确认连接成功
    if (this.isConnecting) {
      console.log('[NetworkManager] 收到设备响应，连接验证成功');
      this.isConnecting = false;
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.stopConnectionVerify(); // 停止连接验证
      this.notifyConnectionChange(true, '已连接');
    }
    
    if (res.remoteInfo.size > 0) {
      try {
        let unit8Arr = new Uint8Array(res.message);
        let encodedString = String.fromCharCode.apply(null, unit8Arr);
        let decodedString = decodeURIComponent(escape(encodedString));
        let json = JSON.parse(decodedString);
        
        // 触发消息回调
        this.messageCallbacks.forEach(callback => {
          try {
            callback(json);
          } catch (error) {
            console.error('[NetworkManager] 消息回调执行失败:', error);
          }
        });
      } catch (error) {
        console.error('[NetworkManager] 解析消息失败:', error);
        errorHandler.handle('parse_error', '消息解析失败: ' + error.message);
      }
    }
  }

  /**
   * 处理错误
   */
  handleError(error) {
    console.error('[NetworkManager] 发生错误:', error);
    errorHandler.handle('network_error', '网络错误: ' + error.message);
    
    // 如果连接失败，启动重连
    if (this.isConnected) {
      this.isConnected = false;
      this.stopConnectionVerify(); // 停止连接验证
      this.notifyConnectionChange(false, '连接异常');
      this.startReconnect();
    }
  }

  /**
   * 启动心跳
   */
  startHeartbeat() {
    this.stopHeartbeat();
    
    this.heartbeatTimer = setInterval(() => {
      this.sendHeartbeat();
      this.checkConnectionTimeout();
    }, this.heartbeatInterval);
    
    console.log('[NetworkManager] 心跳已启动, 间隔:', this.heartbeatInterval, 'ms');
  }

  /**
   * 停止心跳
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
      console.log('[NetworkManager] 心跳已停止');
    }
  }

  /**
   * 发送心跳
   */
  sendHeartbeat() {
    if (!this.udp) return; // 即使未连接也发送，用于测试连接性
    
    try {
      this.udp.send({
        address: this.config.ip,
        port: this.config.port,
        message: JSON.stringify({ cmd: 'ping', timestamp: Date.now() })
      });
      this.lastHeartbeatTime = Date.now();
    } catch (error) {
      console.error('[NetworkManager] 发送心跳失败:', error);
    }
  }

  /**
   * 检查连接超时
   */
  checkConnectionTimeout() {
    const now = Date.now();
    const timeSinceLastReceive = now - this.lastReceiveTime;
    
    // 只有在真正连接后才检查超时
    if (this.isConnected && !this.isConnecting) {
      if (timeSinceLastReceive > this.connectionTimeout) {
        console.warn('[NetworkManager] 连接超时, 上次接收时间:', timeSinceLastReceive, 'ms前');
        
        if (this.isConnected) {
          this.isConnected = false;
          this.notifyConnectionChange(false, '连接超时');
          this.startReconnect();
        }
      }
    }
  }

  /**
   * 启动连接验证（新增：5秒超时机制）
   */
  startConnectionVerify() {
    this.stopConnectionVerify();
    
    this.connectionVerifyTimer = setTimeout(() => {
      // 如果5秒后仍在连接状态（即未收到任何消息），则判定连接失败
      if (this.isConnecting) {
        console.warn('[NetworkManager] 连接验证超时, 设备未响应');
        this.isConnecting = false;
        this.isConnected = false;
        this.notifyConnectionChange(false, '设备未响应，请检查IP配置');
        
        // 关闭socket
        try {
          if (this.udp) {
            this.udp.offMessage();
            this.udp.offError();
            this.udp.offClose();
            this.udp.close();
            this.udp = null;
          }
        } catch (e) {
          console.error('[NetworkManager] 关闭socket失败:', e);
        }
        
        // 启动重连机制
        this.startReconnect();
      }
    }, this.connectionVerifyTimeout);
    
    console.log('[NetworkManager] 连接验证定时器已启动, 超时:', this.connectionVerifyTimeout, 'ms');
  }

  /**
   * 停止连接验证（新增）
   */
  stopConnectionVerify() {
    if (this.connectionVerifyTimer) {
      clearTimeout(this.connectionVerifyTimer);
      this.connectionVerifyTimer = null;
      console.log('[NetworkManager] 连接验证定时器已停止');
    }
  }

  /**
   * 启动重连
   */
  startReconnect() {
    this.stopReconnect();
    
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[NetworkManager] 达到最大重连次数');
      this.notifyConnectionChange(false, '重连失败，请检查网络');
      return;
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    console.log('[NetworkManager] 将在', delay, 'ms后尝试第', this.reconnectAttempts + 1, '次重连');
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
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
   * 注册连接状态变化回调
   */
  onConnectionChange(callback) {
    if (typeof callback === 'function') {
      this.connectionCallbacks.push(callback);
    }
  }

  /**
   * 移除连接状态变化回调
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
  notifyConnectionChange(connected, message) {
    this.connectionCallbacks.forEach(callback => {
      try {
        callback(connected, message);
      } catch (error) {
        console.error('[NetworkManager] 连接状态回调执行失败:', error);
      }
    });
  }

  /**
   * 获取当前连接状态
   */
  getConnectionStatus() {
    return {
      connected: this.isConnected,
      connecting: this.isConnecting,
      ip: this.config.ip,
      port: this.config.port,
      reconnectAttempts: this.reconnectAttempts,
      lastReceiveTime: this.lastReceiveTime
    };
  }
}

// 创建单例
const networkManager = new NetworkManager();

module.exports = networkManager;

