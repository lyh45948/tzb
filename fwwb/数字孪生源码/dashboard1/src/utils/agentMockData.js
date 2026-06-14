/**
 * 智能体页面的数据形状与本地模拟数据。
 *
 * ⚠ 后端接入说明
 * ─────────────────────────────
 * 当前所有数据由本文件的纯函数生成,以便前端独立演示。
 * 后端就绪时,只需:
 *   1. 用 fetch/WebSocket 替换 createMock* 系列函数
 *   2. 保持返回的 JSON 形状与下方 TypeDef 注释一致
 *   3. AgentSection 内会自动解包响应式数据,无需改组件
 *
 * ─── 数据契约 ───────────────────
 *
 * @typedef {Object} AgentInsight 智能体单条洞察(实时流)
 * @property {string|number} id          唯一 ID
 * @property {number} timestamp          UNIX ms
 * @property {'info'|'warning'|'danger'|'critical'|'success'} level
 * @property {'observation'|'reasoning'|'action'|'prediction'} kind  事件类型
 * @property {string} title              简短标题
 * @property {string} content            详细叙述
 * @property {Array<{label:string,value:string|number}>} [evidence]  证据指标
 * @property {string} [suggestion]       建议
 * @property {string} [source]           触发源(模块名)
 *
 * @typedef {Object} AgentTriggerRule 触发规则
 * @property {string} id
 * @property {string} name
 * @property {string} description
 * @property {string} metric
 * @property {string} condition          eg. ">= 800ppm"
 * @property {'warning'|'danger'|'critical'} level
 * @property {boolean} enabled
 * @property {number} hits               近 24h 触发次数
 * @property {number|null} lastFiredAt   UNIX ms
 *
 * @typedef {Object} AgentRisk 风险预测项
 * @property {string} id
 * @property {string} title              风险名称
 * @property {string} category           种类: gas / fire / collision / environment / battery / overload ...
 * @property {number} probability        0~100,占比%
 * @property {'low'|'medium'|'high'|'critical'} severity
 * @property {string} window             预计发生窗口,eg. "未来 30 分钟内"
 * @property {string} reasoning          智能体推理路径
 * @property {string[]} factors          关键诱因
 * @property {string[]} mitigations      缓解建议
 *
 * @typedef {Object} AgentReport 日报/周报
 * @property {string} id
 * @property {'daily'|'weekly'} type
 * @property {string} period             显示用周期文案,eg. "2026-06-13" 或 "2026-06-08 ~ 06-13"
 * @property {number} score              0~100,智能体综合评分
 * @property {string} grade              S / A / B / C / D
 * @property {string} headline           一句话总结
 * @property {Array<{name:string,score:number,delta:number,note:string}>} dimensions  维度评分
 * @property {Array<{title:string,detail:string}>} highlights  亮点
 * @property {Array<{title:string,detail:string,severity:string}>} concerns 待改进
 * @property {string[]} recommendations  下一步建议
 * @property {{labels:string[],values:number[]}} trend  得分趋势
 */

const TITLES = ['危气浓度异常', 'AGV 接近障碍物', '温度逼近警戒', '货物计数异常波动', '红外检测无人值守', '通风联动建议']
const KINDS = ['observation', 'reasoning', 'action', 'prediction']
const LEVELS = ['info', 'warning', 'danger', 'critical', 'success']

let insightSeq = 1000
function nextId(prefix) {
  insightSeq += 1
  return `${prefix}_${insightSeq}`
}

/**
 * 创建一条模拟 insight。
 * 后端接入时:GET /api/agent/insights → AgentInsight[]
 */
export function createMockInsight(level, kind, title, content, options = {}) {
  return {
    id: nextId('ins'),
    timestamp: Date.now(),
    level: level || pick(LEVELS),
    kind: kind || pick(KINDS),
    title: title || pick(TITLES),
    content: content || '智能体基于近 60 秒传感数据完成一次推理,详情见证据列表。',
    evidence: options.evidence || [],
    suggestion: options.suggestion || '',
    source: options.source || '系统'
  }
}

