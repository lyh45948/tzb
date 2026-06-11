/**
 * 统一错误处理器
 */

class ErrorHandler {
  constructor() {
    this.errorCallbacks = [];
    this.errorHistory = [];
    this.maxHistorySize = 50;
    this.logLevel = 'info'; // debug, info, warn, error
  }

  /**
   * 初始化错误处理器
   */
  init(config = {}) {
    if (config.logLevel) {
      this.logLevel = config.logLevel;
    }

    // 监听小程序错误
    wx.onError(this.handleAppError.bind(this));
    
    // 监听未处理的Promise错误
    wx.onUnhandledRejection(this.handlePromiseRejection.bind(this));
    
    console.log('[ErrorHandler] 错误处理器已初始化, 日志级别:', this.logLevel);
  }

  /**
   * 处理应用错误
   */
  handleAppError(error) {
    console.error('[ErrorHandler] 应用错误:', error);
    this.handle('app_error', error.message || error, error);
  }

  /**
   * 处理Promise拒绝
   */
  handlePromiseRejection(res) {
    console.error('[ErrorHandler] Promise拒绝:', res);
    this.handle('promise_rejection', res.reason, res);
  }

  /**
   * 统一错误处理
   * @param {string} type - 错误类型
   * @param {string} message - 错误信息
   * @param {object} detail - 错误详情
   */
  handle(type, message, detail = null) {
    const errorInfo = {
      type,
      message,
      detail,
      timestamp: Date.now(),
      level: this.getLevelByType(type)
    };

    // 记录到历史
    this.addToHistory(errorInfo);

    // 根据日志级别输出
    this.log(errorInfo);

    // 触发回调
    this.notifyCallbacks(errorInfo);

    // 保存到本地存储
    this.saveToStorage(errorInfo);
  }

  /**
   * 根据错误类型获取日志级别
   */
  getLevelByType(type) {
    const levelMap = {
      'network_error': 'error',
      'network_timeout': 'warn',
      'parse_error': 'error',
      'send_error': 'warn',
      'receive_error': 'warn',
      'app_error': 'error',
      'promise_rejection': 'error',
      'config_error': 'error',
      'validation_error': 'warn',
      'permission_error': 'error'
    };
    return levelMap[type] || 'info';
  }

  /**
   * 添加到历史记录
   */
  addToHistory(errorInfo) {
    this.errorHistory.unshift(errorInfo);
    
    if (this.errorHistory.length > this.maxHistorySize) {
      this.errorHistory.pop();
    }
  }

  /**
   * 根据日志级别输出
   */
  log(errorInfo) {
    const { level, type, message, timestamp } = errorInfo;
    const timeStr = new Date(timestamp).toLocaleTimeString();
    
    const logMessage = `[${timeStr}] [${type}] ${message}`;

    switch (level) {
      case 'debug':
        console.log('[ErrorHandler]', logMessage);
        break;
      case 'info':
        console.info('[ErrorHandler]', logMessage);
        break;
      case 'warn':
        console.warn('[ErrorHandler]', logMessage);
        break;
      case 'error':
        console.error('[ErrorHandler]', logMessage);
        if (errorInfo.detail) {
          console.error('[ErrorHandler] 详情:', errorInfo.detail);
        }
        break;
    }
  }

  /**
   * 触发错误回调
   */
  notifyCallbacks(errorInfo) {
    this.errorCallbacks.forEach(callback => {
      try {
        callback(errorInfo);
      } catch (error) {
        console.error('[ErrorHandler] 错误回调执行失败:', error);
      }
    });
  }

  /**
   * 保存到本地存储
   */
  saveToStorage(errorInfo) {
    try {
      const savedErrors = wx.getStorageSync('error_log') || [];
      savedErrors.unshift(errorInfo);
      
      // 只保留最近100条
      if (savedErrors.length > 100) {
        savedErrors.pop();
      }
      
      wx.setStorageSync('error_log', savedErrors);
    } catch (error) {
      console.error('[ErrorHandler] 保存错误日志失败:', error);
    }
  }

  /**
   * 注册错误回调
   */
  onError(callback) {
    if (typeof callback === 'function') {
      this.errorCallbacks.push(callback);
    }
  }

  /**
   * 移除错误回调
   */
  offError(callback) {
    const index = this.errorCallbacks.indexOf(callback);
    if (index > -1) {
      this.errorCallbacks.splice(index, 1);
    }
  }

  /**
   * 获取错误历史
   */
  getErrorHistory() {
    return this.errorHistory;
  }

  /**
   * 清除错误历史
   */
  clearErrorHistory() {
    this.errorHistory = [];
    try {
      wx.removeStorageSync('error_log');
    } catch (error) {
      console.error('[ErrorHandler] 清除错误历史失败:', error);
    }
  }

  /**
   * 获取错误统计
   */
  getErrorStats() {
    const stats = {};
    
    this.errorHistory.forEach(error => {
      if (!stats[error.type]) {
        stats[error.type] = {
          count: 0,
          messages: []
        };
      }
      
      stats[error.type].count++;
      
      // 只保留每类错误的前5条消息
      if (stats[error.type].messages.length < 5) {
        stats[error.type].messages.push(error.message);
      }
    });
    
    return stats;
  }

  /**
   * 导出错误日志
   */
  exportErrors() {
    const errors = wx.getStorageSync('error_log') || [];
    return JSON.stringify(errors, null, 2);
  }

  /**
   * 清除所有错误
   */
  clearAll() {
    this.errorHistory = [];
    try {
      wx.removeStorageSync('error_log');
      console.log('[ErrorHandler] 已清除所有错误日志');
    } catch (error) {
      console.error('[ErrorHandler] 清除错误日志失败:', error);
    }
  }
}

// 创建单例
const errorHandler = new ErrorHandler();

module.exports = errorHandler;

