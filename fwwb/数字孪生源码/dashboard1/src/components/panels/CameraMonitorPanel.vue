<template>
  <div class="panel-frame camera-monitor">
    <div class="panel-header"><span class="dot"></span>摄像头监测</div>
    <div class="panel-body camera-grid">
      <div v-for="camera in cameras" :key="camera.name" class="camera-card">
        <div class="camera-feed" :class="camera.className">
          <div class="scan-line"></div>
          <div class="corner lt"></div>
          <div class="corner rt"></div>
          <div class="corner lb"></div>
          <div class="corner rb"></div>
          <div class="camera-overlay">
            <span class="live-dot"></span>
            <span>LIVE</span>
          </div>
          <div class="camera-crosshair"></div>
        </div>
        <div class="camera-meta">
          <span class="camera-name">{{ camera.name }}</span>
          <span class="camera-status">{{ camera.status }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const cameras = [
  { name: '检测一', status: '运行中', className: 'feed-one' },
  { name: '检测二', status: '运行中', className: 'feed-two' },
  { name: '检测三', status: '运行中', className: 'feed-three' }
]
</script>

<style scoped>
.camera-monitor { min-height: 0; }
.camera-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  min-height: 0;
}

.camera-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  border-radius: 8px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.14);
}

.camera-feed {
  position: relative;
  flex: 1;
  min-height: 130px;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.88), rgba(30, 64, 175, 0.72)),
    repeating-linear-gradient(0deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 7px);
}
.camera-feed::before {
  content: '';
  position: absolute;
  inset: 18% 12%;
  border-radius: 10px;
  background:
    linear-gradient(90deg, transparent 0 22%, rgba(148, 163, 184, 0.32) 22% 24%, transparent 24% 46%, rgba(148, 163, 184, 0.22) 46% 48%, transparent 48%),
    linear-gradient(0deg, rgba(148, 163, 184, 0.20), rgba(15, 23, 42, 0.12));
  box-shadow: inset 0 0 28px rgba(6, 182, 212, 0.16);
}
.feed-two { background: linear-gradient(135deg, rgba(20, 83, 45, 0.82), rgba(15, 23, 42, 0.88)); }
.feed-three { background: linear-gradient(135deg, rgba(88, 28, 135, 0.78), rgba(15, 23, 42, 0.90)); }

.scan-line {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.9), transparent);
  animation: scan 3.2s linear infinite;
}
@keyframes scan {
  from { transform: translateY(0); }
  to { transform: translateY(150px); }
}

.camera-overlay {
  position: absolute;
  top: 8px;
  left: 8px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 7px;
  border-radius: 999px;
  color: #fff;
  font-size: 10px;
  font-family: Consolas, monospace;
  background: rgba(15, 23, 42, 0.68);
}
.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}

.corner {
  position: absolute;
  width: 18px;
  height: 18px;
  border-color: rgba(34, 211, 238, 0.85);
}
.lt { top: 10px; left: 10px; border-top: 2px solid; border-left: 2px solid; }
.rt { top: 10px; right: 10px; border-top: 2px solid; border-right: 2px solid; }
.lb { bottom: 10px; left: 10px; border-bottom: 2px solid; border-left: 2px solid; }
.rb { bottom: 10px; right: 10px; border-bottom: 2px solid; border-right: 2px solid; }

.camera-crosshair {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 34px;
  height: 34px;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(34, 211, 238, 0.45);
  border-radius: 50%;
}
.camera-crosshair::before,
.camera-crosshair::after {
  content: '';
  position: absolute;
  background: rgba(34, 211, 238, 0.45);
}
.camera-crosshair::before { left: 50%; top: -8px; width: 1px; height: 50px; }
.camera-crosshair::after { left: -8px; top: 50%; width: 50px; height: 1px; }

.camera-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 9px;
  background: rgba(255, 255, 255, 0.72);
}
.camera-name {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 800;
}
.camera-status {
  color: #16a34a;
  font-size: 11px;
  font-weight: 700;
}

@media (prefers-reduced-motion: reduce) {
  .scan-line { animation: none; }
}
</style>
