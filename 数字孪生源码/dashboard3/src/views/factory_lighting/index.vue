<template>
  <div class="section-page">
    <LightingSection />
  </div>
</template>

<script setup>
import { useFactoryInit } from '@/factory/composables/useFactoryInit'
import LightingSection from '@/factory/components/sections/LightingSection.vue'

useFactoryInit()
</script>
