// pages/settings/settings.js - 融合 smart_agriculture 阈值配置
const configManager = require('../../utils/config-manager');
const app = getApp();

Page({
  /**
   * Page data
   */
  data: {
    // Threshold settings（融合 smart_agriculture 的阈值配置）
    thresholds: {
      temperature: {
        min: 15,
        max: 35,
        currentMin: 18,
        currentMax: 30
      },
      humidity: {
        min: 40,
        max: 80,
        currentMin: 40,
        currentMax: 70
      },
      light: {
        min: 500,
        max: 5000,
        currentMin: 800,
        currentMax: 3000
      },
      co2: {
        min: 400,
        max: 1000,
        currentMin: 400,
        currentMax: 800
      }
    },
    // Alert notification toggle
    alertEnabled: true,
    // 自动控制模式（融合 smart_agriculture）
    autoControl: false,
    // Original settings for reset
    originalSettings: null,
    // Has changes flag
    hasChanges: false
  },

  /**
   * Lifecycle function - onLoad
   */
  onLoad(options) {
    this.loadSettings();
  },

  /**
   * Load saved settings from storage
   */
  loadSettings() {
    try {
      // 从 configManager 加载阈值配置
      const thresholds = configManager.getThresholds();
      
      // 合并阈值配置到 currentMin/currentMax
      const mergedThresholds = {};
      for (const [key, threshold] of Object.entries(thresholds)) {
        mergedThresholds[key] = {
          ...threshold,
          currentMin: threshold.min + 3, // 默认偏移
          currentMax: threshold.max - 3
        };
      }
      
      // 加载告警设置
      const savedSettings = wx.getStorageSync('threshold_settings');
      const alertEnabled = savedSettings?.alertEnabled !== undefined ? savedSettings.alertEnabled : true;
      const autoControl = app.globalData.autoControl || false;
      
      this.setData({
        thresholds: {
          ...this.data.thresholds,
          ...mergedThresholds
        },
        alertEnabled,
        autoControl,
        originalSettings: JSON.parse(JSON.stringify({
          thresholds: { ...this.data.thresholds, ...mergedThresholds },
          alertEnabled,
          autoControl
        }))
      });
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
  },

  /**
   * Check if settings have changed
   */
  checkChanges() {
    const current = {
      thresholds: this.data.thresholds,
      alertEnabled: this.data.alertEnabled
    };
    const original = this.data.originalSettings;

    const hasChanges = JSON.stringify(current) !== JSON.stringify(original);
    this.setData({ hasChanges });
  },

  /**
   * Temperature min slider change
   */
  onTempMinChange(e) {
    const value = Math.round(e.detail);
    const maxVal = this.data.thresholds.temperature.currentMax - 2;
    const clampedValue = Math.min(value, maxVal);

    this.setData({
      'thresholds.temperature.currentMin': clampedValue
    }, () => this.checkChanges());
  },

  /**
   * Temperature max slider change
   */
  onTempMaxChange(e) {
    const value = Math.round(e.detail);
    const minVal = this.data.thresholds.temperature.currentMin + 2;
    const clampedValue = Math.max(value, minVal);

    this.setData({
      'thresholds.temperature.currentMax': clampedValue
    }, () => this.checkChanges());
  },

  /**
   * Humidity min slider change
   */
  onHumiMinChange(e) {
    const value = Math.round(e.detail);
    const maxVal = this.data.thresholds.humidity.currentMax - 5;
    const clampedValue = Math.min(value, maxVal);

    this.setData({
      'thresholds.humidity.currentMin': clampedValue
    }, () => this.checkChanges());
  },

  /**
   * Humidity max slider change
   */
  onHumiMaxChange(e) {
    const value = Math.round(e.detail);
    const minVal = this.data.thresholds.humidity.currentMin + 5;
    const clampedValue = Math.max(value, minVal);

    this.setData({
      'thresholds.humidity.currentMax': clampedValue
    }, () => this.checkChanges());
  },

  /**
   * Light min slider change
   */
  onLightMinChange(e) {
    const value = Math.round(e.detail);
    const maxVal = this.data.thresholds.light.currentMax - 100;
    const clampedValue = Math.min(value, maxVal);

    this.setData({
      'thresholds.light.currentMin': clampedValue
    }, () => this.checkChanges());
  },

  /**
   * Light max slider change
   */
  onLightMaxChange(e) {
    const value = Math.round(e.detail);
    const minVal = this.data.thresholds.light.currentMin + 100;
    const clampedValue = Math.max(value, minVal);

    this.setData({
      'thresholds.light.currentMax': clampedValue
    }, () => this.checkChanges());
  },

  /**
   * CO2 min slider change（融合 smart_agriculture）
   */
  onCo2MinChange(e) {
    const value = Math.round(e.detail);
    const maxVal = this.data.thresholds.co2.currentMax - 50;
    const clampedValue = Math.min(value, maxVal);

    this.setData({
      'thresholds.co2.currentMin': clampedValue
    }, () => this.checkChanges());
  },

  /**
   * CO2 max slider change（融合 smart_agriculture）
   */
  onCo2MaxChange(e) {
    const value = Math.round(e.detail);
    const minVal = this.data.thresholds.co2.currentMin + 50;
    const clampedValue = Math.max(value, minVal);

    this.setData({
      'thresholds.co2.currentMax': clampedValue
    }, () => this.checkChanges());
  },

  /**
   * Alert toggle change
   */
  onAlertToggle(e) {
    this.setData({
      alertEnabled: e.detail
    }, () => this.checkChanges());
  },

  /**
   * 自动控制模式切换（融合 smart_agriculture）
   */
  onAutoControlChange(e) {
    const enabled = e.detail;
    this.setData({ autoControl: enabled });
    app.toggleAutoControl(enabled);
    this.checkChanges();
  },

  /**
   * Save settings（融合 smart_agriculture 配置）
   */
  onSave() {
    // 保存阈值配置到 configManager
    const thresholdsToSave = {};
    for (const [key, threshold] of Object.entries(this.data.thresholds)) {
      thresholdsToSave[key] = {
        min: threshold.min,
        max: threshold.max,
        unit: threshold.unit || this.getDefaultUnit(key),
        name: threshold.name || this.getDefaultName(key)
      };
    }
    configManager.saveThresholds(thresholdsToSave);
    
    // 保存告警和自动控制设置
    const settings = {
      thresholds: this.data.thresholds,
      alertEnabled: this.data.alertEnabled,
      autoControl: this.data.autoControl
    };

    try {
      wx.setStorageSync('threshold_settings', settings);

      // Update original settings
      this.setData({
        originalSettings: JSON.parse(JSON.stringify(settings)),
        hasChanges: false
      });

      wx.showToast({
        title: '保存成功',
        icon: 'success',
        duration: 2000
      });
    } catch (e) {
      console.error('Failed to save settings:', e);
      wx.showToast({
        title: '保存失败',
        icon: 'error',
        duration: 2000
      });
    }
  },

  // 获取默认单位
  getDefaultUnit(key) {
    const units = {
      temperature: '°C',
      humidity: '%',
      light: 'lux',
      co2: 'ppm'
    };
    return units[key] || '';
  },

  // 获取默认名称
  getDefaultName(key) {
    const names = {
      temperature: '温度',
      humidity: '湿度',
      light: '光照',
      co2: 'CO2'
    };
    return names[key] || '';
  },

  /**
   * Reset settings to original（融合 smart_agriculture 配置）
   */
  onReset() {
    wx.showModal({
      title: '确认重置',
      content: '确定要重置所有配置到默认值吗？',
      confirmText: '确定',
      cancelText: '取消',
      confirmColor: '#07c160',
      success: (res) => {
        if (res.confirm) {
          // 重置阈值配置
          configManager.resetThresholds();
          
          // Default settings（融合 smart_agriculture）
          const defaultSettings = {
            thresholds: {
              temperature: {
                min: 15,
                max: 35,
                currentMin: 18,
                currentMax: 30,
                unit: '°C',
                name: '温度'
              },
              humidity: {
                min: 40,
                max: 80,
                currentMin: 40,
                currentMax: 70,
                unit: '%',
                name: '湿度'
              },
              light: {
                min: 500,
                max: 5000,
                currentMin: 800,
                currentMax: 3000,
                unit: 'lux',
                name: '光照'
              },
              co2: {
                min: 400,
                max: 1000,
                currentMin: 400,
                currentMax: 800,
                unit: 'ppm',
                name: 'CO2'
              }
            },
            alertEnabled: true,
            autoControl: false
          };

          this.setData({
            thresholds: defaultSettings.thresholds,
            alertEnabled: defaultSettings.alertEnabled,
            autoControl: defaultSettings.autoControl,
            originalSettings: JSON.parse(JSON.stringify(defaultSettings)),
            hasChanges: false
          });

          wx.showToast({
            title: '已恢复默认',
            icon: 'success',
            duration: 2000
          });
        }
      }
    });
  },

  /**
   * Navigate back
   */
  onBack() {
    if (this.data.hasChanges) {
      wx.showModal({
        title: '未保存的更改',
        content: '您有未保存的更改，确定要离开吗？',
        confirmText: '离开',
        cancelText: '取消',
        confirmColor: '#ee0a24',
        success: (res) => {
          if (res.confirm) {
            wx.navigateBack();
          }
        }
      });
    } else {
      wx.navigateBack();
    }
  }
});