export function buildInitialInsights() {
  const now = Date.now()
  return [
    {
      id: nextId('ins'),
      timestamp: now - 1000 * 60 * 18,
      level: 'success',
      kind: 'observation',
      title: '车间环境恢复正常区间',
      content: '过去 30 分钟内 CO₂ 与 TVOC 均回落至安全阈值以下,排风系统已自动停机。',
      evidence: [
        { label: 'CO₂ 平均', value: '612 ppm' },
        { label: 'TVOC 平均', value: '210 ppb' }
      ],
      suggestion: '保持当前通风策略,无需人工干预。',
      source: '环境监测'
    },
    {
      id: nextId('ins'),
      timestamp: now - 1000 * 60 * 12,
      level: 'warning',
      kind: 'reasoning',
      title: 'AGV-01 与巡检车-01 路径冲突预警',
      content: '在 V=3.5 通道两车将于 1 分 20 秒后相遇,根据优先级巡检车-01 应在交叉点前等待。',
      evidence: [
        { label: '冲突点', value: '(3.5, -1.5)' },
        { label: '预计 ETA', value: '+80s' }
      ],
      suggestion: '已自动让步,无需人工接管。',
      source: 'AGV 调度'
    },
    {
      id: nextId('ins'),
      timestamp: now - 1000 * 60 * 6,
      level: 'danger',
      kind: 'prediction',
      title: '危气区夜间风险上升',
      content: '基于昨日同时段对比,危气区 TVOC 平均偏高 18%,若维持当前通风等级,2 小时后预计触达警戒。',
      evidence: [
        { label: 'TVOC 趋势', value: '↑ 18%' },
        { label: '风扇档位', value: '低速' }
      ],
      suggestion: '建议将危气区风扇调至中速,并通知值班人员加强巡检。',
      source: '风险预测'
    },
    {
      id: nextId('ins'),
      timestamp: now - 1000 * 60 * 2,
      level: 'info',
      kind: 'action',
      title: '已生成今日运行日报草稿',
      content: '基于今日 0:00 至 18:00 的传感、AGV、告警数据,完成日报草稿,等待人工复核。',
      evidence: [
        { label: '告警数', value: 4 },
        { label: '任务完成率', value: '96%' }
      ],
      suggestion: '点击「日/周报」面板查看完整报告。',
      source: '报告中心'
    }
  ]
}

/**
 * 滚动消息流(每 4~6 秒模拟一条)。
 * 后端接入时:WebSocket /ws/agent/insights → 推送 AgentInsight
 */
export function rollInsight(prev) {
  const choices = [
    {
      level: 'info', kind: 'observation', title: '智能体心跳', source: '系统',
      content: '已完成一轮多模态采样,数据维度齐全,模型置信度稳定。',
      evidence: [{ label: '采样间隔', value: '1 s' }, { label: '维度', value: 9 }]
    },
    {
      level: 'warning', kind: 'reasoning', title: '光照偏暗,建议补光', source: '智能照明',
      content: '当前 lux 低于人工作业推荐值,且红外检测到人员活动。',
      evidence: [{ label: 'lux', value: 280 }, { label: '人员', value: '在场' }],
      suggestion: '将照明亮度提升至 70%。'
    },
    {
      level: 'danger', kind: 'prediction', title: 'CO₂ 30 分钟内可能突破警戒', source: '风险预测',
      content: '近 10 分钟 CO₂ 上升斜率 25 ppm/min,按当前趋势 28 分钟后将达 800 ppm。',
      evidence: [{ label: '斜率', value: '25 ppm/min' }, { label: 'ETA', value: '+28m' }],
      suggestion: '建议提前开启强制通风。'
    },
    {
      level: 'success', kind: 'action', title: '排风联动已启动', source: '设备控制',
      content: '依据 CO₂ 上升预测,智能体已自动下发风扇启动指令。',
      evidence: [{ label: '风扇', value: '开启' }, { label: '蜂鸣器', value: '关闭' }]
    },
    {
      level: 'critical', kind: 'observation', title: '危气区火焰传感触发', source: '危气安全',
      content: '检测到火焰信号,已并行触发蜂鸣器、关闭周边设备并通知值班。',
      evidence: [{ label: 'flameStatus', value: 1 }],
      suggestion: '立即派员复核现场,核对消防设备状态。'
    }
  ]
  const tmpl = choices[Math.floor(Math.random() * choices.length)]
  return [
    {
      ...createMockInsight(tmpl.level, tmpl.kind, tmpl.title, tmpl.content, {
        evidence: tmpl.evidence, suggestion: tmpl.suggestion, source: tmpl.source
      })
    },
    ...prev.slice(0, 39)
  ]
}

function pick(arr) { return arr[Math.floor(Math.random() * arr.length)] }

