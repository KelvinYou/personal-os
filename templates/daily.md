---
# ============================================================
#  只记例外 (Exception-based logging)
#  仅当私有 data/config/thresholds.yaml 已由本人确认时，留空字段才按
#  logging_defaults 评分；缺少当天日志不会生成数据。
# ============================================================

energy_level:           # 1-10；留空时按个人 logging_defaults 评分

# 下面全部可选，只在**偏离基线**那天写：
# deep_work_hours:      # 留空 = 个人配置中的工作日/周末基线
# mental_load:          # 留空 = 个人配置中的基线
# caffeine_cutoff:      # 留空 = 个人配置中的时间
# adherence:
#   timetable:          # 留空 = ✅ 按 standard_week 执行；偏离才写 ⚠️ / 🔴
#   deviation_note:     # 写 ⚠️/🔴 时补一行根因
# primary_blocker:      # 仅 incident 当日写一行
# daily_spend:          # 留空 = 个人配置中的日常支出基线；额外支出才逐项写
#   - item: 描述
#     amount: 0.0
#     category: food

# === 体测字段 (每 2 周一次，Sun 晨起空腹；无测量就整块留空) ===
# 注意：body.* 不参与基线兜底 —— 没测就是没测，不会凭空造数
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

# === 健康数据：启用 COROS 时由 make sync-coros 写入；否则可手填实测值 ===
# === 不参与基线兜底；启用同步后，脚本会覆盖同名手填字段 ===
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
