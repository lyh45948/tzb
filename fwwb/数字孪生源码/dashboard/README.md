# 智能小车数字孪生大屏 (Smart Car Digital Twin Dashboard)

## 项目概述
本项目是一个基于 Web 技术的数字孪生大屏前端项目，主要用于实时监控和展示智能小车的状态、传感器数据以及 3D 实时模型。

## 技术栈 (Tech Stack)
* **核心框架**: Vue 3 (Composition API / `<script setup>`)
* **构建工具**: Vite 5
* **状态管理**: Pinia 2
* **3D 引擎**: Three.js (`^0.160.0`)
* **数据可视化**: ECharts (`^5.4.3`)

## 目录结构分析 (Directory Structure)

* **`src/components/`**: UI 组件库
  * `layout/`: 大屏布局组件（如 `DashboardLayout.vue` 主要拼装页面结构）。
  * `three/`: 3D 渲染视图，结合 Three.js 展示小车的数字孪生三维模型。
  * `charts/`: 图表组件，基于 ECharts 封装，用于各种数据指标的图形展示。
  * `panels/`: 业务面板组件，展示特定模块的信息（例如传感器面板、控制面板）。
  * `common/`: 通用的原子级别 UI 组件。
* **`src/stores/`**: 状态管理中心
  * `deviceStore.js`: 维护小车的全局状态，包含设备连接状态、传感器实时数据等。
* **`src/composables/`**: Vue 组合式函数 (Hooks)，实现逻辑复用
  * `useWebSocket.js`: 封装 WebSocket 客户端功能，负责数据实时推送。
  * `useRealtimeData.js`: 处理实时数据流的逻辑。
  * `useHistoryData.js`: 处理历史数据的获取和处理（基于 REST API）。
* **`src/utils/`**: 工具函数库
  * `constants.js`: 定义项目中的全局常量（如枚举、配置字段等）。
  * `dataFormatter.js`: 数据格式化工具，将后端原始数据转换为图表或 UI 渲染可以直接使用的格式。
* **`src/config.js`**: 环境及参数配置
  * 包含了 WebSocket 地址 (`ws://localhost:9090`) 和 REST API 基础地址 (`http://localhost:8889`)。
  * 配置了图表刷新间隔（500ms）及实时报表的最大数据点数（60）。

## 通信协议

1. **WebSocket ( ws://localhost:9090 )**: 承担小车运行状态、姿态及高频环境感测数据的实时下发，实现数字孪生系统页面的低延迟刷新。
2. **HTTP API ( http://localhost:8889 )**: 通过常规请求获取小车历史轨迹或设备配置等静态数据。

## 布局设计与响应式策略

针对数字大屏数据密集、高度受限的特点，系统采用了以下自适应方案：

*   **侧边栏**：左右栏根据图表重要性设置了不同的垂直占比，并引入隐藏域滚动 `overflow-y: auto` 以保障狭长屏幕下的查阅。
*   **网格图表自包裹**：折线图全局启用 `containLabel: true`，结合相对百分比安全外框，解决坐标数值重叠。
*   **仪防越界表盘**：中心焦点向下微提，限制在安全半径中，防止仪表被顶端或底端截断。


---
*本文档由 AI 助手阅读代码自动生成。*
