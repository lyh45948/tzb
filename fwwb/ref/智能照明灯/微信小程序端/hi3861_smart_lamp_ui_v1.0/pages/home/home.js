// pages/home/home.js
const util = require("../../utils/util.js");
const app = getApp();

// 标志位
var global_flag = {
  request_token: false,   // 是否获取成功Token信息的标志位
  request_device_online: false, // 查看设备是否在线的标志位
}
// 全局的变量值
var global_data = {
  X_Auth_Token: "",       // 鉴权token信息
  sensor:{
    light_value: 0    // 光照传感器的数值
  },
  led: {
    // LED灯的状态
    status: false,
    text: "已关闭",
    control: {
      // LED灯的控制信息
      led_light: 0, // LED灯的光照强度
    },
  },
  // WiFi的数据
  wifi: {
    name: "", // 名字
    passwd: "", // 密码
  },
  // 定时器
  timer: {
    // 定时开启定时器
    open_timer: {   
      status: false,  
      value: ''
    },
    // 定时关闭定时器
    close_timer : { 
      status: false,  
      value: ''
    },
    // 倒计时
    count_timer : {
      mode: '',   // 倒计时的模式 开或关
      status: false,  // 是否开启定时器
      value: ''
    }
  },
};
var timerID = 0;

Page({
  data: {
    nfc_show: false, // NFC配网的弹窗界面控制
    setTimer_show: false, // 设置定时器的弹窗界面控制
    setCountTimer_show: false, // 设置倒计时的弹窗界面控制

    led_control_status: false, // LED灯当前的状态值
    led_control_text: "已关闭", // 开关，LED控制开关状态
    led_control_light_value: 100, // 滑块，LED灯的亮度控制

    light_sensor_value: 0, // 光照传感器的数据

    device_online_status: '', // 设备的在线状态 在线还是不在线

    count_timer_button_status: false,   // 倒计时控件中的按钮状态

    items: [
      // 倒计时 单选器
      { value: "ON", name: "开", checked: "true" },
      { value: "OFF", name: "关" },
    ],
  },
  // 翻转变量函数
  toggle(type) {
    this.setData({
      [type]: !this.data[type],
    });
  },

  // 倒计时 单选器的携带值
  radioChange(e) {
    console.log("radio发生change事件，携带value值为：", e.detail.value);
    
    global_data.timer.count_timer.mode = e.detail.value   // 倒计时单选器的模式

    const items = this.data.items;
    for (let i = 0, len = items.length; i < len; ++i) {
      items[i].checked = items[i].value === e.detail.value;
    }
    this.setData({
      items,
    });
  },
  // 弹窗：NFC弹窗界面
  bind_wifi_nfc_button() {
    console.log("按下“NFC配网组件”按钮");
    this.toggle("nfc_show");
  },
  // 弹窗：设置定时器弹窗界面
  bind_set_timer_top(e) {
    console.log("按下“设置定时器”按钮");
    this.toggle("setTimer_show");
  },
  // 弹窗：设置倒计时的弹窗界面
  bind_set_count_timer_top(e) {
    console.log("按下“设置倒计时”按钮");
    this.toggle("setCountTimer_show");
  },
  // 弹窗: 调整颜色控制弹窗界面
  bind_set_color_top() {
    console.log("按下“颜色控制”按钮, 跳转界面");
    // this.toggle('setColor_show');
    wx.navigateTo({
      url: "../switch_color/switch_color",
      success: function(res) {
        // 通过eventChannel向被打开页面传送数据
        res.eventChannel.emit('acceptDataFromOpenedPage', { 
          request_device_online: global_flag.request_device_online,
          request_token: global_flag.request_token,
          X_Auth_Token: global_data.X_Auth_Token
        })
      }
    });
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
  // 输入框： 定时器 - 开启时间
  bind_set_open_time_Input(e) {
    console.log(e.detail.value);
    global_data.timer.open_timer.value = e.detail.value + ':00'
  },
  // 输入框： 定时器 - 关闭时间
  bind_set_close_time_Input(e) {
    console.log(e.detail.value);
    global_data.timer.close_timer.value = e.detail.value + ':00'
  },
  // 输入框： 倒计时 - 时间
  bind_set_count_time_Input(e) {
    console.log(e.detail.value);
    global_data.timer.count_timer.value = e.detail.value
  },
  // 开关： 手动控制LED灯
  bind_led_control_change(e) {
    console.log("按下“手动控制LED灯”按钮: ", e.detail.value);
    API_send_device_cmd('lamp', {value: e.detail.value ? 'ON' : 'OFF'})
    this.setData({
      led_control_text: e.detail.value ? "已开启" : "已关闭",
      led_control_status: e.detail.value,
    });
  },
  // 开关： 定时器 - 是否打开 开启时间
  bind_set_open_timer_change(e) {
    console.log("按下“定时器 - 是否打开 开启时间”按钮: ", e.detail.value);
    global_data.timer.open_timer.status = e.detail.value
  },
  // 开关： 定时器 - 是否打开 关闭时间
  bind_set_close_timer_change(e) {
    console.log("按下“定时器 - 是否打开 关闭时间”按钮: ", e.detail.value);
    global_data.timer.close_timer.status = e.detail.value
  },
  // 开关： 倒计时 - 是否打开
  bind_set_count_timer_change(e) {
    console.log("按下“倒计时 - 是否打开”按钮: ", e.detail.value);
    global_data.timer.count_timer.status = e.detail.value
  },
  // 开关： 设置自动调光模式
  bind_auto_light_mode_change(e) {
    console.log("按下“设置自动调光模式”按钮: ", e.detail.value);
    API_send_device_cmd('is_auto_light_mode', {value: e.detail.value ? 'ON' : 'OFF'});
  },
  // 开关： 设置睡眠模式
  bind_sleep_mode_change(e) {
    console.log("按下“设置睡眠模式”按钮: ", e.detail.value);
    API_send_device_cmd('is_sleep_mode', {value: e.detail.value ? 'ON' : 'OFF'});
  },
  // 开关： 设置阅读模式
  bind_read_book_mode_change(e) {
    console.log("按下“设置阅读模式”按钮: ", e.detail.value);
    API_send_device_cmd('is_readbook_mode', {value: e.detail.value ? 'ON' : 'OFF'});
  },
  // 开关： 设置变换模式
  bind_led_blink_mode_change(e) {
    console.log("按下“设置变换模式”按钮: ", e.detail.value);
    API_send_device_cmd('is_blink_mode', {value: e.detail.value ? 'ON' : 'OFF'});
  },
  // 滑块： 调整LED灯的亮度值
  bind_led_control_light_change(e) {
    console.log("滑动触发的值：", e.detail.value);
    this.setData({ led_control_light_value: e.detail.value });
    API_send_device_cmd('led_light', {value: e.detail.value});
  },

  /**
   * 实现下拉刷新函数
   */
  onPullDownRefresh() {
    console.log("下拉刷新页面");
    wx.stopPullDownRefresh();
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

    // 定时器 5s 获取设备的镜像数据
    setInterval(() => {
      // 界面提示
      API_request_device_online();    // 获取设备是否在线
      if(global_flag.request_token != true)
        API_request_Token(app.globalData.iamUserName,app.globalData.iamUserPassword,app.globalData.userName, app.globalData.productName);

      if(global_flag.request_device_online)
        that.setData({device_online_status: '在线'})
      else
        that.setData({device_online_status: '不在线'})
      
      API_request_device_message();
      
    }, 5000);

    // 定时器 1s 获取手机的本地时间
    setInterval(() => {
      var currentTime = util.formatTime(new Date())
      console.log(currentTime)
      
      that.setData({
        light_sensor_value: global_data.sensor.light_value
      })
      
      // 定时开
      if(global_data.timer.open_timer.status)
      {
        if(currentTime == global_data.timer.open_timer.value)
        {
          console.log("定时开启 时间到了")
          API_send_device_cmd('lamp', {value: 'ON'})
          that.setData({
            led_control_text: "已开启",
            led_control_status: true,
          });
        }
      }

      // 定时关
      if(global_data.timer.close_timer.status)
      {
        if(currentTime == global_data.timer.close_timer.value)
        {
          console.log("定时关闭 时间到了")
          API_send_device_cmd('RGB',{value: 'OFF'})
          that.setData({
            led_control_text: "已关闭",
            led_control_status: false,
          });
        }
      }

      // 倒计时
      if(global_data.timer.count_timer.status)
      {
        var currentSec = util.formatSec(new Date())

        if(currentSec == global_data.timer.count_timer.value)
        {
          console.log("倒计时 时间到了")
          
          API_send_device_cmd('lamp', {value: global_data.timer.count_timer.mode})
          that.setData({
            led_control_text: global_data.timer.count_timer.mode == 'ON' ? '已打开': '已关闭',
            led_control_status: global_data.timer.count_timer.mode == 'ON' ? true: false,
            count_timer_button_status: false,   // 关闭按钮
          });
        }
      }
    }, 1000);
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
    // this.addlog({time:util.formatTime(new Date()),text:'请先移到设备旁，准备写入数据...'})
  },

  // 启动NFC搜寻
  startDiscovery() {
    // this.addlog({
    //   time: util.formatTime(new Date()),
    //   text: "请将设备放入NFC识别区",
    // });
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
        global_data.sensor.light_value = res.data.shadow[0].reported.properties.light;

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
