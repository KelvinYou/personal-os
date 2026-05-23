---
# === 手填字段 (晚上 ~30s 完成；完美执行日只填 4-5 项) ===
energy_level:                 # 1-10
deep_work_hours:              # 不填默认 8（上班族 default）
mental_load:                  # 1-7
caffeine_cutoff:              # HH:MM；默认 14:00 内，超了才改
adherence:
  timetable:                  # ✅ 严格执行 / ⚠️ 小偏差 / 🔴 破坏 plan
  deviation_note:             # 仅 ⚠️/🔴 时写一行根因
primary_blocker:              # 仅 incident 当日写一行；否则留空
daily_spend: []
  # - item: 描述
  #   amount: 0.0
  #   category: food

# === 体测字段 (仅 Sun 体测日填) ===
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

# === COROS 自动同步 (make sync-coros) — 不要手填 ===
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
  load_ratio:         # ATI/CTI (>1.5 警示过训)
  stamina_level:      # 体能储备 0-100 (跑步后更新)
  performance:        # -1 / 0 / +1
training:
  today_load:         # 当日总训练负荷
  vo2max:             # VO2max (缓慢更新)
  lthr:               # 乳酸阈心率 (bpm)
activities: []
  # - type: Running
  #   name: Kuala Lumpur Run
  #   duration_min: 41.0
  #   distance_km: 5.02
  #   avg_hr: 143
  #   calories: 441
  #   training_load: 130
---

<!-- W22+ Lightweight 版（替代旧版 4 章叙事）— 仅 adherence.timetable != ✅ 时手填根因，
     完美执行日整个 body 留空。COROS + frontmatter 已含全部 weekly-review 所需数据。 -->
