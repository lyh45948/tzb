<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>CO 浓度</div>
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

function updateChart(val) {
  if (!chart) return
  const v = val ?? 0
  const display = +Number(v).toFixed(1)
  chart.setOption({
    series: [{
      data: [{ value: display, itemStyle: { color: getColor(display) } }],
      detail: { formatter: `${display} ppm` }
    }]
  })
}

function getColor(v) {
  if (v >= 50) return '#ef4444'
  if (v >= 35) return '#f59e0b'
  return '#22c55e'
}

onMounted(() => {
  chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chart.setOption({
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      min: 0,
      max: 100,
      radius: '92%',
      center: ['50%', '58%'],
      axisLine: {
        lineStyle: {
          width: 12,
          // 0~35 安全(绿) / 35~50 警戒(黄) / 50~100 危险(红)
          color: [[0.35, '#22c55e'], [0.50, '#f59e0b'], [1, '#ef4444']]
        }
      },
      pointer: { width: 4, length: '55%', itemStyle: { color: '#2563eb' } },
      axisTick: { show: false },
      splitLine: { distance: -12, length: 8, lineStyle: { color: '#64748b', width: 1 } },
      axisLabel: { color: '#64748b', fontSize: 12, distance: 14 },
      detail: { valueAnimation: true, formatter: '-- ppm', color: '#1e293b', fontSize: 18, fontWeight: 'bold', offsetCenter: [0, '58%'] },
      data: [{ value: 0, itemStyle: { color: '#94a3b8' } }]
    }]
  })
  startResize()
})

watch(() => store.co, updateChart)
onUnmounted(() => { if (chart) chart.dispose() })
</script>
