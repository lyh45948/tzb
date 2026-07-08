<template>
  <Teleport to="body">
    <div class="dialog-mask" @click.self="emit('close')">
    <div class="dialog-card">
      <div class="dialog-header">
        <span class="dialog-title">连接小车</span>
        <button class="icon-btn" @click="emit('close')" aria-label="关闭">×</button>
      </div>

      <!-- 连接表单 -->
      <section class="section">
        <h4 class="section-title">输入小车地址</h4>
        <div class="form-row">
          <label class="field">
            <span>IP 地址</span>
            <input
              v-model.trim="form.carIp"
              type="text"
              placeholder="例如 192.168.1.123"
              :disabled="connecting"
              @keyup.enter="onConnect"
            />
          </label>
          <label class="field field-port">
            <span>端口</span>
            <input
              v-model.number="form.carPort"
              type="number"
              min="1"
              max="65535"
              :disabled="connecting"
              @keyup.enter="onConnect"
            />
          </label>
          <label class="field">
            <span>Device ID（可选）</span>
            <input
              v-model.trim="form.deviceId"
              type="text"
              placeholder="留空自动生成"
              :disabled="connecting"
              @keyup.enter="onConnect"
            />
          </label>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" :disabled="connecting" @click="onConnect">
            {{ connecting ? '连接中…' : '连接' }}
          </button>
          <span v-if="formError" class="error-text">{{ formError }}</span>
          <span v-else-if="formInfo" class="info-text">{{ formInfo }}</span>
        </div>
      </section>

      <!-- 已连接列表 -->
      <section class="section">
        <div class="section-head">
          <h4 class="section-title">已连接小车</h4>
          <button class="btn btn-link" :disabled="loadingList" @click="refreshList">
            {{ loadingList ? '刷新中…' : '刷新' }}
          </button>
        </div>
        <ul v-if="cars.length" class="car-list">
          <li v-for="c in cars" :key="c.device_id" class="car-row">
            <span class="dot" :class="c.connected ? 'on' : 'off'"></span>
            <div class="car-meta">
              <div class="car-id">{{ c.device_id }}</div>
              <div class="car-addr">{{ c.car_ip }}:{{ c.car_port }}</div>
            </div>
            <button
              class="btn btn-danger"
              :disabled="busyId === c.device_id"
              @click="onDisconnect(c.device_id)"
            >
              {{ busyId === c.device_id ? '断开中…' : '断开' }}
            </button>
          </li>
        </ul>
        <div v-else class="empty-text">暂无已连接小车</div>
        <div v-if="listError" class="error-text">{{ listError }}</div>
      </section>

      <div class="dialog-footer">
        <button class="btn" @click="emit('close')">关闭</button>
      </div>
    </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ApiError, connectCar, disconnectCar, listCars } from '../../services/api'

const emit = defineEmits(['close', 'connected'])

const form = reactive({
  carIp: '',
  carPort: 7788,
  deviceId: '',
})
const connecting = ref(false)
const formError = ref('')
const formInfo = ref('')

const cars = ref([])
const loadingList = ref(false)
const listError = ref('')
const busyId = ref(null)

const IPV4_RE = /^(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d)$/

onMounted(refreshList)

async function refreshList() {
  loadingList.value = true
  listError.value = ''
  try {
    const data = await listCars()
    // /v1/agv/cars 也会包含离线/有历史任务记录的车，对话框只关心真实在连的
    cars.value = Array.isArray(data) ? data.filter((c) => c?.connected) : []
  } catch (e) {
    cars.value = []
    listError.value = e instanceof ApiError ? e.message : String(e)
  } finally {
    loadingList.value = false
  }
}

async function onConnect() {
  formError.value = ''
  formInfo.value = ''
  const ip = form.carIp
  if (!ip) {
    formError.value = '请输入小车 IP'
    return
  }
  if (!IPV4_RE.test(ip)) {
    formError.value = 'IP 格式不合法（应为 IPv4，例如 192.168.1.123）'
    return
  }
  const port = Number(form.carPort) || 7788
  if (port < 1 || port > 65535) {
    formError.value = '端口必须在 1-65535'
    return
  }

  connecting.value = true
  try {
    const result = await connectCar({
      carIp: ip,
      carPort: port,
      deviceId: form.deviceId || undefined,
    })
    formInfo.value = `已连接 ${result?.deviceId || ip}`
    emit('connected', result)
    // 清除 deviceId 输入；保留 ip/port 方便用户下次微调
    form.deviceId = ''
    await refreshList()
  } catch (e) {
    formError.value = e instanceof ApiError ? e.message : String(e)
  } finally {
    connecting.value = false
  }
}

async function onDisconnect(deviceId) {
  busyId.value = deviceId
  listError.value = ''
  try {
    await disconnectCar(deviceId)
    await refreshList()
  } catch (e) {
    listError.value = e instanceof ApiError ? e.message : String(e)
  } finally {
    busyId.value = null
  }
}
</script>

<style scoped>
.dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}
.dialog-card {
  width: min(520px, 100%);
  max-height: 90vh;
  overflow: auto;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.25);
  padding: 18px 20px 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.dialog-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
}
.icon-btn {
  background: transparent;
  border: none;
  font-size: 22px;
  line-height: 1;
  color: var(--text-secondary, #64748b);
  cursor: pointer;
  padding: 0 6px;
}
.icon-btn:hover { color: var(--text-primary, #1e293b); }

.section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}
.section:last-of-type { border-bottom: none; }
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  letter-spacing: 0.5px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 110px;
  gap: 10px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary, #64748b);
}
.field input {
  height: 32px;
  padding: 0 10px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  outline: none;
}
.field input:focus { border-color: var(--accent-blue, #2563eb); }
.field input:disabled { background: #f1f5f9; cursor: not-allowed; }
.field-port { grid-column: 2 / 3; }
.field:nth-of-type(3) { grid-column: 1 / -1; }

.form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-primary, #1e293b);
}
.btn:hover:not(:disabled) { background: #f8fafc; }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary {
  background: var(--accent-blue, #2563eb);
  border-color: var(--accent-blue, #2563eb);
  color: #fff;
}
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-danger {
  border-color: #ef4444;
  color: #dc2626;
}
.btn-danger:hover:not(:disabled) { background: #fef2f2; }
.btn-link {
  background: transparent;
  border: none;
  color: var(--accent-blue, #2563eb);
  padding: 0;
  height: auto;
}

.error-text { color: #dc2626; font-size: 12px; }
.info-text { color: #16a34a; font-size: 12px; }
.empty-text { color: var(--text-secondary, #64748b); font-size: 12px; padding: 4px 0; }

.car-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.car-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  background: #f8fafc;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot.on { background: #16a34a; box-shadow: 0 0 4px #16a34a; }
.dot.off { background: #94a3b8; }
.car-meta { flex: 1; min-width: 0; }
.car-id {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.car-addr {
  font-size: 12px;
  color: var(--text-secondary, #64748b);
  font-family: 'Consolas', monospace;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
