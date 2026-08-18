# Schedule Rules Quick Reference

Coach-planner 的公共规则速查。个人时间、训练日型、餐单、器械、成本和
睡眠 baseline 不属于本文件；它们必须从 private runtime data 读取。

## Ownership

- `data/protocol/standard_week.md`：standing timetable 的唯一人类可读 owner。
- `data/protocol/standard_week.yaml`：standing timetable 的 Calendar anchors projection。
- `data/user_profile.md`：个人作息、饮食、训练偏好与阶段目标。
- `config/thresholds.yaml`：睡眠、HRV、训练与熔断阈值。
- `data/reports/YYYY-w##-delta.md`：只记录例外周相对 standing protocol 的变化。

每次排期先读 `data/protocol/standard_week.md`，再读 profile、daily logs 和 weekly
report。不要从本文件推断个人 baseline，也不要把本文件改成第二份 timetable。

## Planning rules

- 标准周直接执行 standing protocol；没有例外时不生成 weekly timetable、delta 或 calendar sidecar。
- 只有日程例外、熔断限制、目标挂载或一次性实验改变实际时间块时，才生成 dated delta。
- 例外周的 delta 必须表达“相对哪一段 protocol 改了什么”，不要复制完整餐单、训练表或时间表。
- 训练 gate 使用 `config/thresholds.yaml` 和最新日志证据；缺数据时保留不确定性，不猜测 baseline。
- 训练结束与 lights-out 之间至少保留项目 protocol/证据要求的恢复间隔；具体时间从 private data 解析。
- 训练重量、动作架构和 day type 只从 `standard_week.md` 读取；不要在 public reference 维护器械清单。
- 餐点时间、份量、蛋白目标和成本从 `data/user_profile.md` 与 `meal-library.md` 解析；不要在本文件写个人数值。

## Google Calendar sidecar

`scripts/sync_calendar.py` 有两个独立模式：

- `--protocol`：读取 `data/protocol/standard_week.yaml`，同步 recurring anchors。
- `--week`：读取 `data/reports/YYYY-w##-calendar.yaml`，同步某一例外周的 dated events。

例外周 sidecar schema：

```yaml
week: "YYYY-W##"
timezone: "<IANA timezone>"
calendar_id: "primary" # optional; defaults to GOOGLE_CALENDAR_ID
events:
  - date: "YYYY-MM-DD"
    start: "HH:MM"
    end: "HH:MM"
    title: "Calendar event"
    description: "Optional context"
```

同步按 `week` 做 delete-then-insert，sidecar 必须整份覆盖生成，不能追加单个 event。
无时间块变化的周不生成 sidecar；需要发布 Calendar 时才写入
`data/reports/YYYY-w##-calendar.yaml`。OAuth 与权限说明见 `scripts/lib/gcal.py`。

## Weekly delta output

```markdown
# YYYY-W## Delta

> 基线：`data/protocol/standard_week.md`

## Exceptions
- YYYY-MM-DD：哪个时间块改变，以及如何补偿

## Constraints
- active breaker / objective / experiment
```

保存前先以 Draft 呈现并等待用户确认。确认后才写入
`data/reports/YYYY-w##-delta.md`；若没有例外，明确说明无需写文件。

## Timetable output templates

### Daily

```markdown
## [Day] MM-DD 时间表 (Draft)

> 状态快照：睡眠 Xh | 精力 X/10 | 熔断：[None / breaker names]

| 时间 | 行动 | 备注 |
|------|------|------|
| HH:MM | Action | Details from private protocol/profile |
| ... | ... | ... |
| HH:MM | [强制断电] | lights-out from private protocol/profile |
```

### Weekly delta

```markdown
## YYYY-W## Delta (Draft)

> 只写相对 `data/protocol/standard_week.md` 的变化。

| 日期 | Protocol block | Change | Reason |
|------|----------------|--------|--------|
| YYYY-MM-DD | section/time block | exception | report / user input |
```

## Training detail

包含训练日时，日程 row 只写概要；详细区应包含：

1. HRV / sleep gate：阈值来自 `config/thresholds.yaml`，不要复制数字。
2. Weight table：重量来自 private `standard_week.md` 的器械档位；未变化时引用上一份已确认 protocol。
3. 每个训练日的动作、组次、tempo、组间休息、执行 cue 和降档条件。

若用户要求完整 timetable，仍须先读 standing protocol，再把 profile、daily state、weekly objectives
和临时例外合并；完整输出是 escape hatch，不应成为每周默认产物。
