<template>
  <div class="panel-frame-wrapper">
    <div class="panel-frame">
      <div class="panel-header">
        <span class="dot"></span>
        <span class="panel-title">{{ title }}</span>
      </div>
      <div class="panel-body">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' }
})
</script>

<style scoped>
.panel-frame-wrapper {
  height: 100%;
}
</style>
