<template>
  <aside :class="['sidebar-nav', { collapsed }]">
    <div class="brand-block">
      <div class="brand-icon">🏭</div>
      <div v-if="!collapsed" class="brand-texts">
        <div class="brand-title">Factory Twin</div>
        <div class="brand-subtitle">安全监测平台</div>
      </div>
    </div>

    <button
      class="collapse-btn"
      type="button"
      :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'"
      :title="collapsed ? '展开侧边栏' : '收起侧边栏'"
      @click="$emit('update:collapsed', !collapsed)"
    >
      <span v-if="collapsed">»</span>
      <span v-else>«</span>
    </button>

    <nav class="nav-list">
      <button
        v-for="item in navItems"
        :key="item.key"
        :class="['nav-item', { active: active === item.key }]"
        :title="collapsed ? item.label : ''"
        @click="$emit('update:active', item.key)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
        <span v-if="!collapsed && item.badge" class="nav-badge">{{ item.badge }}</span>
      </button>
    </nav>

    <div v-if="!collapsed" class="nav-status">
      <div class="status-title">当前模块</div>
      <div class="status-value">{{ activeLabel }}</div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { dashboardModules } from '../../modules/dashboardModules'

const props = defineProps({
  active: {
    type: String,
    default: 'overview'
  },
  collapsed: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:active', 'update:collapsed'])

const navItems = dashboardModules

const activeLabel = computed(() => navItems.find(item => item.key === props.active)?.label || '总览')
</script>

<style scoped>
.sidebar-nav {
  width: var(--sidebar-width);
  flex-shrink: 0;
  margin: var(--gap) 0 var(--gap) var(--gap);
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.94));
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-panel);
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.25s ease;
}

.sidebar-nav.collapsed {
  width: var(--sidebar-collapsed-width);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.sidebar-nav.collapsed .brand-block {
  justify-content: center;
  padding: 14px 0;
}

.brand-icon {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(37, 99, 235, 0.22);
  border: 1px solid rgba(96, 165, 250, 0.35);
  border-radius: 8px;
  font-size: 18px;
  flex-shrink: 0;
}

.brand-texts {
  overflow: hidden;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.brand-subtitle {
  margin-top: 2px;
  color: #94a3b8;
  font-size: 12px;
}

.collapse-btn {
  width: 100%;
  height: 28px;
  border: none;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  background: rgba(0, 0, 0, 0.15);
  color: #94a3b8;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}

.collapse-btn:hover {
  background: rgba(59, 130, 246, 0.15);
  color: #e2e8f0;
}

.nav-list {
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sidebar-nav.collapsed .nav-list {
  padding: 10px 4px;
  align-items: center;
}

.nav-item {
  width: 100%;
  height: 38px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  cursor: pointer;
  transition: all 0.18s ease;
  text-align: left;
}

.sidebar-nav.collapsed .nav-item {
  justify-content: center;
  padding: 0;
  width: 38px;
}

.nav-item:hover {
  background: rgba(59, 130, 246, 0.12);
  color: #fff;
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.42), rgba(6, 182, 212, 0.18));
  border-color: rgba(96, 165, 250, 0.55);
  color: #fff;
  box-shadow: inset 3px 0 0 #38bdf8;
}

.sidebar-nav.collapsed .nav-item.active {
  box-shadow: inset 0 0 0 1.5px #38bdf8;
}

.nav-icon {
  width: 18px;
  color: #38bdf8;
  font-size: 14px;
  text-align: center;
  flex-shrink: 0;
}

.nav-label {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-badge {
  padding: 1px 5px;
  border-radius: 999px;
  background: rgba(239, 68, 68, 0.18);
  color: #fca5a5;
  font-size: 10px;
}

.nav-status {
  margin: auto 10px 10px;
  padding: 10px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.15);
  overflow: hidden;
}

.status-title {
  color: #94a3b8;
  font-size: 12px;
}

.status-value {
  margin-top: 4px;
  color: #38bdf8;
  font-size: 15px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>