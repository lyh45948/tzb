const networkManager = require('../../utils/network-manager');

Page({
    data: {
        connected: false,
        envData: {
            temp: 0,
            humi: 0
        }
    },

    onLoad: function () {
        this.initNetwork();
    },

    onShow: function () {
        this.updateStatus();
    },

    onUnload: function () {
        this.cleanup();
    },

    initNetwork: function () {
        this.onConnectionChange = (connected) => {
            this.setData({ connected });
        };
        networkManager.onConnectionChange(this.onConnectionChange);

        this.onMessage = (res) => {
            if (res.temp !== undefined || res.humi !== undefined) {
                this.setData({
                    'envData.temp': res.temp || this.data.envData.temp,
                    'envData.humi': res.humi || this.data.envData.humi
                });
            }
        };
        networkManager.onMessage(this.onMessage);
    },

    updateStatus: function () {
        const status = networkManager.getConnectionStatus();
        this.setData({ connected: status.connected });
    },

    cleanup: function () {
        if (this.onConnectionChange) networkManager.offConnectionChange(this.onConnectionChange);
        if (this.onMessage) networkManager.offMessage(this.onMessage);
    },

    sendVoiceCmd: function (e) {
        const hexCmd = e.currentTarget.dataset.cmd;
        // App-side simulation:
        // Some commands map to specific JSON fields
        let msg = {};
        switch (hexCmd) {
            case '0x10': msg = { carStatus: 'on' }; break;
            case '0x11': msg = { carStatus: 'off' }; break;
            case '0x20': msg = { carStatus: 'run' }; break;
            case '0x21': msg = { carStatus: 'back' }; break;
            case '0x22': msg = { carStatus: 'left' }; break;
            case '0x23': msg = { carStatus: 'right' }; break;
            case '0x24': msg = { carStatus: 'stop' }; break;
            case '0x30': msg = { carMode: 'avoid' }; break;
            case '0x31': msg = { carMode: 'line' }; break;
            case '0x50': msg = { fanStatus: 'on' }; break;
            case '0x51': msg = { fanStatus: 'off' }; break;
            case '0x60': msg = { cmd: 'query_env' }; break;
            case '0x40': // Square
                msg = {
                    carMode: 'path', path: [
                        { d: 200, a: 0 }, { d: 200, a: 90 }, { d: 200, a: 90 }, { d: 200, a: 90 }
                    ]
                };
                break;
            case '0x41': // Triangle
                msg = {
                    carMode: 'path', path: [
                        { d: 200, a: 0 }, { d: 200, a: 120 }, { d: 200, a: 120 }
                    ]
                };
                break;
        }

        if (networkManager.send(msg)) {
            wx.showToast({ title: `执行指令 ${hexCmd}`, icon: 'none' });
        }
    }
});
