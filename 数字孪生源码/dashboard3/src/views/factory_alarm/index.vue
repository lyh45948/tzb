<template>
  <div class="section-page">
    <AlarmSection />
  </div>
</template>

<script setup>
import { useFactoryInit } from '@/factory/composables/useFactoryInit'
import AlarmSection from '@/factory/components/sections/AlarmSection.vue'

useFactoryInit()
</script>
