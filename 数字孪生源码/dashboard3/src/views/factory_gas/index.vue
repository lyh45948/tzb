<template>
  <div class="section-page">
    <GasSafetySection />
  </div>
</template>

<script setup>
import { useFactoryInit } from '@/factory/composables/useFactoryInit'
import GasSafetySection from '@/factory/components/sections/GasSafetySection.vue'

useFactoryInit()
</script>
