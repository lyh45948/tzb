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

const chartEl = ref(null)
let chart = null
const store = useDeviceStore()

const { start: startResize } = useChartResize(chartEl, () => chart)

function updateChart() {
  if (!chart || !store.historyLabels.length) return
  chart.setOption({
    xAxis: { data: store.historyLabels },
    series: [
      { data: store.historyTemp },
      { data: store.historyHumi },
      { data: store.historyCO2 },
      { data: store.historyTVOC },
      { data: store.historySmartLight }
    ]
  })
}

onMounted(() => {
  chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['温度(℃)', '湿度(%)', 'CO₂(ppm)', 'TVOC(ppb)', '亮度(%)'], textStyle: { color: '#64748b', fontSize: 12 }, top: 0 },
    grid: { left: '3%', right: '4%', top: 35, bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category', data: [],
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b', fontSize: 11, interval: 9 },
      splitLine: { show: false }
    },
    yAxis: [
      { type: 'value', name: '℃/%', min: 0, max: 100, nameTextStyle: { color: '#64748b', fontSize: 12 }, axisLabel: { color: '#64748b', fontSize: 12 }, splitLine: { lineStyle: { color: '#cbd5e1' } } },
      { type: 'value', name: 'ppm/ppb', min: 0, max: 1400, nameTextStyle: { color: '#64748b', fontSize: 12 }, axisLabel: { color: '#64748b', fontSize: 12 }, splitLine: { show: false } }
    ],
    series: [
      { name: '温度(℃)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#ef4444' }, itemStyle: { color: '#ef4444' }, data: [] },
      { name: '湿度(%)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#2563eb' }, itemStyle: { color: '#2563eb' }, data: [] },
      { name: 'CO₂(ppm)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { color: '#8b5cf6' }, itemStyle: { color: '#8b5cf6' }, data: [] },
      { name: 'TVOC(ppb)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { color: '#06b6d4', type: 'dashed' }, itemStyle: { color: '#06b6d4' }, data: [] },
      { name: '亮度(%)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#f59e0b', type: 'dashed', width: 1.5 }, itemStyle: { color: '#f59e0b' }, data: [] }
    ]
  })
  startResize()
})

watch(() => store.historyLabels.length, updateChart)
onUnmounted(() => { if (chart) chart.dispose() })
</script>
