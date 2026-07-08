import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import '@/assets/css/main.scss'
import '@/assets/css/tailwind.css'
// dashboard1 迁移: Three.js CSS2DRenderer 标签所需的全局样式 (适配深色主题)
import '@/assets/css/three-labels.css'
// 工厂数字孪生深色科技主题 (覆盖迁移组件的浅色 CSS 变量 + 隐藏内联 panel-frame)
import '@/assets/css/factory-theme.css'

import {registerEcharts} from "@/plugins/echarts"

// 工厂数字孪生大屏: 使用 deviceStore 自带的模拟/SSE/轮询数据, 不使用 IofTV 原生 mock
// import { mockXHR } from "@/mock/index";
// mockXHR()

const app = createApp(App)
registerEcharts(app)
app.use(createPinia())
app.use(router)

app.mount('#app')
