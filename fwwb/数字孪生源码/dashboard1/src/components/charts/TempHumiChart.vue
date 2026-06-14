<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>温湿度监测</div>
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
      { data: store.historyHumi }
    ]
  })
}

onMounted(() => {
  chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['温度(℃)', '湿度(%)'], textStyle: { color: '#64748b', fontSize: 13 }, top: 0 },
    grid: { left: '3%', right: '4%', top: 35, bottom: '5%', containLabel: true },
    xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: '#cbd5e1' } }, axisLabel: { color: '#64748b', fontSize: 11, interval: 9 }, splitLine: { show: false } },
    yAxis: [
      { type: 'value', name: '℃', nameTextStyle: { color: '#64748b', fontSize: 12 }, axisLabel: { color: '#64748b', fontSize: 12 }, splitLine: { lineStyle: { color: '#cbd5e1' } }, min: 10, max: 45 },
      { type: 'value', name: '%', nameTextStyle: { color: '#64748b', fontSize: 12 }, axisLabel: { color: '#64748b', fontSize: 12 }, splitLine: { show: false }, min: 20, max: 100 }
    ],
    series: [
      { name: '温度(℃)', type: 'line', smooth: true, symbol: 'none', lineStyle: { color: '#ef4444', width: 2 }, itemStyle: { color: '#ef4444' }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(239,68,68,0.25)' }, { offset: 1, color: 'rgba(239,68,68,0)' }]) }, data: [] },
      { name: '湿度(%)', type: 'line', smooth: true, symbol: 'none', yAxisIndex: 1, lineStyle: { color: '#2563eb', width: 2 }, itemStyle: { color: '#2563eb' }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(37,99,235,0.25)' }, { offset: 1, color: 'rgba(37,99,235,0)' }]) }, data: [] }
    ]
  })
  startResize()
})

watch(() => store.historyLabels.length, updateChart)
onUnmounted(() => { if (chart) chart.dispose() })
</script>
