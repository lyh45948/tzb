// pages/virtual_fence/virtual_fence.js
// 虚拟围栏页面 - 通过后端连接控制小车

const udpBackendManager = require('../../utils/udp-backend-manager');
const errorHandler = require('../../utils/error-handler');

var fenceCanvas = null;
var fenceCtx = null;

// Dead Reckoning Constants
const WHEEL_BASELINE = 286; // mm (Corrected for 2x rotation)

Page({
    data: {
        connectionStatus: { connected: false, message: '未连接后端' },
        fenceMode: 'circle',
        fenceRadius: 50,
        fencePoints: [],
        savedFences: [],
        canvasWidth: 0,
        canvasHeight: 0,
        activeNames: [],

        // Joystick data (Center: (140-44)/2 = 48)
        handleLeft: 48,
        handleTop: 48,
        handleTransition: 'none',
        fenceEnabled: true,
        dynamicScale: 0.5 // Scale to map mm to pixels
    },

    lastSendTime: 0,
    joystickRect: null,
    isViolationStopped: false,
    isOutsideZone: false,

    // Dead Reckoning State (Millimeters)
    posX: 0,
    posY: 0,
    heading: -Math.PI / 2,
    lastMsgTime: 0,

    onLoad: function () {
        this.loadSavedData();
        this.initBackendListeners();
        this.updateConnectionStatus();
    },

    onFenceEnabledChange(e) {
        this.setData({ fenceEnabled: e.detail });
        if (!e.detail) {
            this.isViolationStopped = false;
            this.isOutsideZone = false;
        } else {
            this.checkFenceSafety();
        }
    },

    onReady: function () {
        this.initCanvas();
        const query = wx.createSelectorQuery();
        query.select('.joystick-container-mini').boundingClientRect(res => {
            this.joystickRect = res;
        }).exec();
    },

    onUnload: function () {
        this.cleanupBackendListeners();
    },

    // Initialize backend connection listeners
    initBackendListeners() {
        // Connection status callback
        this._onConnectionChange = (connected, message, data) => {
            this.updateConnectionStatus();
        };
        udpBackendManager.onConnectionChange(this._onConnectionChange);

        // Message callback: receive realtime data from backend
        this._onMessage = (data) => {
            if (data) {
                this.handleDeviceMessage(data);
            }
        };
        udpBackendManager.onMessage(this._onMessage);
    },

    cleanupBackendListeners() {
        if (this._onConnectionChange) {
            udpBackendManager.offConnectionChange(this._onConnectionChange);
        }
        if (this._onMessage) {
            udpBackendManager.offMessage(this._onMessage);
        }
    },

    updateConnectionStatus() {
        const status = udpBackendManager.getConnectionStatus();
        const connected = status.connected && status.carConnected;
        const message = status.carConnected
            ? '已连接小车(经后端)'
            : (status.connected ? '已连接后端' : '未连接后端');
        this.setData({ connectionStatus: { connected, message } });
    },

    initCanvas() {
        const query = wx.createSelectorQuery();
        query.select('#fenceCanvas').fields({ node: true, size: true }).exec((res) => {
            if (!res[0]) return;
            const canvas = res[0].node;
            const ctx = canvas.getContext('2d');
            const dpr = wx.getWindowInfo().pixelRatio;
            canvas.width = res[0].width * dpr;
            canvas.height = res[0].height * dpr;
            ctx.scale(dpr, dpr);
            fenceCanvas = canvas;
            fenceCtx = ctx;
            this.setData({ canvasWidth: res[0].width, canvasHeight: res[0].height });
            this.resetCarPosition();
            this.updateDynamicScale();
            this.drawFencePreview();
        });
    },

    resetCarPosition() {
        this.posX = 0;
        this.posY = 0;
        this.heading = -Math.PI / 2;
        this.isViolationStopped = false;
        this.isOutsideZone = false;
    },

    // Handle realtime data from backend (same format as before: L_spd, R_spd)
    handleDeviceMessage(json) {
        const now = Date.now();
        if (this.lastMsgTime === 0) { this.lastMsgTime = now; return; }
        const dt = (now - this.lastMsgTime) / 1000;
        this.lastMsgTime = now;

        const SCALE_FACTOR = 0.4825;
        const vL = (json.L_spd !== undefined ? json.L_spd : 0) * SCALE_FACTOR;
        const vR = (json.R_spd !== undefined ? json.R_spd : 0) * SCALE_FACTOR;

        const v = (vL + vR) / 2;
        const omega = (vL - vR) / WHEEL_BASELINE;

        if (Math.abs(omega) < 0.001) {
            this.posX += v * Math.cos(this.heading) * dt;
            this.posY += v * Math.sin(this.heading) * dt;
        } else {
            const dTheta = omega * dt;
            this.posX += (v / omega) * (Math.sin(this.heading + dTheta) - Math.sin(this.heading));
            this.posY -= (v / omega) * (Math.cos(this.heading + dTheta) - Math.cos(this.heading));
            this.heading += dTheta;
        }

        while (this.heading > Math.PI) this.heading -= 2 * Math.PI;
        while (this.heading < -Math.PI) this.heading += 2 * Math.PI;

        this.updateDynamicScale();
        this.checkFenceSafety();
        this.drawFencePreview();
    },

    updateDynamicScale() {
        const carDistSq = this.posX * this.posX + this.posY * this.posY;
        const carDist = Math.sqrt(carDistSq);
        const maxFenceRadius = this.data.fenceRadius;

        // Ensure both car and fence are in view with some padding (40mm)
        const maxNeededDim = Math.max(carDist + 40, maxFenceRadius + 40);
        const minCanvasDim = Math.min(this.data.canvasWidth, this.data.canvasHeight) / 2;

        let scale = minCanvasDim / maxNeededDim;
        scale = Math.min(1.0, Math.max(0.05, scale)); // Slightly wider range

        this.setData({ dynamicScale: scale });
    },

    checkFenceSafety() {
        if (!this.data.fenceEnabled) return;
        const activeFences = this.data.savedFences.filter(f => f.enabled);
        if (activeFences.length === 0) return;

        let insideAny = false;
        const carP = { x: this.posX, y: this.posY };

        for (const fence of activeFences) {
            if (this.isPointInFenceWorld(carP, fence)) {
                insideAny = true;
                break;
            }
        }

        if (!insideAny) {
            this.isOutsideZone = true;
            if (!this.isViolationStopped) {
                this.triggerSafetyStop();
            }
        } else {
            this.isOutsideZone = false;
            this.isViolationStopped = false;
        }
    },

    isPointInFenceWorld(p, fence) {
        if (fence.mode === 'circle') {
            const dist = Math.sqrt(p.x * p.x + p.y * p.y);
            return dist <= fence.radius;
        } else if (fence.mode === 'rectangle') {
            const s = fence.radius * 1.5;
            return Math.abs(p.x) <= s / 2 && Math.abs(p.y) <= s / 2;
        } else if (fence.mode === 'polygon' && fence.points.length >= 3) {
            return this.isPointInPolygon(p, fence.points);
        }
        return true;
    },

    isPointInPolygon(point, vs) {
        let x = point.x, y = point.y;
        let inside = false;
        for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
            let xi = vs[i].x, yi = vs[i].y;
            let xj = vs[j].x, yj = vs[j].y;
            let intersect = ((yi > y) != (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    },

    // Send stop command through backend
    triggerSafetyStop() {
        this.isViolationStopped = true;
        const status = udpBackendManager.getConnectionStatus();
        if (status.connected && status.carConnected) {
            udpBackendManager.sendControl({ carMode: 'manual', carStatus: 'stop' });
        }
        wx.showToast({ title: '触发电子围栏制动', icon: 'error', duration: 2000 });
        wx.vibrateLong();
    },

    loadSavedData() {
        const fences = wx.getStorageSync('saved_fences') || [];
        this.setData({ savedFences: fences });
    },

    toggleFenceMode(e) {
        this.setData({ fenceMode: e.currentTarget.dataset.mode, fencePoints: [] });
        this.updateDynamicScale();
        this.drawFencePreview();
    },

    onFenceRadiusChange(e) {
        this.setData({ fenceRadius: e.detail });
        this.updateDynamicScale();
        this.drawFencePreview();
    },

    onFenceRadiusInputChange(e) {
        const val = parseInt(e.detail);
        if (!isNaN(val) && val > 0) {
            this.setData({ fenceRadius: val });
            this.updateDynamicScale();
            this.drawFencePreview();
        }
    },

    drawFencePreview() {
        if (!fenceCtx) return;
        const ctx = fenceCtx;
        const w = this.data.canvasWidth;
        const h = this.data.canvasHeight;
        const scale = this.data.dynamicScale;

        ctx.clearRect(0, 0, w, h);

        ctx.save();
        ctx.translate(w / 2, h / 2);
        ctx.scale(scale, scale);

        // Draw grid
        ctx.strokeStyle = '#f0f0f0';
        ctx.lineWidth = 1 / scale;
        ctx.beginPath();
        for (let x = -5000; x <= 5000; x += 200) {
            ctx.moveTo(x, -5000); ctx.lineTo(x, 5000);
        }
        for (let y = -5000; y <= 5000; y += 200) {
            ctx.moveTo(-5000, y); ctx.lineTo(5000, y);
        }
        ctx.stroke();

        // Draw saved fences
        this.data.savedFences.forEach(f => {
            if (!f.enabled) return;
            const isCarInIdx = this.isPointInFenceWorld({ x: this.posX, y: this.posY }, f);
            ctx.strokeStyle = isCarInIdx ? '#07c160' : '#ee0a24';
            ctx.lineWidth = 3 / scale;

            if (f.mode === 'circle') {
                ctx.beginPath();
                ctx.arc(0, 0, f.radius, 0, Math.PI * 2);
                ctx.stroke();
            } else if (f.mode === 'rectangle') {
                const s = f.radius * 1.5;
                ctx.strokeRect(-s / 2, -s / 2, s, s);
            } else if (f.points && f.points.length > 0) {
                ctx.beginPath();
                ctx.moveTo(f.points[0].x, f.points[0].y);
                f.points.forEach(p => ctx.lineTo(p.x, p.y));
                ctx.closePath();
                ctx.stroke();
            }
        });

        // Draw current preview (dashed)
        ctx.strokeStyle = '#ff976a';
        ctx.setLineDash([5 / scale, 5 / scale]);
        ctx.lineWidth = 2 / scale;
        if (this.data.fenceMode === 'circle') {
            ctx.beginPath();
            ctx.arc(0, 0, this.data.fenceRadius, 0, Math.PI * 2);
            ctx.stroke();
        } else if (this.data.fenceMode === 'rectangle') {
            const s = this.data.fenceRadius * 1.5;
            ctx.strokeRect(-s / 2, -s / 2, s, s);
        } else if (this.data.fencePoints.length > 0) {
            ctx.beginPath();
            ctx.moveTo(this.data.fencePoints[0].x, this.data.fencePoints[0].y);
            this.data.fencePoints.forEach(p => ctx.lineTo(p.x, p.y));
            if (this.data.fencePoints.length > 2) ctx.closePath();
            ctx.stroke();
        }
        ctx.setLineDash([]);

        // Draw car
        ctx.save();
        ctx.translate(this.posX, this.posY);
        ctx.rotate(this.heading + Math.PI / 2);

        ctx.beginPath();
        ctx.moveTo(0, -12 / scale); ctx.lineTo(10 / scale, 10 / scale); ctx.lineTo(-10 / scale, 10 / scale);
        ctx.closePath();
        ctx.fillStyle = '#ee0a24';
        ctx.fill();
        ctx.restore();

        ctx.restore();
    },

    onFenceTouchStart(e) {
        if (this.data.fenceMode !== 'polygon') return;
        const { x, y } = e.touches[0];
        const scale = this.data.dynamicScale;
        const worldX = (x - this.data.canvasWidth / 2) / scale;
        const worldY = (y - this.data.canvasHeight / 2) / scale;

        const points = this.data.fencePoints;
        points.push({ x: worldX, y: worldY });
        this.setData({ fencePoints: points });
        this.drawFencePreview();
    },

    onFenceTouchMove(e) {
        // Reserved for future drag functionality
    },

    onFenceTouchEnd(e) {
        // Reserved for future drag functionality
    },

    clearCanvas() {
        this.setData({ fencePoints: [] });
        this.drawFencePreview();
    },

    saveFence() {
        const fence = {
            id: Date.now(),
            name: '围栏 ' + new Date().toLocaleTimeString(),
            mode: this.data.fenceMode,
            points: this.data.fencePoints,
            radius: this.data.fenceRadius,
            enabled: true
        };
        const saved = [fence, ...this.data.savedFences].slice(0, 10);
        wx.setStorageSync('saved_fences', saved);
        this.setData({ savedFences: saved });
        wx.showToast({ title: '已保存', icon: 'success' });
        this.drawFencePreview();
    },

    deleteFence(e) {
        const id = e.currentTarget.dataset.id;
        const saved = this.data.savedFences.filter(f => f.id !== id);
        wx.setStorageSync('saved_fences', saved);
        this.setData({ savedFences: saved });
        this.drawFencePreview();
    },

    toggleFence(e) {
        const id = e.currentTarget.dataset.id;
        const saved = this.data.savedFences.map(f => f.id === id ? { ...f, enabled: !f.enabled } : f);
        wx.setStorageSync('saved_fences', saved);
        this.setData({ savedFences: saved });
        this.drawFencePreview();
    },

    // Joystick
    onTouchStart() { this.setData({ handleTransition: 'none' }); },
    onTouchMove(e) {
        if (!this.joystickRect) return;
        const touch = e.touches[0];
        const centerX = this.joystickRect.left + this.joystickRect.width / 2;
        const centerY = this.joystickRect.top + this.joystickRect.height / 2;
        let dx = touch.clientX - centerX, dy = touch.clientY - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const maxRadius = this.joystickRect.width / 2 - 22; // Half of 44px
        if (distance > maxRadius) { dx *= maxRadius / distance; dy *= maxRadius / distance; }
        this.setData({ handleLeft: 48 + dx, handleTop: 48 + dy });
        this.sendJoystickData(dx * (100 / maxRadius), -dy * (100 / maxRadius));
    },
    onTouchEnd() {
        this.setData({ handleLeft: 48, handleTop: 48, handleTransition: 'all 0.2s ease' });
        this.sendJoystickData(0, 0);
    },

    // Send joystick data through backend
    sendJoystickData(x, y) {
        const status = udpBackendManager.getConnectionStatus();
        if (!status.connected || !status.carConnected) {
            return;
        }

        const now = Date.now();
        if (x === 0 && y === 0) {
            udpBackendManager.sendControl({ joyX: 0, joyY: 0 });
            return;
        }

        if (this.data.fenceEnabled && this.isOutsideZone) {
            const currentDistSq = this.posX * this.posX + this.posY * this.posY;
            const moveV = y > 0 ? 1 : (y < 0 ? -1 : 0);
            const predX = this.posX + Math.cos(this.heading) * moveV;
            const predY = this.posY + Math.sin(this.heading) * moveV;
            const predDistSq = predX * predX + predY * predY;

            if (predDistSq > currentDistSq) {
                y = 0;
            }
            if (x === 0 && y === 0) return;
        }

        if (now - this.lastSendTime > 50) {
            udpBackendManager.sendControl({ joyX: Math.round(x), joyY: Math.round(y) });
            this.lastSendTime = now;
        }
    },
    onCollapseChange(e) { this.setData({ activeNames: e.detail }); }
});
