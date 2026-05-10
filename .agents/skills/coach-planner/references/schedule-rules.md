# Schedule Rules Quick Reference

Coach-planner 排期时的约束规则速查。主 SKILL.md 定义工作流，本文件存放具体排期细节。

## 作息锚点 (Daily Anchors)

**当前架构 (W20+): 3 天 Full Body — Mon/Wed/Fri AM 训练 · Tue/Thu Z2 walk · Sat/Sun 休**

**AM 训练日模式 (Mon/Wed/Fri)**:

| 时间 | 事项 | 备注 |
|------|------|------|
| **05:45** | 起床 + 温水 + 黑咖啡 + 看 COROS HRV | 双闹钟 05:40 + 05:45；HRV 决定全量/降级 |
| 05:50 | Pre-workout shake | 半勺 whey + 1 香蕉 + 5g creatine |
| **06:00–07:10** | AM 训练 (Full Body A/B/C) | 含 8-10min 升级热身（4 级 ramp） |
| 07:15 | 常温水澡 | 训练日避免冷水（保护 mTOR） |
| 07:30 | Post-workout 早餐 | 2 蛋 + 150g 白饭(熟) + 200g Greek Yogurt (~37g P) |
| 08:20 | 出门通勤 | |
| 09:00–18:00 | 核心工作时间 | 上午脑力最充沛，优先排 Deep Work |
| ~19:30 | 到家 | |
| 20:00 | Wind down | 拉伸 / 阅读 / 不刷短视频 |
| 21:00 | 调暗灯 + Magnesium | 200mg Magnesium Glycinate |
| **22:00** | **🔴 灯灭** | **7.75h 睡眠窗口 (22:00→05:45)** |

**Z2 Walk 日模式 (Tue/Thu)**:

| 时间 | 事项 | 备注 |
|------|------|------|
| 06:00 | 起床 | 比训练日多睡 15min |
| 06:30 | 户外 Z2 walk 30min | HR ≤ 137bpm；累可跳过 |
| 07:15 | 早餐 | 3 蛋 + 1 片全麦 + 100g GY + matcha |
| 22:00 | **灯灭** | 保持一致 |

**休息日模式 (Sat/Sun)**:

| 时间 | 事项 | 备注 |
|------|------|------|
| 07:30 | 自然醒 | 体成分测量 (Sat 08:00 空腹) |
| 22:00 | **灯灭** | 保持一致 |

> **Pre-sleep casein 已移除**（per user feedback）— Trommelen 2023；改为午晚餐放大版替代。

## 训练时间窗口

- **Z2 Cardio (Tue/Thu walk)**: 06:30–07:00 户外，30min
  - **Cardio 必须放 AM 或周末**，晚做对 cortisol/arousal 影响远大于阻力训练（Frontiers Physiology 2024）
  - 心率目标 Zone 2 (≤137bpm，能完整说话)
  - **NEAT 工具，非训练**；累可跳过，不进入 RPE 区间
- **抗阻训练 (Strength) — Mon/Wed/Fri Full Body AM**:
  - **AM 06:00–07:10**（W20+ 3 天 Full Body 架构）。距前晚睡 7h+，距当晚睡 14h，零睡眠干扰。**长期 EV 最高**。
  - AM 力量初期下降 ~2-10%，**2-3 周适应后追平 PM 峰值**
  - AM 热身必须 **≥8-10min**（含 4 级递增 ramp），PM 可 6min
  - 训练日用**常温水澡**（冷水抑制 mTOR → 降肌肥大 ~10-15%）
  - 工作日在家 DB 训练，周末可去 gym 大重量日
  - **PM 19:45–21:00 晚训模式**（backup）：需灯灭推迟到 23:00（保 2h 间隔）
  - **详细 evidence**: 见 `references/training-timing-evidence.md`

## 哑铃档位约束 (Home Gym DB Increments)

**家中哑铃可用重量 (kg/each)**: 2.5 / 3.5 / 4.5 / 5.5 / 6.5 / 8 / 9 / 10 / 11.5 / 13.5 / 16 / 18 / 20.5 / 22.5 / 24

- **排重量必须从此列表选**，不要写 7kg / 12kg / 15kg / 17kg 等不存在档位
- 档间距不均匀：低段 1kg（2.5→6.5），中段 1.5-2kg（8→13.5），高段 2-2.5kg（16→24）
- 上限 24kg/each（双手动作如 Goblet/RDL 可达 48kg total）
- Ramp 选档示例: 6.5→9→11.5→13.5→16→18 (递增 ~20-25%)

