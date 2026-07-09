<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>最近障碍物</div>
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

function getColor(v) {
  if (v < 30) return '#ef4444'
  if (v < 60) return '#f59e0b'
  return '#22c55e'
}

function getMinDistance() {
  if (!store.fleet.length) return 0
  return Math.min(...store.fleet.map(r => r.distance ?? 999))
}

function updateChart() {
  if (!chart) return
  const v = getMinDistance()
  chart.setOption({
    series: [{
      data: [{ value: v, itemStyle: { color: getColor(v) } }],
      detail: { formatter: v > 200 ? '> 200' : `${Math.round(v)} cm` }
    }]
  })
}

onMounted(() => {
  chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chart.setOption({
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      min: 0,
      max: 200,
      radius: '100%',
      center: ['50%', '65%'],
      axisLine: {
        lineStyle: {
          width: 12,
          color: [[0.15, '#ef4444'], [0.3, '#f59e0b'], [1, '#22c55e']]
        }
      },
      pointer: { width: 4, length: '55%', itemStyle: { color: '#2563eb' } },
      axisTick: { show: false },
      splitLine: { distance: -12, length: 8, lineStyle: { color: '#64748b', width: 1 } },
      axisLabel: { color: '#64748b', fontSize: 12, distance: 14 },
      detail: { valueAnimation: true, formatter: '-- cm', color: '#1e293b', fontSize: 16, fontWeight: 'bold', offsetCenter: [0, '70%'] },
      data: [{ value: 0 }]
    }]
  })
  startResize()
})

watch(() => store.fleet, updateChart, { deep: true })
onUnmounted(() => { if (chart) chart.dispose() })
</script>
