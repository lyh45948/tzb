// 加载库
var util = require('../../utils/util.js')
const app = getApp();

// 标志位
var global_flag = {
  request_token: false,   // 是否获取成功Token信息的标志位
  request_device_online: false, // 查看设备是否在线的标志位
}
var input_humi_up = 0;
var input_humi_down = 0;

// 全局的变量值
var global_data = {
  X_Auth_Token: "",       // 鉴权token信息
  status:{
    auto: false,
    fan: false,
  },
  sensor:{
    humi: 0,    
    temp: 0,
  },
  threshold:{
    humi_up: 0,
    humi_down: 0,
  },
  // WiFi的数据
  wifi: {
    name: "", // 名字
    passwd: "", // 密码
  },
};
var timerID = 0;    // NFC配网使用的定时器

Page({
  data: {
    nfc_show: false, // NFC配网的弹窗界面控制
    status:{
      auto: false,
      fan: false,
      device_online: '掉线',    // 在线或者掉线
    },
    sensor:{
      humi: 0,    
      temp: 0,
    },
    threshold:{
      humi_up: 0,
      humi_down: 0,
    }
  },
  // 翻转变量函数
  toggle(type) {
    this.setData({
      [type]: !this.data[type],
    });
  },
  // 弹窗：NFC弹窗界面
  bind_wifi_nfc_button() {
    console.log("按下“NFC配网组件”按钮");
    this.toggle("nfc_show");
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
  // 输入框： 上限输入
  bind_slider_set_humi_up(e){
    console.log("bind_slider_set_humi_up = ", e);
    input_humi_up = e.detail.value
  },
  // 输入框： 下限输入
  bind_slider_set_humi_down(e){
    console.log("bind_slider_set_humi_down = ", e);
    input_humi_down = e.detail.value
  },
  // 将上下限数据保存在本地
  bind_write_device_flash(e){
    console.log("bind_write_device_flash = ", e);
    API_send_device_cmd("humidity", {up: input_humi_up, down: input_humi_down})
  },
  // 开关： 手动控制
  bind_fan_control_change(e) {
    console.log("bind_fan_control_change = ", e);
    API_send_device_cmd("fan", {value: e.detail.value ? 'ON' : 'OFF'})
  },
  // 开关： 设置自动模式
  bind_auto_control_change(e) {
    console.log("bind_auto_control_change = ", e);
    API_send_device_cmd("autoMode", {value: e.detail.value ? 'ON' : 'OFF'})
  },
  /**
   * 界面加载函数
   */
  onLoad: function () {
    var that = this;
    // 初始化NFC
    that.NFCAdapter = wx.getNFCAdapter();
    // 获取NDEF对象
    that.NFCTab = that.NFCAdapter.getNdef();
    // 获取API的Token鉴权信息
    API_request_Token(app.globalData.iamUserName,app.globalData.iamUserPassword,app.globalData.userName, app.globalData.productName);

    // 定时器 1s 获取设备的镜像数据
    setInterval(() => {
      // 界面提示
      API_request_device_online();    // 获取设备是否在线
      if(global_flag.request_token != true)
        API_request_Token(app.globalData.iamUserName,app.globalData.iamUserPassword,app.globalData.userName, app.globalData.productName);

      if(global_flag.request_device_online){
        that.setData({
          status:{
            auto: global_data.status.auto,
            fan: global_data.status.fan,
            device_online: '在线',    
          },
          sensor:{
            humi: global_data.sensor.humi,    
            temp: global_data.sensor.temp,
          },
          threshold:{
            humi_up: global_data.threshold.humi_up,
            humi_down: global_data.threshold.humi_down,
          }
        })
      }
      else{
        that.setData({
          status:{
            device_online: '掉线'
          }
        }) 
      }
      
      API_request_device_message();
    }, 300);
  },


  /*************************************** NFC wifi 配网函数 ***************************************/
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
      success: (res) => { },
      fail: (error) => { },
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
      complete: (res) => { },
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

  
});



/*************************************** 华为云HTTP服务API ***************************************/
// 获取Token信息
function API_request_Token(iamUserName, iamUserPassword, userName, productName) {
  wx.request({
    url: `https://${app.globalData.iamEndpoint}/v3/auth/tokens?nocatalog=true`,
    method: "POST",
    data: {
      auth: {
        identity: {
          methods: ["password"],
          password: {
            user: {
              domain: {
                name: userName,
              },
              name: iamUserName,
              password: iamUserPassword,
            },
          },
        },
        scope: {
          project: {
            name: productName,
          },
        },
      },
    },
    success: (res) => {
      // 保存当前的Token
      global_data.X_Auth_Token = res.header["X-Subject-Token"];
      console.log("获取Token: OK!");
      global_flag.request_token = true;
      API_request_device_online()
      // 弹窗提示
      wx.showToast({
        title: "获取Token成功!",
        icon: "success",
      });
    },
    fail: (res) => {
      console.log("获取Token信息，API获取失败! res: ");
      console.log(res);
      global_flag.request_token = false;

      // 弹窗提示
      wx.showToast({
        title: "获取Token失败!",
        icon: "error",
      });
    },
  });
}
// 获取设备状态
function API_request_device_online() {
  if(global_flag.request_token){
    wx.request({
      url: `https://${app.globalData.iotDAEndpoint}/v5/iot/${app.globalData.project_id}/devices/${app.globalData.device_id}`,
      header: {
        "X-Auth-Token": global_data.X_Auth_Token,
      },
      success: (res) => {
        console.log("获取设备是否在线，API获取成功! res: ", res);
        if (res.data.status == "ONLINE") {
          console.log("设备在线状态");
          global_flag.request_device_online = true;
        } else {
          console.log("设备不在线");
          global_flag.request_device_online = false;
        }
      },
      fail: (res) => {
        console.log("获取设备是否在线，API获取失败! res: ");
        console.log(res);
      },
    });
  }
}
// 获取设备的镜像信息
function API_request_device_message() {
  var that = this
  if (global_flag.request_device_online && global_flag.request_token) {
    wx.request({
      url: `https://${app.globalData.iotDAEndpoint}/v5/iot/${app.globalData.project_id}/devices/${app.globalData.device_id}/shadow`,
      header: {
        "X-Auth-Token": global_data.X_Auth_Token,
      },
      success: (res) => {
        console.log(res.data.shadow[0].reported.properties);
        // global_data.sensor.light_value = res.data.shadow[0].reported.properties.light;
        global_data.sensor.temp = res.data.shadow[0].reported.properties.temperature;
        global_data.sensor.humi = res.data.shadow[0].reported.properties.humidity;
        global_data.threshold.humi_down = res.data.shadow[0].reported.properties.humi_down;
        global_data.threshold.humi_up = res.data.shadow[0].reported.properties.humi_up;
        global_data.status.fan = (res.data.shadow[0].reported.properties.fan == "ON") ? true : false;
        global_data.status.auto = (res.data.shadow[0].reported.properties.autoMode == "ON") ? true : false;
      },
      fail: (res) => {
        console.log("查询设备影子，API获取失败! res: ");
        console.log(res);
      },
    });
  }
}
// 下发设备命令
function API_send_device_cmd(cmd, data) {
  if (global_flag.request_device_online && global_flag.request_token) {
    wx.request({
      url: `https://${app.globalData.iotDAEndpoint}/v5/iot/${app.globalData.project_id}/devices/${app.globalData.device_id}/commands`,
      header: {
        "X-Auth-Token": global_data.X_Auth_Token,
      },
      method: "POST",
      data: {
        service_id: 'control',
        command_name: cmd,
        paras: data,
      },
      success: (res) => {
        console.log("下发命令成功", res);

        // 弹窗提示
        wx.showToast({
          title: "下发命令成功",
          icon: "error",
        });
      },
      fail: (res) => {
        console.log("下发命令失败", res);

        // 弹窗提示
        wx.showToast({
          title: "下发命令失败",
          icon: "error",
        });
      },
    });
  } else {
    // 弹窗提示
    wx.showToast({
      title: "设备不在线",
      icon: "error",
    });
  }
}