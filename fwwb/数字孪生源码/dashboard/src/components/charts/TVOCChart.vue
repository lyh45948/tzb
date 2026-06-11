<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>TVOC趋势</div>
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
    series: [{ data: store.historyTVOC }]
  })
}

onMounted(() => {
  chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>TVOC: {c} ppb'
    },
    grid: { left: '3%', right: '4%', top: 20, bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: [],
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b', fontSize: 11, interval: 9 },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: 'ppb',
      nameTextStyle: { color: '#64748b', fontSize: 12 },
      min: 0,
      max: 1200,
      axisLabel: { color: '#64748b', fontSize: 12 },
      splitLine: { lineStyle: { color: '#cbd5e1' } }
    },
    series: [{
      name: 'TVOC',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#06b6d4', width: 2 },
      itemStyle: { color: '#06b6d4' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(6,182,212,0.28)' },
          { offset: 1, color: 'rgba(6,182,212,0)' }
        ])
      },
      data: []
    }]
  })
  startResize()
})

watch(() => store.historyLabels.length, updateChart)
onUnmounted(() => { if (chart) chart.dispose() })
</script>
