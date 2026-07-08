<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>安全数据趋势</div>
    <div class="panel-body">
      <div ref="chartEl" style="width:100%;height:100%"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { useDeviceStore } from '../../stores/deviceStore'
import { useChartResize } from '../../composables/useChartResize'
import config from '../../config'

const chartEl = ref(null)
let chart = null
const store = useDeviceStore()

const { start: startResize } = useChartResize(chartEl, () => chart)
const chartAnimationDuration = config.chartUpdateInterval || 1000

function updateChart() {
  if (!chart || !store.historyLabels.length) return
  chart.setOption({
    animationDurationUpdate: chartAnimationDuration,
    animationEasingUpdate: 'linear',
    xAxis: { data: store.historyLabels },
    series: [
      { data: store.historyTemp },
      { data: store.historyHumi },
      { data: store.historyCO2 },
      { data: store.historyTVOC },
      { data: store.historyGasMic }
    ]
  })
}

onMounted(() => {
  chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chart.setOption({
    animationDuration: chartAnimationDuration,
    animationDurationUpdate: chartAnimationDuration,
    animationEasing: 'linear',
    animationEasingUpdate: 'linear',
    tooltip: { trigger: 'axis' },
    legend: { data: ['温度(℃)', '湿度(%)', 'CO(ppm)', 'TVOC(ppb)', '危气(ppm)'], textStyle: { color: '#64748b', fontSize: 12 }, top: 4, left: 'center' },
    grid: { left: 50, right: 160, top: 36, bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category', data: [],
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b', fontSize: 11, interval: 9 },
      splitLine: { show: false }
    },
    yAxis: [
      { type: 'value', name: '℃/%', min: 0, max: 100, nameLocation: 'middle', nameGap: 36, nameRotate: 90, nameTextStyle: { color: '#64748b', fontSize: 12 }, axisLabel: { color: '#64748b', fontSize: 12 }, splitLine: { lineStyle: { color: '#cbd5e1' } } },
      { type: 'value', name: 'TVOC', min: 0, max: 1200, nameLocation: 'middle', nameGap: 36, nameRotate: 90, nameTextStyle: { color: '#06b6d4', fontSize: 12 }, axisLabel: { color: '#06b6d4', fontSize: 12 }, splitLine: { show: false }, position: 'right' },
      { type: 'value', name: '危气', min: 0, max: 1200, nameLocation: 'middle', nameGap: 36, nameRotate: 90, nameTextStyle: { color: '#f59e0b', fontSize: 12 }, axisLabel: { color: '#f59e0b', fontSize: 12 }, splitLine: { show: false }, position: 'right', offset: 50 },
      // CO 量级 0~80 ppm 独占第四轴，避免与 ppb 量级混轴
      { type: 'value', name: 'CO ppm', position: 'right', offset: 100, min: 0, max: 80, nameLocation: 'middle', nameGap: 28, nameRotate: -90, nameTextStyle: { color: '#8b5cf6', fontSize: 12 }, axisLine: { show: true, lineStyle: { color: '#8b5cf6' } }, axisLabel: { color: '#8b5cf6', fontSize: 12 }, splitLine: { show: false } }
    ],
    series: [
      { name: '温度(℃)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#ef4444' }, itemStyle: { color: '#ef4444' }, data: [] },
      { name: '湿度(%)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#2563eb' }, itemStyle: { color: '#2563eb' }, data: [] },
      { name: 'CO(ppm)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 3, lineStyle: { color: '#8b5cf6' }, itemStyle: { color: '#8b5cf6' }, data: [] },
      { name: 'TVOC(ppb)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { color: '#06b6d4', type: 'dashed' }, itemStyle: { color: '#06b6d4' }, data: [] },
      { name: '危气(ppm)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 2, lineStyle: { color: '#f59e0b', type: 'dashed', width: 1.5 }, itemStyle: { color: '#f59e0b' }, data: [] }
    ]
  })
  startResize()
})

watch(() => store.historyLabels, updateChart, { deep: true })
onUnmounted(() => { if (chart) chart.dispose() })
</script>
