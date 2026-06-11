// utils/udp.js
// UDP communication utility for smart car

const udp = {
  socket: null,
  ip: '',
  port: 7788,
  onMessageCallback: null,

  // Initialize UDP socket
  init: function() {
    if (!this.socket) {
      this.socket = wx.createUDPSocket();
      this.socket.bind();
      this.socket.onMessage((res) => {
        if (this.onMessageCallback) {
          try {
            const message = String.fromCharCode.apply(null, new Uint8Array(res.message));
            const data = JSON.parse(message);
            this.onMessageCallback(data);
          } catch (e) {
            console.error('[UDP] Parse error:', e);
          }
        }
      });
    }
    return this.socket;
  },

  // Set server address
  setServer: function(ip, port) {
    this.ip = ip;
    this.port = port || 7788;
  },

  // Send command
  send: function(cmd) {
    if (!this.socket) {
      this.init();
    }

    if (!this.ip) {
      console.warn('[UDP] No IP configured');
      return false;
    }

    const message = typeof cmd === 'string' ? cmd : JSON.stringify(cmd);
    this.socket.send({
      address: this.ip,
      port: this.port,
      message: message
    });
    return true;
  },

  // Set message handler
  onMessage: function(callback) {
    this.onMessageCallback = callback;
  },

  // Close socket
  close: function() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
};

module.exports = udp;
