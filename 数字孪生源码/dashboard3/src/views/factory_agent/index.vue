<template>
  <div class="section-page">
    <AgentSection />
  </div>
</template>

<script setup>
import { useFactoryInit } from '@/factory/composables/useFactoryInit'
import AgentSection from '@/factory/components/sections/AgentSection.vue'

useFactoryInit()
</script>