// ─── 触发规则 ───
export function buildTriggerRules() {
  return [
    {
      id: 'rule_co2',
      name: 'CO₂ 浓度过高',
      description: '车间 CO₂ 浓度超过预警阈值时立刻广播告警并联动通风',
      metric: 'CO₂',
      condition: '>= 800 ppm',
      level: 'warning',
      enabled: true,
      hits: 6,
      lastFiredAt: Date.now() - 1000 * 60 * 14
    },
    {
      id: 'rule_co2_danger',
      name: 'CO₂ 危险阈值',
      description: '突破 1000 ppm 直接触发危险等级告警',
      metric: 'CO₂',
      condition: '>= 1000 ppm',
      level: 'danger',
      enabled: true,
      hits: 1,
      lastFiredAt: Date.now() - 1000 * 60 * 65
    },
    {
      id: 'rule_temperature',
      name: '车间高温预警',
      description: '温度超 30℃ 提示降负荷,超 35℃ 触发危险告警',
      metric: '温度',
      condition: '>= 30 ℃ / 35 ℃',
      level: 'warning',
      enabled: true,
      hits: 3,
      lastFiredAt: Date.now() - 1000 * 60 * 42
    },
    {
      id: 'rule_flame',
      name: '火焰传感触发',
      description: '危气区任意火焰传感器触发立刻广播紧急告警',
      metric: 'flameStatus',
      condition: '== 1',
      level: 'critical',
      enabled: true,
      hits: 0,
      lastFiredAt: null
    },
    {
      id: 'rule_gas',
      name: '可燃气体异常',
      description: 'gasMic 信号超出阈值或 gasStatus 直接置位',
      metric: 'gasMic / gasStatus',
      condition: 'gasMic >= 500',
      level: 'critical',
      enabled: true,
      hits: 0,
      lastFiredAt: null
    },
    {
      id: 'rule_obstacle',
      name: 'AGV 安全距离',
      description: '任一 AGV 障碍距离 ≤ 30cm 进入避障观察,≤ 15cm 直接告警',
      metric: 'distanceCm',
      condition: '<= 30 / 15 cm',
      level: 'warning',
      enabled: true,
      hits: 12,
      lastFiredAt: Date.now() - 1000 * 60 * 4
    },
    {
      id: 'rule_low_battery',
      name: 'AGV 低电量返航',
      description: '电量 ≤ 20% 自动派发返航至充电桩任务',
      metric: 'battery',
      condition: '<= 20%',
      level: 'warning',
      enabled: false,
      hits: 0,
      lastFiredAt: null
    },
    {
      id: 'rule_human_dark',
      name: '黑暗环境人员检测',
      description: 'lux < 100 且 PIR 检测到人员活动时,自动补光',
      metric: 'lux + PIR',
      condition: 'lux < 100 且 humanDetected = 1',
      level: 'warning',
      enabled: true,
      hits: 2,
      lastFiredAt: Date.now() - 1000 * 60 * 90
    }
  ]
}

// ─── 风险预测 ───
export function buildRisks() {
  return [
    {
      id: 'risk_gas',
      title: '危气区夜间 TVOC 越限',
      category: 'gas',
      probability: 72,
      severity: 'high',
      window: '未来 2 小时内',
      reasoning: '昨日同时段 TVOC 已突破 600 ppb,今日斜率与昨日吻合;且当前风扇仍在低档。',
      factors: ['夜间通风减弱', 'TVOC 上升斜率高', '历史同期已发生过'],
      mitigations: ['危气区风扇调至中速', '增加值班巡检频次', '准备紧急排风预案']
    },
    {
      id: 'risk_collision',
      title: 'AGV-01 与物料车交汇拥堵',
      category: 'collision',
      probability: 45,
      severity: 'medium',
      window: '未来 30 分钟',
      reasoning: '在 H=4 通道两车密度增加,优先级冲突会引发让步等待累积。',
      factors: ['任务重叠', '通道容量有限'],
      mitigations: ['临时调整 AGV-01 巡检路线', '将物料任务切分为两段下发']
    },
    {
      id: 'risk_overheat',
      title: '车间下午高温越线',
      category: 'environment',
      probability: 30,
      severity: 'medium',
      window: '14:00 ~ 16:00',
      reasoning: '气象温度走高,叠加生产线满负荷,过去三日均出现 30℃+ 局部峰值。',
      factors: ['外部气温', '设备散热集中'],
      mitigations: ['提前开启车间空调', '错峰排产']
    },
    {
      id: 'risk_battery',
      title: '物料车电量将不足',
      category: 'battery',
      probability: 58,
      severity: 'medium',
      window: '未来 45 分钟',
      reasoning: '当前任务密度下,物料车-01 平均放电 0.6%/min,预计 45 分钟后跌破 20%。',
      factors: ['任务连续派发', '空载返航增多'],
      mitigations: ['任务结束后强制返航充电', '调度备用 AGV 接管']
    },
    {
      id: 'risk_fire',
      title: '焊接区火焰风险',
      category: 'fire',
      probability: 12,
      severity: 'low',
      window: '今日',
      reasoning: '焊接-01 工位粒尘浓度偏高,但火焰传感器无异常;历史发生概率低。',
      factors: ['粒尘浓度偏高'],
      mitigations: ['加强火焰传感器自检']
    }
  ]
}