## 周节奏 (Weekly Rhythm)

| 日 | 主题 | 说明 |
|----|------|------|
| 周一–周五 | 工作日 | 上班是 default，deep_work_hours 不提默认 8h |
| 周六 | System Offline | **禁止编程和产出目标** — 目的是强制心理恢复，防止 burnout。长期不休息会导致创造力和决策质量下降，一天的产出损失远小于持续疲劳的累积代价。如用户有紧急情况需要破例，建议限定时间窗口（如最多 2h）并次日补偿 |
| 周日 | 规划 + 备餐 | 周报复盘、下周排期、食材采购与 meal prep |

## 练后营养分档

| 训练类型 | Pre-workout | Post-workout | 理由 |
|----------|-------------|-------------|------|
| **AM 重训（当前模式）** | 半勺 whey + 1 香蕉 + 5g creatine | 2 蛋 + 150g 白饭 + 150g Greek Yogurt (~32g P) | whey 前移填氨基酸池；post 用高 GI 白饭回补糖原 |
| 周末 Gym 大重量日 | 同上 | 200g Greek Yogurt + 1 勺蛋白粉 (~44g P) | 高强度训练糖原消耗大 |
| 工作日徒手训练 | 同上（可选） | 200g Greek Yogurt alone (~20g P) | 糖原消耗低 |
| 晨跑 Zone 2 | 无需 | 正常早餐覆盖 | |

## 热量管理 (Recomp 期间 — 当前)

| 日类型 | 热量目标 | Deficit | 说明 |
|--------|---------|---------|------|
| 训练日 | **~1,900 kcal** | ~300 kcal | 碳水围绕训练窗口；recomp 黄金区间 |
| 休息日 | **~1,700 kcal** | ~500 kcal | 高于 BMR 1,620 底线 |

- 周累计 deficit 目标: **-2,000 至 -3,500 kcal/周**（避免日均 > -500 kcal 切到 cut 模式）
- 周减体重控制在 <0.5% BW (~0.35kg)，recomp 不追求快速减重
- 蛋白质: **161g/天 (2.30 g/kg)** — recomp 黄金区间 (2.2-2.6 g/kg)
- 脂肪: ≥49g (0.7g/kg 底线，维持激素)
- 餐间隔: 3-5h（持续触发 MPS）
- **Pre-sleep casein 已移除** — 改午晚餐放大版（晚餐蛋白源 130g → 200g 生重）

### Cut 阶段回退档 (体脂率 < 12% 时切换)

| 日类型 | 热量目标 | Deficit |
|--------|---------|---------|
| 训练日 | ~1,800 kcal | ~600 kcal |
| 休息日 | ~1,620 kcal (=BMR) | ~550 kcal |

- 蛋白质拉到 2.0 g/kg = 140g
- 阶段切换由 user 主动触发，写入 `config/thresholds.yaml` 的 `phase.current`

## 睡眠优化

- **8h 窗口**: 21:30 灯灭 → 05:30 起床 = ~7.5-7.75h 实际睡眠
- 7.5h 是最低安全线（一晚剥夺 → MPS -18%、睾酮 -24%）
- 21:00 服用 200mg Magnesium Glycinate（助深睡 + 肌肉放松）
- 20:00 开始 wind down：拉伸/阅读，不刷短视频不看屏幕
- **21:30 灯灭是整个系统的 single point of failure** — 不灭 = 次日训练质量直接砸

## 排期格式模板

### 单日
```
## [Day] MM-DD 时间表 (Draft)

> 状态快照: 睡眠 Xh (Quality) | 精力 X/10 | 熔断: [None / breaker names]

| 时间 | 行动 | 备注 |
|------|------|------|
| HH:MM | Action | Details (macros, cost, project name) |
| ... | ... | ... |
| 22:00 | **[强制断电]** | 准备入睡 |

> 预估支出: ~RMX.XX | Deep Work 目标: Xh
```

### 周计划中的每日
```
### Day MM-DD (Theme)
> 训练模式: Normal / Deload / Recovery | 目标 Deep Work: Xh

| 时间 | 行动 | 备注 |
|------|------|------|
| 06:30 | 起床 | ... |
| ... | ... | ... |
| 22:00 | **[强制断电]** | 准备入睡 |

> 预估支出: ~RMX.XX
```
