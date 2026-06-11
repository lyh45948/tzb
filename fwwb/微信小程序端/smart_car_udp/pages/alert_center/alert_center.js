// pages/alert_center/alert_center.js
const udpBackendManager = require('../../utils/udp-backend-manager');
const app = getApp();

Page({
  data: {
    alerts: [],
    historyAlerts: [],
    stats: {
      warning: 0,
      danger: 0,
      critical: 0,
      total: 0
    },
    collapsedPanels: []
  },

  alertTypeNames: {
    'temperature': '温度',
    'humidity': '湿度',
    'co2': 'CO2浓度',
    'smoke': '烟雾',
    'co': '一氧化碳',
    'flame': '火焰',
    'gas_leak': '燃气泄漏',
    'agv_obstacle': 'AGV障碍',
    'goods_count': '货物计数'
  },

  onLoad() {
    this.initBackendMessageListener();
    this.startRefreshTimer();
  },

  onShow() {
    this.updateConnectionStatus();
  },

  onUnload() {
    if (this._onBackendMessage) {
      udpBackendManager.offMessage(this._onBackendMessage);
    }
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
  },

  onPullDownRefresh() {
    this.refreshAlerts();
    setTimeout(() => {
      wx.stopPullDownRefresh();
    }, 500);
  },

  initBackendMessageListener() {
    this._onBackendMessage = (data) => {
      if (data && data.env && data.env.factoryAlert) {
        const factoryAlert = data.env.factoryAlert;
        const alertLevel = factoryAlert.level || 0;
        const alertType = factoryAlert.type || 0;
        const alertCount = factoryAlert.count || 0;

        // 更新本地警报状态
        if (alertLevel > 0) {
          this.addAlertFromData(data.env);
        }

        this.setData({
          currentAlertLevel: alertLevel,
          currentAlertType: alertType,
          currentAlertCount: alertCount
        });
      }
    };

    udpBackendManager.onMessage(this._onBackendMessage);
  },

  updateConnectionStatus() {
    const status = udpBackendManager.getConnectionStatus();
    this.setData({
      connected: status.connected || status.demoMode || false
    });
  },

  startRefreshTimer() {
    this.refreshTimer = setInterval(() => {
      this.refreshAlerts();
    }, 5000);
  },

  refreshAlerts() {
    // 模拟刷新警报（实际应从后端API获取）
    // 这里只是演示，实际项目中应该调用后端API
  },

  addAlertFromData(env) {
    const factoryAlert = env.factoryAlert || {};
    const alerts = this.data.alerts;

    // 添加新的高优先级警报
    if (factoryAlert.flameDetected) {
      this.addAlert({
        id: Date.now(),
        alert_type: 'flame',
        severity: 'critical',
        message: '检测到火焰！请立即检查！',
        created_at: new Date().toLocaleTimeString()
      });
    }

    if (factoryAlert.gasLeakDetected) {
      this.addAlert({
        id: Date.now() + 1,
        alert_type: 'gas_leak',
        severity: 'critical',
        message: '检测到燃气泄漏！请立即检查！',
        created_at: new Date().toLocaleTimeString()
      });
    }

    if (factoryAlert.smokeAlert) {
      this.addAlert({
        id: Date.now() + 2,
        alert_type: 'smoke',
        severity: 'danger',
        message: `烟雾浓度超标: ${env.smoke || 0}`,
        created_at: new Date().toLocaleTimeString()
      });
    }

    if (factoryAlert.coAlert) {
      this.addAlert({
        id: Date.now() + 3,
        alert_type: 'co',
        severity: 'danger',
        message: `一氧化碳浓度超标: ${env.co || 0} ppm`,
        created_at: new Date().toLocaleTimeString()
      });
    }
  },

  addAlert(alert) {
    const alerts = this.data.alerts;
    // 避免重复添加
    const exists = alerts.some(a => a.alert_type === alert.alert_type && a.severity === alert.severity);
    if (!exists) {
      alerts.unshift(alert);
      this.setData({ alerts: alerts.slice(0, 20) }); // 最多保留20条
      this.updateStats();
    }
  },

  updateStats() {
    const alerts = this.data.alerts;
    const stats = {
      warning: alerts.filter(a => a.severity === 'warning').length,
      danger: alerts.filter(a => a.severity === 'danger').length,
      critical: alerts.filter(a => a.severity === 'critical').length,
      total: alerts.length
    };
    this.setData({ stats });
  },

  acknowledgeAlert(e) {
    const alertId = e.currentTarget.dataset.id;
    const alerts = this.data.alerts.map(a => {
      if (a.id === alertId) {
        return { ...a, acknowledged: true };
      }
      return a;
    });
    this.setData({ alerts });
    this.updateStats();

    wx.showToast({
      title: '警报已确认',
      icon: 'success'
    });
  },

  onCollapseChange(e) {
    this.setData({
      collapsedPanels: e.detail.value
    });
  },

  getAlertIcon(severity) {
    const icons = {
      'warning': 'info',
      'danger': 'warning',
      'critical': 'warning'
    };
    return icons[severity] || 'info';
  },

  getAlertColor(severity) {
    const colors = {
      'warning': '#ffc107',
      'danger': '#ff9800',
      'critical': '#ee0a24'
    };
    return colors[severity] || '#999';
  },

  getAlertTypeName(type) {
    return this.alertTypeNames[type] || type;
  },

  getSeverityName(severity) {
    const names = {
      'warning': '警告',
      'danger': '危险',
      'critical': '紧急'
    };
    return names[severity] || severity;
  },

  getTagType(severity) {
    const types = {
      'warning': 'warning',
      'danger': 'danger',
      'critical': 'danger'
    };
    return types[severity] || 'default';
  }
});