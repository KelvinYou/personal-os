---
# ============================================================
#  可选观测：留空 = 未知；显式 0 = 已观测到零。
# ============================================================

energy_level:           # 1-10；留空 = 未记录

# 下面全部可选；有观测时才填写：
# deep_work_hours:      # 可填 0；留空 = 未记录
# mental_load:          # 留空 = 未记录
# caffeine_cutoff:      # 留空 = 未记录
# adherence:
#   timetable:          # 留空 = 未记录；✅ / ⚠️ / 🔴 均须显式填写
#   deviation_note:     # 写 ⚠️/🔴 时补一行根因
# primary_blocker:      # 仅 incident 当日写一行
# daily_spend:          # 留空 = 未记录；金额 0 表示已确认零支出
#   - item: 描述
#     amount: 0.0
#     category: food

# === 手动体测；可以只记体重，其他字段留空 ===
body:
  weight:             # 体重 (kg)
  body_fat_pct:       # 体脂率 %
  muscle_kg:          # 肌肉量 (kg)
  visceral_fat:       # 内脏脂肪等级
  bmi:                # BMI
  water_pct:          # 水分比例 %
  protein_pct:        # 蛋白质比例 %
  bone_mass_kg:       # 骨量 (kg)
  basal_metabolism:   # 基础代谢 (kcal)

# === Optional health snapshots: official COROS MCP is queried on demand, not auto-written here ===
# === 启用同步后，脚本会覆盖同名手填字段 ===
# coros_synced: true  # Legacy provenance only; do not set from routine MCP queries.
sleep:
  duration:           # 总睡眠时长 (小时, e.g. 7.65)
  deep_min:           # 深睡 (分钟)
  light_min:          # 浅睡 (分钟)
  rem_min:            # REM (分钟)
  awake_min:          # 清醒 (分钟)
  nap_min:            # 白天小睡 (分钟)
  avg_hr:             # 夜间均心率
  min_hr:             # 夜间最低心率 (≈真实 RHR)
  max_hr:             # 夜间最高心率
readiness:
  hrv:                # 昨夜 HRV (ms)
  hrv_baseline:       # 7 日 baseline (ms)
  rhr:                # 静息心率 (bpm)
  tired_rate:         # 疲劳指数 (负值=偏疲劳)
  ati:                # 急性训练负荷 (Acute TI)
  cti:                # 慢性训练负荷 / 基础体能 (Chronic TI)
  load_ratio:         # ATI/CTI；预警阈值见个人配置
  stamina_level:      # 体能储备 0-100 (跑步后更新)
  performance:        # -1 / 0 / +1
training:
  today_load:         # 当日总训练负荷
  vo2max:             # VO2max (缓慢更新)
  lthr:               # 乳酸阈心率 (bpm)
activities: []
---

<!-- Body 留空即可。只有 adherence 是 ⚠️/🔴 或当天有 incident 时才写一行根因。 -->
