<template>
  <!-- 货物计数大屏: IofTV 风格 左计数 + 中3D场景 + 右视频/车队 -->
  <div class="section-page goods-section">
    <div class="goods-grid">
      <!-- 左栏: 货物计数 -->
      <div class="col col-left">
        <ItemWrap title="货物计数">
          <GoodsCountPanel />
        </ItemWrap>
      </div>

      <!-- 中栏: 3D 场景 -->
      <div class="col col-center">
        <ItemWrap title="数字孪生仓库实景">
          <div class="scene-host">
            <CarScene />
          </div>
        </ItemWrap>
      </div>

      <!-- 右栏: 视频预览 + 车队状态 -->
      <div class="col col-right">
        <ItemWrap title="视频预览">
          <CameraPreviewPanel />
        </ItemWrap>
        <ItemWrap title="车队状态">
          <CarStatusPanel />
        </ItemWrap>
      </div>
    </div>
  </div>
</template>

<script setup>
import ItemWrap from '@/components/item-wrap/item-wrap.vue'
import GoodsCountPanel from '../panels/GoodsCountPanel.vue'
import CameraPreviewPanel from '../panels/CameraPreviewPanel.vue'
import CarScene from '../three/CarScene.vue'
import CarStatusPanel from '../panels/CarStatusPanel.vue'
</script>

<style scoped>
.section-page {
  width: 100%;
  height: 100%;
}
.goods-section {
  display: flex;
}
.goods-grid {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(300px, 0.85fr) minmax(0, 1.6fr) minmax(300px, 0.85fr);
  gap: 12px;
  min-height: 0;
}
.col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.col-left > *,
.col-center > *,
.col-right > * {
  flex: 1;
  min-height: 0;
}
.scene-host {
  width: 100%;
  height: 100%;
}
</style>
