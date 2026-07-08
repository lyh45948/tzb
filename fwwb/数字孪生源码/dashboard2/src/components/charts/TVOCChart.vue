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
    series: [{ data: store.historyTVOC }]
  })
}

onMounted(() => {
  chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chart.setOption({
    animationDuration: chartAnimationDuration,
    animationDurationUpdate: chartAnimationDuration,
    animationEasing: 'linear',
    animationEasingUpdate: 'linear',
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>TVOC: {c} ppb',
      backgroundColor: 'rgba(8,18,40,0.9)',
      borderColor: 'rgba(49,171,227,0.5)',
      textStyle: { color: '#e0f7ff' }
    },
    grid: { left: '3%', right: '4%', top: 32, bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: [],
      axisLine: { lineStyle: { color: 'rgba(49,171,227,0.25)' } },
      axisLabel: { color: 'rgba(224,247,255,0.7)', fontSize: 11, interval: 9 },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: 'ppb',
      nameTextStyle: { color: 'rgba(224,247,255,0.7)', fontSize: 12 },
      min: 0,
      max: 1200,
      axisLabel: { color: 'rgba(224,247,255,0.7)', fontSize: 12 },
      splitLine: { lineStyle: { color: 'rgba(49,171,227,0.25)' } }
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

watch(() => store.historyLabels, updateChart, { deep: true })
onUnmounted(() => { if (chart) chart.dispose() })
</script>
