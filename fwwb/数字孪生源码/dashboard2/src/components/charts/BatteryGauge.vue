<template>
  <div class="panel-frame">
    <div class="panel-header"><span class="dot"></span>移动设备电量</div>
    <div class="panel-body">
      <div ref="chartEl" style="width:100%;height:100%"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { useDeviceStore } from '../../stores/deviceStore'
import { getBatteryColor } from '../../utils/dataFormatter'
import { useChartResize } from '../../composables/useChartResize'

const chartEl = ref(null)
let chart = null
const store = useDeviceStore()

const { start: startResize } = useChartResize(chartEl, () => chart)

function updateChart() {
  if (!chart) return
  const fleet = store.fleet
  if (!fleet.length) return

  const names = fleet.map(r => r.name)
  const batteries = fleet.map(r => Math.round(r.battery ?? 0))
  const colors = fleet.map(r => getBatteryColor(r.battery ?? 0))

  chart.setOption({
    xAxis: { data: names },
    series: [{
      data: batteries.map((v, i) => ({
        value: v,
        itemStyle: { color: colors[i], borderRadius: [2, 2, 0, 0] }
      }))
    }]
  })
}

onMounted(() => {
  chart = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(8,18,40,0.9)',
      borderColor: 'rgba(49,171,227,0.5)',
      textStyle: { color: '#e0f7ff' }
    },
    grid: { left: 40, right: 10, top: 15, bottom: 25 },
    xAxis: {
      type: 'category',
      data: [],
      axisLabel: { color: 'rgba(224,247,255,0.7)', fontSize: 12, interval: 0 },
      axisLine: { lineStyle: { color: 'rgba(49,171,227,0.25)' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: 'rgba(224,247,255,0.7)', fontSize: 12, formatter: '{value}%' },
      splitLine: { lineStyle: { color: 'rgba(49,171,227,0.25)' } },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [{
      type: 'bar',
      barWidth: '40%',
      label: {
        show: true,
        position: 'top',
        color: '#e0f7ff',
        fontSize: 13,
        fontWeight: 'bold',
        formatter: '{c}%'
      },
      data: []
    }]
  })
  startResize()
})

watch(() => store.fleet, updateChart, { deep: true })
onUnmounted(() => { if (chart) chart.dispose() })
</script>
