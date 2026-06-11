export const dashboardModules = [
  {
    key: 'overview',
    label: '总览',
    icon: '▦',
    color: '#2563eb',
    desc: '展示工厂安全态势、AGV运行、环境与告警模拟数据'
  },
  {
    key: 'environment',
    label: '环境监测',
    icon: '🌡',
    color: '#ef4444',
    desc: '温湿度、照度、CO2/TVOC趋势，对齐 /v1/sensors/current 的展示规划'
  },
  {
    key: 'gas',
    label: '危气安全',
    icon: '⚠',
    color: '#ef4444',
    desc: 'CO2、TVOC、gasMic、火焰与风扇/蜂鸣器联动告警'
  },
  {
    key: 'agv',
    label: 'AGV避障',
    icon: '◆',
    color: '#06b6d4',
    desc: '多车状态、左右轮速、安全距离和本地演示控制'
  },
  {
    key: 'goods',
    label: '货物计数',
    icon: '▣',
    color: '#22c55e',
    desc: '货物感应计数、视觉 digits 与 P6 脉冲模拟'
  },
  {
    key: 'lighting',
    label: '智能照明',
    icon: '💡',
    color: '#f59e0b',
    desc: '红外人体检测、照明模式、目标亮度与时段策略'
  },
  {
    key: 'control',
    label: '设备控制',
    icon: '⚙',
    color: '#8b5cf6',
    desc: '演示控制与设备联动状态，仅本地模拟不下发命令'
  },
  {
    key: 'alarm',
    label: '告警中心',
    icon: '●',
    color: '#ef4444',
    desc: '最近告警、安全趋势与模拟操作审计入口',
    badge: 'LIVE'
  }
]

export const dashboardModuleMap = dashboardModules.reduce((map, item) => {
  map[item.key] = item
  return map
}, {})
