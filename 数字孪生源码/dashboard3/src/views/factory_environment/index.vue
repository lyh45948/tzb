<template>
  <div class="section-page">
    <EnvironmentSection />
  </div>
</template>

<script setup>
import { useFactoryInit } from '@/factory/composables/useFactoryInit'
import EnvironmentSection from '@/factory/components/sections/EnvironmentSection.vue'

useFactoryInit()
</script>
