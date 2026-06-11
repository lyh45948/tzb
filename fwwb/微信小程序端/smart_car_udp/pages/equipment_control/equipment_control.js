// pages/equipment_control/equipment_control.js
const udpBackendManager = require('../../utils/udp-backend-manager');
const app = getApp();

Page({
  data: {
    deviceStatus: {
      fan: false,
      led: false,
      buzzer: false
    },
    smartLightEnabled: false,
    brightness: 50,
    pirDetected: false,
    flameDetected: false,
    gasLeakDetected: false,
    agvDistance: 999,
    agvObstacle: false
  },

  onLoad() {
    this.initBackendMessageListener();
  },

  onShow() {
    this.updateConnectionStatus();
  },

  onUnload() {
    if (this._onBackendMessage) {
      udpBackendManager.offMessage(this._onBackendMessage);
    }
  },

  initBackendMessageListener() {
    this._onBackendMessage = (data) => {
      if (data && data.env) {
        const env = data.env;
        const factoryAlert = env.factoryAlert || {};

        this.setData({
          pirDetected: factoryAlert.pirDetected || false,
          flameDetected: factoryAlert.flameDetected || false,
          gasLeakDetected: factoryAlert.gasLeakDetected || false,
          agvDistance: factoryAlert.agvDistance || this.data.agvDistance,
          agvObstacle: factoryAlert.agvObstacleFlag || false,
          deviceStatus: {
            fan: env.fan || false,
            led: env.led || false,
            buzzer: env.buzzer || false
          }
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

  onFanChange(e) {
    this.toggleDevice('fan', e.detail);
  },

  onLedChange(e) {
    this.toggleDevice('led', e.detail);
  },

  onBuzzerChange(e) {
    this.toggleDevice('buzzer', e.detail);
  },

  onSmartLightChange(e) {
    const enabled = e.detail;
    this.setData({ smartLightEnabled: enabled });

    const command = {
      smartLight: {
        mode: enabled ? 'auto' : 'manual',
        brightness: enabled ? this.data.brightness : 0
      }
    };

    if (this.data.connected) {
      udpBackendManager.sendControl(command);
    }
  },

  onBrightnessChange(e) {
    const brightness = e.detail.value;
    this.setData({ brightness });

    const command = {
      smartLight: {
        mode: 'manual',
        brightness: brightness
      }
    };

    if (this.data.connected) {
      udpBackendManager.sendControl(command);
    }
  },

  toggleDevice(device, enabled) {
    this.setData({
      [`deviceStatus.${device}`]: enabled
    });

    const command = {};
    command[device] = enabled ? 1 : 0;

    if (this.data.connected) {
      udpBackendManager.sendControl(command);
    }
  },

  agvMoveForward() {
    if (this.data.connected) {
      udpBackendManager.sendControl({ carStatus: 'run' });
    }
  },

  agvMoveBack() {
    if (this.data.connected) {
      udpBackendManager.sendControl({ carStatus: 'back' });
    }
  },

  agvStop() {
    if (this.data.connected) {
      udpBackendManager.sendControl({ carStatus: 'stop' });
    }
  }
});