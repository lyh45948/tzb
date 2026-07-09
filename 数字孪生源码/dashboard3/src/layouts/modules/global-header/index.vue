<script setup lang="ts">
import { ref } from 'vue';
import { useFullscreen } from '@vueuse/core';
import { GLOBAL_HEADER_MENU_ID } from '@/constants/app';
import { useAppStore } from '@/store/modules/app';
import { useThemeStore } from '@/store/modules/theme';
import GlobalLogo from '../global-logo/index.vue';
import GlobalBreadcrumb from '../global-breadcrumb/index.vue';
import GlobalSearch from '../global-search/index.vue';
import ThemeButton from './components/theme-button.vue';
import UserAvatar from './components/user-avatar.vue';
import CarConnectDialog from '@/factory/components/dialogs/CarConnectDialog.vue';

defineOptions({
  name: 'GlobalHeader'
});

interface Props {
  /** Whether to show the logo */
  showLogo?: App.Global.HeaderProps['showLogo'];
  /** Whether to show the menu toggler */
  showMenuToggler?: App.Global.HeaderProps['showMenuToggler'];
  /** Whether to show the menu */
  showMenu?: App.Global.HeaderProps['showMenu'];
}

defineProps<Props>();

const appStore = useAppStore();
const themeStore = useThemeStore();
const { isFullscreen, toggle } = useFullscreen();

const carDialogOpen = ref(false);
</script>

<template>
  <DarkModeContainer class="h-full flex-y-center px-12px shadow-header">
    <GlobalLogo v-if="showLogo" class="h-full" :style="{ width: themeStore.sider.width + 'px' }" />
    <MenuToggler v-if="showMenuToggler" :collapsed="appStore.siderCollapse" @click="appStore.toggleSiderCollapse" />
    <div v-if="showMenu" :id="GLOBAL_HEADER_MENU_ID" class="h-full flex-y-center flex-1-hidden"></div>
    <div v-else class="h-full flex-y-center flex-1-hidden">
      <GlobalBreadcrumb v-if="!appStore.isMobile" class="ml-12px" />
    </div>
    <div class="h-full flex-y-center justify-end">
      <button class="connect-car-btn" title="输入小车 IP 连接" @click="carDialogOpen = true">
        连接小车
      </button>
      <GlobalSearch v-if="themeStore.header.globalSearch.visible" />
      <FullScreen v-if="!appStore.isMobile" :full="isFullscreen" @click="toggle" />
      <LangSwitch
        v-if="themeStore.header.multilingual.visible"
        :lang="appStore.locale"
        :lang-options="appStore.localeOptions"
        @change-lang="appStore.changeLocale"
      />
      <ThemeSchemaSwitch
        :theme-schema="themeStore.themeScheme"
        :is-dark="themeStore.darkMode"
        @switch="themeStore.toggleThemeScheme"
      />
      <ThemeButton />
      <UserAvatar />
    </div>
    <CarConnectDialog v-if="carDialogOpen" @close="carDialogOpen = false" />
  </DarkModeContainer>
</template>

<style scoped>
.connect-car-btn {
  padding: 4px 12px;
  margin-right: 8px;
  border: 1px solid var(--accent-blue, #2563eb);
  background: rgba(30, 80, 180, 0.08);
  color: var(--accent-blue, #2563eb);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}
.connect-car-btn:hover {
  background: var(--accent-blue, #2563eb);
  color: #fff;
}
</style>
