<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>AGV运行速度</div>
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

const barColors = ['#2563eb', '#22c55e', '#06b6d4', '#f97316']

function updateChart() {
  if (!chart || !store.fleet.length) return
  const names = store.fleet.map(r => r.name)
  const speeds = store.fleet.map(r => Math.round(r.speed))

  chart.setOption({
    xAxis: { data: names },
    series: [{
      data: speeds.map((v, i) => ({
        value: v,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: barColors[i] || '#2563eb' },
            { offset: 1, color: (barColors[i] || '#2563eb') + '44' }
          ]),
          borderRadius: [3, 3, 0, 0]
        }
      }))
    }]
  })
}

onMounted(() => {
  chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', top: 20, bottom: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: [],
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b', fontSize: 12 }
    },
    yAxis: {
      type: 'value', name: 'mm/s',
      nameTextStyle: { color: '#64748b', fontSize: 12 },
      axisLabel: { color: '#64748b', fontSize: 12 },
      splitLine: { lineStyle: { color: '#cbd5e1' } }
    },
    series: [{
      type: 'bar',
      barWidth: '35%',
      data: [],
      label: {
        show: true,
        position: 'top',
        color: '#1e293b',
        fontSize: 12,
        fontWeight: 'bold'
      }
    }]
  })
  startResize()
})

watch(() => store.fleet, updateChart, { deep: true })
onUnmounted(() => { if (chart) chart.dispose() })
</script>
