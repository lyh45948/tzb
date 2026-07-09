<template>
  <div class="section-page">
    <OverviewSection />
  </div>
</template>

<script setup>
import { useFactoryInit } from '@/factory/composables/useFactoryInit'
import OverviewSection from '@/factory/components/sections/OverviewSection.vue'

useFactoryInit()
</script>
