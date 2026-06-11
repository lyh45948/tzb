// components/sensor-gauge/sensor-gauge.js
// 圆形仪表盘组件 - 使用van-circle封装
Component({
  properties: {
    // 当前值
    value: {
      type: Number,
      value: 0
    },
    // 最大值
    max: {
      type: Number,
      value: 100
    },
    // 标题/标签
    title: {
      type: String,
      value: ''
    },
    // 单位
    unit: {
      type: String,
      value: ''
    },
    // 颜色
    color: {
      type: String,
      value: '#4CAF50'
    },
    // 尺寸
    size: {
      type: Number,
      value: 120
    },
    // 线条宽度
    strokeWidth: {
      type: Number,
      value: 8
    }
  },

  data: {
    percentage: 0
  },

  observers: {
    'value, max': function(value, max) {
      const percentage = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
      this.setData({
        percentage: Math.round(percentage)
      });
    }
  },

  lifetimes: {
    attached() {
      const percentage = this.properties.max > 0
        ? Math.min(100, Math.max(0, (this.properties.value / this.properties.max) * 100))
        : 0;
      this.setData({
        percentage: Math.round(percentage)
      });
    }
  },

  methods: {
    // 预留方法
  }
});
