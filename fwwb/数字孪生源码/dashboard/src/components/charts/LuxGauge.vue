<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>光照强度</div>
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
  if (!chart) return
  const v = store.lux ?? 0
  chart.setOption({
    series: [{ data: [{ value: v }] }]
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
      max: 1500,
      radius: '100%',
      center: ['50%', '65%'],
      axisLine: {
        lineStyle: {
          width: 12,
          color: [[0.3, '#f97316'], [0.6, '#f59e0b'], [1, '#22c55e']]
        }
      },
      pointer: { width: 4, length: '60%', itemStyle: { color: '#2563eb' } },
      axisTick: { distance: -12, length: 4, lineStyle: { color: '#64748b', width: 1 } },
      axisLabel: { color: '#64748b', fontSize: 12, distance: 16 },
      detail: { valueAnimation: true, formatter: '{value} lux', color: '#1e293b', fontSize: 16, fontWeight: 'bold', offsetCenter: [0, '70%'] },
      data: [{ value: 0 }]
    }]
  })
  startResize()
})

watch(() => store.lux, updateChart)
onUnmounted(() => { if (chart) chart.dispose() })
</script>