// ─── 报告 ───
export function buildLatestReport(type) {
  if (type === 'weekly') {
    return {
      id: `rep_w_${Date.now()}`,
      type: 'weekly',
      period: '2026-06-08 ~ 06-13',
      score: 86,
      grade: 'A',
      headline: '本周整体平稳,危气区夜间通风需关注',
      dimensions: [
        { name: '环境稳定', score: 92, delta: +2, note: '温湿度 / 照度全部维持区间' },
        { name: '危气安全', score: 78, delta: -4, note: '夜间 TVOC 4 次越限' },
        { name: 'AGV 调度', score: 88, delta: +1, note: '任务完成率 97%' },
        { name: '能耗管理', score: 84, delta: 0, note: '风扇启停频次合理' },
        { name: '告警响应', score: 90, delta: +5, note: '响应延迟下降到 12s' }
      ],
      highlights: [
        { title: 'AGV 任务完成率创新高', detail: '本周完成 218 项任务,完成率 97%,较上周提升 3pp。' },
        { title: '联动响应提速', detail: '风扇与蜂鸣器平均联动延迟降至 12s,减少了 18% 的人工介入。' }
      ],
      concerns: [
        { title: '危气区夜间通风偏弱', detail: '04:00~06:00 TVOC 多次接近危险阈值,建议夜间提升风扇档位。', severity: 'warning' },
        { title: '物料车电量管理欠佳', detail: '本周 3 次低电量临时召回,影响调度连续性。', severity: 'warning' }
      ],
      recommendations: [
        '调整危气区夜间通风策略,默认中速档',
        '为物料车追加自动充电规则(电量 ≤ 25% 派发充电任务)',
        '在出货口增加 AGV 优先级配置,避免高峰期等待'
      ],
      trend: {
        labels: ['周一', '周二', '周三', '周四', '周五', '周六', '今日'],
        values: [82, 84, 85, 81, 87, 88, 86]
      }
    }
  }
  return {
    id: `rep_d_${Date.now()}`,
    type: 'daily',
    period: '2026-06-13',
    score: 91,
    grade: 'S',
    headline: '今日运行平稳,所有关键告警均自动闭环',
    dimensions: [
      { name: '环境稳定', score: 94, delta: +1, note: '车间温湿度全天在区间内' },
      { name: '危气安全', score: 88, delta: +2, note: '无危险等级告警' },
      { name: 'AGV 调度', score: 92, delta: +3, note: '任务完成率 98%' },
      { name: '能耗管理', score: 86, delta: 0, note: '风扇运行 4.2 小时' },
      { name: '告警响应', score: 95, delta: +4, note: '人工介入 0 次' }
    ],
    highlights: [
      { title: '零人工介入', detail: '今日 4 起告警均由智能体自动联动闭环。' },
      { title: 'AGV 任务完成率 98%', detail: '38 项任务,1 项被取消,无延误。' }
    ],
    concerns: [
      { title: 'CO₂ 14:32 触达 825 ppm', detail: '触发预警,排风启动后 6 分钟回落,无需人工干预,但提示通风裕度收窄。', severity: 'warning' }
    ],
    recommendations: [
      '14:00 ~ 15:00 时段提前 5 分钟启动通风',
      '为出货口与包装区增加调度协同规则'
    ],
    trend: {
      labels: ['00时', '04时', '08时', '12时', '16时', '20时', '现在'],
      values: [88, 87, 90, 92, 89, 91, 91]
    }
  }
}

// 智能体当前心跳/状态
export function buildAgentStatus() {
  return {
    name: 'Twin Sentinel',
    version: 'v1.2.0',
    online: true,
    uptimeSec: 6400,
    samplesPerMin: 60,
    rulesActive: 7,
    pendingPredictions: 5,
    lastReportAt: Date.now() - 1000 * 60 * 12
  }
}
