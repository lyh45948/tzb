<template>
  <div class="section-page">
    <AgvSection />
  </div>
</template>

<script setup>
import { useFactoryInit } from '@/factory/composables/useFactoryInit'
import AgvSection from '@/factory/components/sections/AgvSection.vue'

useFactoryInit()
</script>
