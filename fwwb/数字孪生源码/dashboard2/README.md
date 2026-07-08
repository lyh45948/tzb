# 工厂数字孪生安全监测监控大屏 (dashboard2)

> 基于 [IofTV-Screen-Vue3](https://github.com/daidaibg/IofTV-Screen-Vue3) (MIT) 深色科技大屏视觉外壳，整合 `dashboard1` 的数据层 / Three.js 3D 工厂场景 / 9 模块业务。

## 与 dashboard1 的关系

`dashboard2` 是 `dashboard1` 的**视觉重做版**。`dashboard1` 的数据/逻辑/3D 场景写得很扎实，但视觉是浅色商务风、缺乏大屏装饰件、排版混乱。本目录用 IofTV 的深色科技外壳替换视觉层，**原样保留** dashboard1 的：

- 数据层：`src/config.js` + `src/services/*` + `src/stores/deviceStore.js` + `src/utils/*`
- 3D 场景：`src/components/three/*`（CarModel / SceneEnvironment / AnimationController / CarScene）
- 业务面板/图表：`src/components/panels/*` + `src/components/charts/*`
- 连接小车对话框：`src/components/dialogs/CarConnectDialog.vue`
- 9 模块定义：`src/modules/dashboardModules.js`

## 技术栈

| 层 | 技术 |
|---|---|
| 框架 | Vue 3 + TypeScript（allowJs 兼容 dashboard1 的 .js） |
| 构建 | Vite 8（端口 8112） |
| 状态 | Pinia |
| 图表 | ECharts 6（dashboard1 组件用 `import * as echarts`，IofTV 用 vue-echarts `<v-chart>`） |
| 3D | Three.js 0.160 |
| 样式 | Tailwind v4 + SCSS + 原生 CSS（`factory-theme.css` 深色主题覆盖） |
| 路由 | vue-router（单页，9 模块靠 `activeModule` ref + `<component :is>` 切换，非路由） |

## 架构要点

```
HomeView.vue (scale-screen 1920×1080 自适应壳)
├── header.vue (标题栏 + 9模块切换Tab + 在线/告警状态 + 连接小车)
├── <component :is="activeSection" />  ← 9 模块切换
│   ├── OverviewSection  总览大屏(左指标+中3D场景+右趋势)
│   ├── EnvironmentSection / GasSafetySection / AgvSection ...
│   └── (每模块内部用 <ItemWrap> 包裹 BorderBox13 科技边框)
└── 数据流: onMounted → dashboardClient.start(store) → live(SSE)→polling→demo
```

## 深色主题适配

dashboard1 的组件内联了浅色 `.panel-frame` 外壳，本目录通过 `src/assets/css/factory-theme.css` 全局覆盖：

- 重映射 CSS 变量（`--bg-panel` 浅色 → 深色 `rgba(8,18,40,0.6)` 等）
- 把内联 `.panel-frame` 透明化（标题/边框由 `ItemWrap` 的 BorderBox13 统一提供）
- 3D 标签样式提取到 `src/assets/css/three-labels.css`（从白底改为深色霓虹）

## 开发

```bash
cd fwwb/数字孪生源码/dashboard2
npm install          # 已配置淘宝镜像
npm run dev          # http://localhost:8112
npm run build        # 生产构建
```

数据来源：默认 `enableLiveData=true`，尝试连接 `http://localhost:5000`（Flask 后端），失败自动降级到本地模拟。强制模拟模式设 `.env.development` 的 `VITE_ENABLE_LIVE_DATA=false`。

### 端口占用排查

若 `npm run dev` 提示 `Port 8112 is in use` 或浏览器报陈旧的 import 错误，通常是**残留的旧 dev server 进程**。清理：

```bash
# 查占用 8112 的进程
lsof -i :8112
# 杀掉后重启
kill -9 <PID>
rm -rf node_modules/.vite   # 清 Vite 依赖缓存
npm run dev
# 浏览器硬刷新 Ctrl+Shift+R 或开无痕窗口
```

## 注意

- `.gitignore` 全局忽略 `*.png`，本目录的 IofTV 装饰图片已用 `git add -f` 强制纳入版本控制。
- `node_modules/` 被 gitignore，不含 21k 个依赖文件。
- IofTV 原生 mock（`src/mock/`）已禁用（`main.ts` 注释），改用 dashboard1 的数据状态机。
