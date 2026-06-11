import { onUnmounted } from 'vue'

export function useChartResize(chartElRef, getChart) {
  let observer = null

  function resize() {
    requestAnimationFrame(() => {
      getChart()?.resize()
    })
  }

  function start() {
    if (!chartElRef.value || !window.ResizeObserver) return

    observer = new ResizeObserver(resize)
    observer.observe(chartElRef.value)
  }

  function stop() {
    if (observer) {
      observer.disconnect()
      observer = null
    }
  }

  onUnmounted(stop)

  return { start, stop }
}
