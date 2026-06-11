// error-handler.js - 错误处理模块

// 错误类型定义
const ErrorTypes = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  DEVICE_ERROR: 'DEVICE_ERROR',
  SENSOR_ERROR: 'SENSOR_ERROR',
  CONFIG_ERROR: 'CONFIG_ERROR',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR'
};

// 错误消息映射
const ErrorMessages = {
  NETWORK_ERROR: '网络连接错误',
  DEVICE_ERROR: '设备通信错误',
  SENSOR_ERROR: '传感器数据错误',
  CONFIG_ERROR: '配置加载错误',
  UNKNOWN_ERROR: '未知错误'
};

// 错误回调
let errorCallback = null;

// 设置错误回调
function setErrorCallback(callback) {
  errorCallback = callback;
}

// 处理错误
function handleError(type, message, detail) {
  const error = {
    type: type || ErrorTypes.UNKNOWN_ERROR,
    message: message || ErrorMessages[type] || '未知错误',
    detail: detail || '',
    timestamp: new Date().toISOString()
  };

  console.error('错误:', error);

  // 调用回调
  if (errorCallback) {
    errorCallback(error);
  }

  // 显示提示
  wx.showToast({
    title: error.message,
    icon: 'none',
    duration: 2000
  });

  return error;
}

// 处理网络错误
function handleNetworkError(message) {
  return handleError(ErrorTypes.NETWORK_ERROR, '网络连接失败', message);
}

// 处理设备错误
function handleDeviceError(message) {
  return handleError(ErrorTypes.DEVICE_ERROR, '设备响应异常', message);
}

// 处理传感器错误
function handleSensorError(message) {
  return handleError(ErrorTypes.SENSOR_ERROR, '传感器数据异常', message);
}

// 记录日志
function log(level, message, data) {
  const logEntry = {
    level,
    message,
    data,
    timestamp: new Date().toISOString()
  };

  console.log(`[${level}] ${message}`, data || '');

  return logEntry;
}

module.exports = {
  ErrorTypes,
  ErrorMessages,
  setErrorCallback,
  handleError,
  handleNetworkError,
  handleDeviceError,
  handleSensorError,
  log
};
