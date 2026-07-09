<script setup lang="ts">
import FactoryDashboard from '@/factory/FactoryDashboard.vue';

defineOptions({
  name: 'Factory'
});
</script>

<template>
  <!-- 数字孪生总入口：全屏使用，承载 9 大 Section。
       GlobalContent 默认会加 p-16px 内边距，但 FactoryDashboard 自带
       padding:var(--gap)，双层 padding 浪费可视空间，这里用负 margin 抵消。 -->
  <div class="factory-page-wrapper">
    <FactoryDashboard />
  </div>
</template>

<style scoped>
/*
 * 抵消 GlobalContent 默认 p-16px 内边距。
 * FactoryDashboard 自身已通过 padding:var(--gap) 控制内边距，
 * 无需外层额外留白，避免浪费可视空间。
 */
.factory-page-wrapper {
  height: 100%;
  margin: -16px;
}
</style>
