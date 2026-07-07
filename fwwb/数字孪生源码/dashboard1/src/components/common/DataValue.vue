<template>
  <span class="data-value">
    {{ formattedValue }}<span class="suffix" v-if="suffix">{{ suffix }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { default: null },
  decimals: { type: Number, default: 1 },
  suffix: { type: String, default: '' }
})

const formattedValue = computed(() => {
  if (props.value == null || isNaN(props.value)) return '--'
  return Number(props.value).toFixed(props.decimals)
})
</script>

<style scoped>
.data-value { font-size: 14px; font-weight: 700; color: var(--text-accent); }
.suffix { font-size: 11px; font-weight: 400; color: var(--text-secondary); margin-left: 2px; }
</style>
