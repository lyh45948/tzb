// pages/control/control.js
const app = getApp();

Page({
  data: {
    deviceStatus: {
      pump: false,
      valve: false,
      led: false,
      fan: false
    },
    ledBrightness: 50,
    autoMode: false
  },

  onLoad() {
    this.loadStatus();
  },

  onShow() {
    this.loadStatus();
    app.setDataUpdateCallback(() => {
      this.loadStatus();
    });
  },

  onHide() {
    app.setDataUpdateCallback(null);
  },

  onUnload() {
    app.setDataUpdateCallback(null);
  },

  // 加载设备状态
  loadStatus() {
    const app = getApp();
    this.setData({
      deviceStatus: app.globalData.deviceStatus,
      autoMode: app.globalData.autoControl
    });
  },

  // 控制水泵
  onPumpChange(e) {
    const status = e.detail;
    const app = getApp();
    app.sendControl('pump', status);
    this.setData({
      'deviceStatus.pump': status
    });
  },

  // 控制电磁阀
  onValveChange(e) {
    const status = e.detail;
    const app = getApp();
    app.sendControl('valve', status);
    this.setData({
      'deviceStatus.valve': status
    });
  },

  // 控制LED灯
  onLedChange(e) {
    const status = e.detail;
    const app = getApp();
    app.sendControl('led', status);
    this.setData({
      'deviceStatus.led': status
    });
  },

  // 控制风扇
  onFanChange(e) {
    const status = e.detail;
    const app = getApp();
    app.sendControl('fan', status);
    this.setData({
      'deviceStatus.fan': status
    });
  },

  // 调整LED亮度
  onLedBrightness(e) {
    const brightness = e.detail;
    this.setData({
      ledBrightness: brightness
    });
    // 可以发送亮度值到设备
    const app = getApp();
    // app.sendControl('ledBrightness', brightness);
  },

  // 切换自动模式
  onAutoModeChange(e) {
    const status = e.detail;
    const app = getApp();
    app.globalData.autoControl = status;
    this.setData({
      autoMode: status
    });
  }
});
