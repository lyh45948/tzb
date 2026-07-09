<template>
  <div class="section-page">
    <ControlSection />
  </div>
</template>

<script setup>
import { useFactoryInit } from '@/factory/composables/useFactoryInit'
import ControlSection from '@/factory/components/sections/ControlSection.vue'

useFactoryInit()
</script>
