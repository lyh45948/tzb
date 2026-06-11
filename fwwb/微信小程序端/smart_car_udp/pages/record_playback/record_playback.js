const networkManager = require('../../utils/network-manager');
const errorHandler = require('../../utils/error-handler');

var recordCanvas = null;
var recordCtx = null;

// Dead Reckoning Constants
const WHEEL_BASELINE = 286; // mm (Corrected for 2x rotation)
const CANVAS_SCALE = 0.5;    // 1mm = 0.5px
const CAMERA_PADDING = 60;   // Padding for dynamic viewport

Page({
    data: {
        connectionStatus: { connected: false, message: '未连接' },
        isRecording: false,
        recordedPath: { id: null, name: '', points: [], timestamp: 0, duration: 0 },
        savedPaths: [],
        recordTime: '00:00',
        activeNames: ['paths'],
        previewPath: null, // Path for visual reference
        canvasWidth: 0,
        canvasHeight: 0,

        // Joystick data
        handleLeft: 50,
        handleTop: 50,
        handleTransition: 'none'
    },

    lastSendTime: 0,
    joystickRect: null,

    // Dead Reckoning & Viewport State
    posX: 0,
    posY: 0,
    heading: -Math.PI / 2,
    lastMsgTime: 0,

    // Camera bounds for auto-expansion
    minX: -10, maxX: 10, minY: -10, maxY: 10,

    onLoad: function () {
        this.loadSavedData();
        this.initNetworkListeners();
        this.updateConnectionStatus();
    },

    onReady: function () {
        this.initCanvas();
        const query = wx.createSelectorQuery();
        query.select('.joystick-container-mini').boundingClientRect(res => {
            this.joystickRect = res;
        }).exec();
    },

    onUnload: function () {
        if (this.data.isRecording) this.stopRecording();
        this.cleanupNetworkListeners();
    },

    initNetworkListeners() {
        this.onConnectionChange = (connected) => { this.updateConnectionStatus(); };
        networkManager.onConnectionChange(this.onConnectionChange);
        this.onMessage = (data) => { this.handleDeviceMessage(data); };
        networkManager.onMessage(this.onMessage);
    },

    cleanupNetworkListeners() {
        if (this.onConnectionChange) networkManager.offConnectionChange(this.onConnectionChange);
        if (this.onMessage) networkManager.offMessage(this.onMessage);
    },

    updateConnectionStatus() {
        const status = networkManager.getConnectionStatus();
        this.setData({ connectionStatus: { connected: status.connected, message: status.connected ? '已连接' : '未连接' } });
    },

    initCanvas() {
        const query = wx.createSelectorQuery();
        query.select('#recordCanvas').fields({ node: true, size: true }).exec((res) => {
            if (!res[0]) return;
            const canvas = res[0].node;
            const ctx = canvas.getContext('2d');
            const dpr = wx.getWindowInfo().pixelRatio;
            canvas.width = res[0].width * dpr;
            canvas.height = res[0].height * dpr;
            ctx.scale(dpr, dpr);
            recordCanvas = canvas;
            recordCtx = ctx;
            this.setData({ canvasWidth: res[0].width, canvasHeight: res[0].height });
            this.resetCarPosition();
            this.render();
        });
    },

    resetCarPosition() {
        this.posX = 0;
        this.posY = 0;
        this.heading = -Math.PI / 2;
        this.minX = -10; this.maxX = 10; this.minY = -10; this.maxY = 10;
        if (!this.data.isRecording) {
            this.setData({ 'recordedPath.points': [] });
        }
    },

    handleDeviceMessage(json) {
        if (!this.data.isRecording) return;

        const now = Date.now();
        if (this.lastMsgTime === 0) { this.lastMsgTime = now; return; }
        const dt = (now - this.lastMsgTime) / 1000;
        this.lastMsgTime = now;

        // Kinematics: Using global WHEEL_BASELINE (286)
        const SCALE_FACTOR = 0.4825;

        // Get signed speeds from protocol
        const vL = (json.L_spd !== undefined ? json.L_spd : 0) * SCALE_FACTOR;
        const vR = (json.R_spd !== undefined ? json.R_spd : 0) * SCALE_FACTOR;

        const v = (vL + vR) / 2;
        const omega = (vL - vR) / WHEEL_BASELINE;

        // Exact Integration (Constant Curvature)
        if (Math.abs(omega) < 0.001) {
            this.posX += v * Math.cos(this.heading) * dt * CANVAS_SCALE;
            this.posY += v * Math.sin(this.heading) * dt * CANVAS_SCALE;
        } else {
            const dTheta = omega * dt;
            this.posX += (v / omega) * (Math.sin(this.heading + dTheta) - Math.sin(this.heading)) * CANVAS_SCALE;
            this.posY -= (v / omega) * (Math.cos(this.heading + dTheta) - Math.cos(this.heading)) * CANVAS_SCALE;
            this.heading += dTheta;
        }

        // Keep heading in [-PI, PI]
        while (this.heading > Math.PI) this.heading -= 2 * Math.PI;
        while (this.heading < -Math.PI) this.heading += 2 * Math.PI;

        // Track trajectory
        const points = this.data.recordedPath.points;
        if (points.length === 0 || Math.sqrt(Math.pow(this.posX - points[points.length - 1].x, 2) + Math.pow(this.posY - points[points.length - 1].y, 2)) > 2) {
            points.push({ x: this.posX, y: this.posY });
            this.setData({ 'recordedPath.points': points });

            this.minX = Math.min(this.minX, this.posX);
            this.maxX = Math.max(this.maxX, this.posX);
            this.minY = Math.min(this.minY, this.posY);
            this.maxY = Math.max(this.maxY, this.posY);
        }

        this.render();
    },

    render() {
        if (!recordCtx) return;
        const ctx = recordCtx;
        const w = this.data.canvasWidth;
        const h = this.data.canvasHeight;

        ctx.save();
        ctx.clearRect(0, 0, w, h);

        // Viewport Math
        // Calculate bounds combining current path AND preview path
        let minX = this.minX, maxX = this.maxX, minY = this.minY, maxY = this.maxY;
        if (this.data.previewPath && this.data.previewPath.points.length > 0) {
            this.data.previewPath.points.forEach(p => {
                minX = Math.min(minX, p.x);
                maxX = Math.max(maxX, p.x);
                minY = Math.min(minY, p.y);
                maxY = Math.max(maxY, p.y);
            });
        }

        const contentW = (maxX - minX) + CAMERA_PADDING * 2;
        const contentH = (maxY - minY) + CAMERA_PADDING * 2;
        const scale = Math.min(w / contentW, h / contentH, 1.0);

        const offsetX = w / 2 - (minX + maxX) / 2 * scale;
        const offsetY = h / 2 - (minY + maxY) / 2 * scale;

        ctx.translate(offsetX, offsetY);
        ctx.scale(scale, scale);

        // Draw Reference Grid
        this.drawGrid(ctx);

        // Draw Historical Preview Path
        if (this.data.previewPath && this.data.previewPath.points.length >= 2) {
            const preview = this.data.previewPath.points;
            ctx.beginPath();
            ctx.moveTo(preview[0].x, preview[0].y);
            for (let i = 1; i < preview.length; i++) ctx.lineTo(preview[i].x, preview[i].y);
            ctx.strokeStyle = 'rgba(150, 150, 150, 0.4)'; // Dotted grey
            ctx.setLineDash([5 / scale, 5 / scale]);
            ctx.lineWidth = 2 / scale;
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Draw Currently Recorded Path
        const points = this.data.recordedPath.points;
        if (points.length >= 2) {
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
            ctx.strokeStyle = '#07c160';
            ctx.lineWidth = 3 / scale;
            ctx.lineCap = 'round';
            ctx.stroke();
        }

        // Draw Start Marker
        if (points.length > 0) {
            ctx.fillStyle = '#ee0a24';
            ctx.beginPath();
            ctx.arc(points[0].x, points[0].y, 5 / scale, 0, Math.PI * 2);
            ctx.fill();
        }

        // Draw Current Car
        ctx.save();
        ctx.translate(this.posX, this.posY);
        ctx.rotate(this.heading + Math.PI / 2);
        ctx.beginPath();
        ctx.moveTo(0, -8); ctx.lineTo(6, 6); ctx.lineTo(-6, 6);
        ctx.closePath();
        ctx.fillStyle = '#ee0a24';
        ctx.fill();
        ctx.restore();

        ctx.restore();
    },

    previewPath(e) {
        const id = e.currentTarget.dataset.id;
        const path = this.data.savedPaths.find(p => p.id === id);
        if (path) {
            this.setData({ previewPath: path });
            this.render();
            wx.showToast({ title: '预览已加载', icon: 'none' });
        }
    },

    drawGrid(ctx) {
        const step = 50;
        const startX = Math.floor(this.minX / step) * step - step * 2;
        const endX = Math.ceil(this.maxX / step) * step + step * 2;
        const startY = Math.floor(this.minY / step) * step - step * 2;
        const endY = Math.ceil(this.maxY / step) * step + step * 2;
        ctx.strokeStyle = '#f2f3f5';
        ctx.lineWidth = 1;
        for (let x = startX; x <= endX; x += step) {
            ctx.beginPath(); ctx.moveTo(x, startY); ctx.lineTo(x, endY); ctx.stroke();
        }
        for (let y = startY; y <= endY; y += step) {
            ctx.beginPath(); ctx.moveTo(startX, y); ctx.lineTo(endX, y); ctx.stroke();
        }
    },

    loadSavedData() {
        const paths = wx.getStorageSync('saved_paths') || [];
        this.setData({ savedPaths: paths });
    },

    onRecordButtonClick() {
        if (this.data.isRecording) this.stopRecording();
        else this.startRecording();
    },

    startRecording() {
        this.resetCarPosition();
        this.lastMsgTime = 0;
        this.setData({
            isRecording: true,
            recordedPath: { id: Date.now(), name: '录制 ' + new Date().toLocaleTimeString(), points: [], timestamp: Date.now(), duration: 0 },
            recordTime: '00:00'
        });

        this.recordTimer = setInterval(() => {
            const elapsed = Date.now() - this.data.recordedPath.timestamp;
            const minutes = Math.floor(elapsed / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            this.setData({
                recordTime: `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`,
                'recordedPath.duration': elapsed
            });
        }, 1000);
    },

    stopRecording() {
        clearInterval(this.recordTimer);
        const path = this.data.recordedPath;
        if (path.points.length < 5) {
            wx.showToast({ title: '记录点不足', icon: 'none' });
            this.setData({ isRecording: false });
            return;
        }
        const savedPaths = this.data.savedPaths;
        path.durationStr = Math.floor(path.duration / 1000) + '秒';
        savedPaths.unshift(path);
        wx.setStorageSync('saved_paths', savedPaths.slice(0, 20));
        this.setData({ isRecording: false, savedPaths: savedPaths.slice(0, 20) });
    },

    playRecordedPath(e) {
        const id = e.currentTarget.dataset.id;
        const path = this.data.savedPaths.find(p => p.id === id);
        if (!path) return;
        this.setData({ previewPath: path });
        this.render();
        networkManager.send({ carMode: 'path', path: this.simplifyPath(path.points) });
        wx.showToast({ title: '正在播放', icon: 'success' });
    },

    simplifyPath(points) {
        const pixelToMm = 1 / CANVAS_SCALE;
        const playbackScale = 1.0;
        const commands = []; let currentAngle = 0;
        for (let i = 1; i < points.length; i += 5) {
            const p1 = points[i - 1], p2 = points[Math.min(i + 4, points.length - 1)], dx = p2.x - p1.x, dy = p2.y - p1.y;
            const dist = Math.sqrt(dx * dx + dy * dy) * pixelToMm * playbackScale, angleDeg = Math.atan2(dx, -dy) * (180 / Math.PI);
            let turnAngle = angleDeg - currentAngle;
            while (turnAngle > 180) turnAngle -= 360; while (turnAngle < -180) turnAngle += 360;
            commands.push({ d: Math.round(dist), a: Math.round(turnAngle) });
            currentAngle = angleDeg; if (i + 4 >= points.length - 1) break;
        }
        return commands;
    },

    deletePath(e) {
        const id = e.currentTarget.dataset.id;
        const savedPaths = this.data.savedPaths.filter(p => p.id !== id);
        wx.setStorageSync('saved_paths', savedPaths);
        this.setData({ savedPaths });
    },

    // Joystick Logic
    onTouchStart() { this.setData({ handleTransition: 'none' }); },
    onTouchMove(e) {
        if (!this.joystickRect) return;
        const touch = e.touches[0];
        const centerX = this.joystickRect.left + this.joystickRect.width / 2;
        const centerY = this.joystickRect.top + this.joystickRect.height / 2;
        let dx = touch.clientX - centerX, dy = touch.clientY - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy), maxRadius = this.joystickRect.width / 2 - 30;
        if (distance > maxRadius) { dx *= maxRadius / distance; dy *= maxRadius / distance; }
        this.setData({ handleLeft: 50 + dx, handleTop: 50 + dy });
        this.sendJoystickData(dx * (100 / maxRadius), -dy * (100 / maxRadius));
    },
    onTouchEnd() {
        this.setData({ handleLeft: 50, handleTop: 50, handleTransition: 'all 0.2s ease' });
        this.sendJoystickData(0, 0);
    },
    sendJoystickData(x, y) {
        const now = Date.now();
        if (x === 0 && y === 0) networkManager.send({ joyX: 0, joyY: 0 });
        else if (now - this.lastSendTime > 50) {
            networkManager.send({ joyX: Math.round(x), joyY: Math.round(y) });
            this.lastSendTime = now;
        }
    },
    onResetCanvas() {
        this.resetCarPosition();
        this.setData({
            previewPath: null,
            'recordedPath.points': []
        });
        this.render();
        wx.showToast({ title: '已清空画布', icon: 'none' });
    }
});
