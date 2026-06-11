// utils/g_value.js
// Global values for smart car status

const g_value = {
  // Car status values
  Value: {
    power: 100,        // Battery percentage
    mode: 'manual',    // Current mode: manual/avoid/line
    distance: 999,     // Distance in mm
    speed: 0,          // Current speed in mm/s
    gears: 1           // Speed gear: 0=low, 1=mid, 2=high
  },

  // Connection status
  connected: false,

  // Update Value from received data
  updateValue: function(data) {
    if (data) {
      Object.assign(this.Value, data);
    }
  },

  // Reset to defaults
  reset: function() {
    this.Value = {
      power: 100,
      mode: 'manual',
      distance: 999,
      speed: 0,
      gears: 1
    };
    this.connected = false;
  }
};

module.exports = g_value;
