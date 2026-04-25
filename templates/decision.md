---
id:                       # YYYY-MM-DD-<slug>，与文件名一致
date_decided:             # YYYY-MM-DD
category:                 # career | finance | health | relationship | project | tooling
stakes:                   # medium | high (low 不记)
                          # high = 改变 ≥ 1 年生活轨迹; medium = 影响 ≥ 1 个月
reversibility:            # easy | costly | irreversible
decision_type:            # proactive | reactive | default
                          # proactive = 主动发起; reactive = 被迫应对; default = 选择不变
expected_outcome:         # 1 句话，必须可证伪
review_date:              # 触发回顾的日期（默认 +30d）
status:                   # open | reviewed | pushed | expired
# 以下字段由 /decision-review 写入
actual_outcome:           # null 直到 review
calibration_delta:        # null | "as_expected" | "better" | "worse" | "too_early" | "irrelevant"
confidence:               # null | 0.0-1.0 — review 时回填，用于 Brier score 校准
lesson:                   # null | 1-2 句话
---

# 决定: {{TITLE}}

{{CONTEXT}}
