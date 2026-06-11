// pages/nfc/nfc.js
const util = require("../../utils/util.js");
// 全局的变量值
var global_data = {
  // WiFi的数据
  wifi: {
    name: "", // 名字
    passwd: "", // 密码
  },
}
var timerID = 0;
Page({

  /**
   * 页面的初始数据
   */
  data: {
    steps: [
      {
        text: '步骤一',
        desc: '请检查 WiFi 名称是否为英文字符！不支持中文！',
      },
      {
        text: '步骤二',
        desc: '请检查 WiFi 密码是否为英文字符！不支持中文！',
      },
      {
        text: '步骤三',
        desc: '点击开始配置后，请将手机靠近NFC线圈，直到显示烧写完成！',
      },
    ],
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad: function (options) {
    var that = this;
    // 初始化NFC
    that.NFCAdapter = wx.getNFCAdapter();
    // 获取NDEF对象
    that.NFCTab = that.NFCAdapter.getNdef();
  },
  // 输入框： WiFi名称
  bind_wifi_ssid_Input(e) {
    console.log(e.detail.value);
    global_data.wifi.name = e.detail.value;
  },
  // 输入框： WiFi密码
  bind_wifi_passwd_Input(e) {
    console.log(e.detail.value);
    global_data.wifi.passwd = e.detail.value;
  },
  /************** NFC wifi 配网函数**************/
  // 写入数据
  bind_wifi_start_set_button() {
    console.log("按下“开始配置”按钮");
    var that = this;
    var payload = `{"ssid":"${global_data.wifi.name}","passwd":"${global_data.wifi.passwd}"}`;
    console.log(payload);

    //准备写入的数据
    const records = [
      {
        id: util.str2ab(new Date().getTime().toString()),
        type: util.str2ab('t'), // 无论填入的是大写还是小写，转换完成之后都是小写的字符(十六进制)
        payload: util.str2ab(payload),
        tnf: 2,
      },
    ];

    // 开启定时器
    timerID = setInterval(function () {
      wx.showToast({
        title: "请靠近设备",
        icon: "loading",
      });
      // 搜寻设备
      that.startDiscovery();
      // 连接设备
      that.NFCconnect(records);
    }, 1000);
  },

  // 启动NFC搜寻
  startDiscovery() {
    this.NFCAdapter.startDiscovery({
      success: (res) => {},
      fail: (error) => {},
    });
  },

  // 连接设备
  NFCconnect(records) {
    this.NFCTab.connect({
      success: (res) => {
        wx.showToast({
          title: "已连接设备",
          icon: "success",
        });
        // 执行写入
        this.writeNdefMessage(records);
      },
      fail: (error) => {
        wx.showToast({
          title: "请靠近设备",
          icon: "error",
        });
      },
      complete: (res) => {},
    });
  },

  // 执行写入
  writeNdefMessage(records) {
    wx.showToast({
      title: "正在执行写入",
      icon: "success",
    });
    this.NFCTab.writeNdefMessage({
      records: records,
      success: (res) => {
        wx.showToast({
          title: "写入数据成功",
          icon: "success",
        });
      },
      fail: (error) => {
        wx.showToast({
          title: "写入数据失败",
          icon: "error",
        });
      },
      complete: () => {
        this.setData({
          disabled: false,
        });
        // 断开连接
        this.NFCTab.close();
        // 关闭定时器
        clearInterval(timerID);
      },
    });
  },

  // 关闭NFC搜寻
  stopDiscovery() {
    wx.showToast({
      title: "关闭NFC搜寻",
      icon: "success",
    });
    this.NFCAdapter.stopDiscovery({
      success: (res) => {
        wx.showToast({
          title: "关闭搜寻成功",
          icon: "success",
        });
      },
      fail: (error) => {
        wx.showToast({
          title: "关闭搜寻失败",
          icon: "error",
        });
      },
    });
  },
})