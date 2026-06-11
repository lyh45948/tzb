//index.js
const app = getApp();
var request_device_online_flag = false
var request_token_flag = false
var X_Auth_Token = ''
Page({
  data: {
    color: 'rgb(0,0,0)'
  },
  onLoad: function() {
    const eventChannel = this.getOpenerEventChannel()
    eventChannel.on('acceptDataFromOpenedPage', function(data) {
      console.log(data)
      request_token_flag = data.request_token;
      request_device_online_flag = data.request_device_online;
      X_Auth_Token = data.X_Auth_Token
    })
    this.setData({
      color: app.globalData.color
    })
  },
  onReady: function() {
    //默认状态不需要设置
    this.colorPicker = this.selectComponent('#picker');
    this.setData({
      size: this.colorPicker.rpx2px(450),
      left: this.colorPicker.rpx2px(150),
      top: this.colorPicker.rpx2px(150)
    })
  },
  selectColor: function(e) {
    var that = this;
    console.log(`rgb(${e.detail.rgb.R},${e.detail.rgb.G},${e.detail.rgb.B})`)
    
    app.globalData.color = `rgb(${e.detail.rgb.R},${e.detail.rgb.G},${e.detail.rgb.B})`

    API_send_device_cmd('RGB', {"red":e.detail.rgb.R,"green":e.detail.rgb.G,"blue":e.detail.rgb.B})
    
    that.setData({
      color: `rgb(${e.detail.rgb.R},${e.detail.rgb.G},${e.detail.rgb.B})`
    })
  }
})



// 下发设备命令
function API_send_device_cmd(cmd, data) {
  if (request_device_online_flag && request_token_flag) {
    wx.request({
      url: `https://${app.globalData.iotDAEndpoint}/v5/iot/${app.globalData.project_id}/devices/${app.globalData.device_id}/commands`,
      header: {
        "X-Auth-Token": X_Auth_Token,
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