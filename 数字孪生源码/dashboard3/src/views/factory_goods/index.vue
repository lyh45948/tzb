<template>
  <div class="section-page">
    <GoodsSection />
  </div>
</template>

<script setup>
import { useFactoryInit } from '@/factory/composables/useFactoryInit'
import GoodsSection from '@/factory/components/sections/GoodsSection.vue'

useFactoryInit()
</script>
