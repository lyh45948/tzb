// 工厂关键功能区域,作为AGV调度任务的起止候选点。
// 坐标系参考 dataFormatter.PATHS,场景安全范围 x∈[-13,13], z∈[-10,10]。
// 所有点位都对齐到 H/V 安全通道交叉点上,避免路径直接穿过建筑物。
//   H通道(横向 z): -8.5, -1.5, 4, 9.5
//   V通道(纵向 x): -8, -1, 3.5, 13
export const FACTORY_WAYPOINTS = [
  { id: 'WH-A',   name: '原料库A',  x:  -8, z: -8.5, color: '#06b6d4' },
  { id: 'WH-B',   name: '原料库B',  x:  -8, z:  4,   color: '#06b6d4' },
  { id: 'PROD-1', name: '加工线1',  x: 3.5, z: -1.5, color: '#2563eb' },
  { id: 'PROD-2', name: '加工线2',  x: 3.5, z:  4,   color: '#2563eb' },
  { id: 'PACK',   name: '包装区',   x:  13, z: -1.5, color: '#22c55e' },
  { id: 'OUT',    name: '出货口',   x: 3.5, z:  9.5, color: '#f59e0b' },
  { id: 'CHARGE', name: '充电桩',   x:  -8, z:  9.5, color: '#8b5cf6' },
  { id: 'INSP',   name: '巡检点',   x:  -1, z: -8.5, color: '#ef4444' }
]

// 场景中 AGV 不可穿越的建筑物 AABB(对齐 SceneEnvironment.js 中的几何体)
// 注:传送带视觉上是低矮带状,允许 AGV 从其旁通行,因此不计入此处。
export const SAFETY_BLOCKS = [
  // 危气区
  { x1: 6.4,   x2: 11.2,  z1: 4.0,   z2: 7.8,  name: 'gas' },
  // 货架排
  { x1: -13.6, x2: -10.4, z1: -7.4,  z2: 2.6,  name: 'shelves' },
  // 工位列(三列 × 上下两排)
  { x1: -4.3,  x2: -2.7,  z1: -5.4,  z2: -4.2, name: 'cnc-1' },
  { x1: 0.4,   x2: 2.0,   z1: -5.4,  z2: -4.2, name: 'asm-1' },
  { x1: 5.2,   x2: 6.8,   z1: -5.4,  z2: -4.2, name: 'qc-1' },
  { x1: -4.3,  x2: -2.7,  z1: 0.6,   z2: 1.8,  name: 'weld-1' },
  { x1: 0.4,   x2: 2.0,   z1: 0.6,   z2: 1.8,  name: 'pack-1' },
  { x1: 5.2,   x2: 6.8,   z1: 0.6,   z2: 1.8,  name: 'count-1' },
  // 货物区
  { x1: -2.6,  x2: 1.6,   z1: 6.6,   z2: 8.4,  name: 'goods' }
]

// 安全通道(只允许 AGV 沿这些线行进)
export const CORRIDORS = {
  horizontal: [-8.5, -1.5, 4, 9.5],
  vertical:   [-8, -1, 3.5, 13]
}

export const TASK_TYPES = [
  { value: 'transport',  label: '物料搬运', color: '#2563eb' },
  { value: 'patrol',     label: '区域巡检', color: '#06b6d4' },
  { value: 'inspection', label: '安全巡查', color: '#ef4444' },
  { value: 'goods',      label: '货物计数', color: '#22c55e' }
]

export const TASK_STATUS_MAP = {
  pending:   { label: '待执行', color: '#94a3b8' },
  running:   { label: '执行中', color: '#2563eb' },
  completed: { label: '已完成', color: '#22c55e' },
  cancelled: { label: '已取消', color: '#64748b' },
  failed:    { label: '失败',   color: '#ef4444' }
}

export const TASK_PRIORITY_MAP = {
  normal: { label: '常规', color: '#64748b' },
  high:   { label: '紧急', color: '#ef4444' }
}

// ─── 路径规划:走廊曼哈顿,避开 SAFETY_BLOCKS ───

// 检测水平/垂直线段是否穿过任意安全块(端点不算穿过 — 用严格不等式)
function segmentHitsBlock(p1, p2) {
  // 水平段(z 相同)或垂直段(x 相同)
  for (const b of SAFETY_BLOCKS) {
    if (Math.abs(p1.x - p2.x) < 1e-6) {
      const x = p1.x
      const zMin = Math.min(p1.z, p2.z)
      const zMax = Math.max(p1.z, p2.z)
      if (x > b.x1 && x < b.x2 && zMax > b.z1 && zMin < b.z2) return true
    } else if (Math.abs(p1.z - p2.z) < 1e-6) {
      const z = p1.z
      const xMin = Math.min(p1.x, p2.x)
      const xMax = Math.max(p1.x, p2.x)
      if (z > b.z1 && z < b.z2 && xMax > b.x1 && xMin < b.x2) return true
    }
  }
  return false
}

function pathLength(points) {
  let len = 0
  for (let i = 1; i < points.length; i++) {
    len += Math.hypot(points[i].x - points[i - 1].x, points[i].z - points[i - 1].z)
  }
  return len
}

/**
 * 规划从 from 到 to 的曼哈顿路径,避开建筑物。
 * 优先尝试 L 型(两段),失败再尝试 U 型(经过中间走廊)。
 * 返回 waypoint 数组(包含起点和终点)。
 */
export function planRoute(from, to) {
  // 同 x 或同 z 直线 — 不被挡时直接返回
  const sameX = Math.abs(from.x - to.x) < 1e-6
  const sameZ = Math.abs(from.z - to.z) < 1e-6
  if ((sameX || sameZ) && !segmentHitsBlock(from, to)) {
    return [from, to]
  }
  const candidates = []

  // L 型只在不退化时尝试(否则两个段共线,等价于直线)
  if (!sameX && !sameZ) {
    const m1 = { x: from.x, z: to.z }
    if (!segmentHitsBlock(from, m1) && !segmentHitsBlock(m1, to)) {
      candidates.push([from, m1, to])
    }
    const m2 = { x: to.x, z: from.z }
    if (!segmentHitsBlock(from, m2) && !segmentHitsBlock(m2, to)) {
      candidates.push([from, m2, to])
    }
    if (candidates.length) {
      candidates.sort((a, b) => pathLength(a) - pathLength(b))
      return candidates[0]
    }
  }

  // U 型:经过某条横通道 my,from→(fx,my)→(tx,my)→to
  for (const my of CORRIDORS.horizontal) {
    if (Math.abs(my - from.z) < 1e-6 || Math.abs(my - to.z) < 1e-6) continue
    const u1 = { x: from.x, z: my }
    const u2 = { x: to.x, z: my }
    if (!segmentHitsBlock(from, u1) && !segmentHitsBlock(u1, u2) && !segmentHitsBlock(u2, to)) {
      candidates.push([from, u1, u2, to])
    }
  }
  // U 型:经过某条纵通道 mx
  for (const mx of CORRIDORS.vertical) {
    if (Math.abs(mx - from.x) < 1e-6 || Math.abs(mx - to.x) < 1e-6) continue
    const u1 = { x: mx, z: from.z }
    const u2 = { x: mx, z: to.z }
    if (!segmentHitsBlock(from, u1) && !segmentHitsBlock(u1, u2) && !segmentHitsBlock(u2, to)) {
      candidates.push([from, u1, u2, to])
    }
  }
  if (candidates.length) {
    candidates.sort((a, b) => pathLength(a) - pathLength(b))
    return candidates[0]
  }

  // 最后保底:直线
  return [from, to]
}
