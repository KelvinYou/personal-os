# Nutrition Source — 读取契约

替代旧的 `meal-library.md`（已删除，见 `docs/plan-public-knowledge-integration.md` §13.1）。
公共食材事实/价格现在唯一 owner 是 `repos/kelvinyou-notes`（public submodule）；
本文件只放**查询规则 + 无法剥离的私有内容**。

> **2026-08-24 更新**：结构化餐食模板（`datasets/nutrition/meals/`、
> `nutrition.py` 的 `meal`/`search` 子命令）已移除——排餐不再拼装固定食材组合，
> 改成从「已知食材 id」里挑选 + 参考 notes 里的技法/搭配笔记（腌制方法、隔夜燕麦
> 搭配等，见 `repos/kelvinyou-notes/docs/health/nutrition/`）。`nutrition.py` 现在
> 只有 `food` 一个子命令。

## 读取优先级（§10）

1. `data/user_profile.md` — 个人目标、偏好、禁忌
2. `data/protocol/standard_week.md` — 当周 baseline
3. `scripts/nutrition.py food <id>` — 只查所需的一条食材
4. 仅当用户问理由、或要具体做法时，才读 `repos/kelvinyou-notes/docs/health/nutrition/`
   的 evidence/技法文档

排餐**不读整个营养数据集**，只查用得到的那一条。

## 查询命令

```sh
python3 scripts/nutrition.py food <food_id>
```

输出示例：

```text
id: chicken_breast_raw
name: 鸡胸肉 (chicken breast, raw weight)
basis: 100g_raw
protein: 23g  carbs: 0g  fat: 3.6g  sugar: 0g
kcal: 124
price: ~RM1.5 / 100g
source_updated: 2026-08-19
```

**已知食材 id**（`python3 scripts/nutrition.py food <id>` 逐一确认，不要凭空造 id）：
`egg`、`chicken_breast_raw`、`wholemeal_bread`、`brown_rice_cooked`、`white_rice_cooked`、
`potato`、`rolled_oats`、`greek_yogurt`、`whole_milk`、`cheese_slice`、`taiwan_sausage`、
`whey_protein_powder`、`ikan_kembung`、`tempeh`、`salmon_raw`、`dory_fillet_raw`、
`shrimp_peeled_raw`、`vegetables_mixed`、`almonds`、`walnuts`、`chia_seeds`、
`dark_chocolate_999`、`keto_almond_chocolate`、`black_sesame_powder`、`black_sesame_oil`、
`cocoa_powder_100`、`matcha_powder`、`frozen_blueberries`、`creatine_monohydrate`、
`magnesium_glycinate`。

**技法/搭配参考**（做法而非结构化数据，人类可读文档）：
`repos/kelvinyou-notes/docs/health/nutrition/chicken-marinades.md`（鸡胸腌制 3 种）、
`overnight-oats.md`（隔夜燕麦搭配 + 比例）、`supplements.md`（补剂证据等级）。

## 明确的错误模式（不做 graceful fallback）

- `repos/kelvinyou-notes` 未 checkout → `nutrition.py` 硬报错并提示
  `git submodule update --init repos/kelvinyou-notes`（notes 是公开仓库，任何人
  `clone --recursive` 都拿得到，不存在 `data/` 那种权限降级场景）
- 未知 food id、价格缺失
- 绝不静默编造营养数值，绝不用个人目标顶替公共事实

---

以下内容**不可剥离**（全部依赖 `{{placeholder}}` 或纯私有阈值，见 plan §9），
从旧 `meal-library.md` 原样保留：

## AM 训练日餐食模板 (目标 `{{protein_target_g}}`g P / `{{kcal_training_day}}` kcal)

蛋白目标 = `{{body_weight_kg}}` kg × `{{protein_per_kg}}` g/kg = `{{protein_target_g}}`g。

| Meal slot | 内容 | Protein | Carbs | Fat | kcal |
|------|------|---------|-------|-----|------|
| Pre-workout | 轻量、易消化的碳水/蛋白组合 | 按 profile | 按 profile | 按 profile | 按 profile |
| Post-workout breakfast | 高蛋白早餐 + 训练后碳水 | 按 profile | 按 profile | 按 profile | 按 profile |
| Lunch | 蛋白源 + 蔬菜 + 主食 | 按 profile | 按 profile | 按 profile | 按 profile |
| Snack | 按当天目标补足蛋白或碳水/脂肪 | 按 profile | 按 profile | 按 profile | 按 profile |
| Dinner | 瘦蛋白 + 蔬菜；是否加主食由 profile 决定 | 按 profile | 按 profile | 按 profile | 按 profile |
| **合计** | 以 `data/user_profile.md` §0 的 phase target 为准 | `{{protein_target_g}}` | — | — | `{{kcal_training_day}}` |

具体时间、份量、禁忌、库存和补足方式必须从 private profile/protocol 解析；本文件不保存个人版本差异。
食材候选从上面「已知食材 id」用 `nutrition.py food <id>` 逐个查询，不要在本文件写死示例食物。

## 休息日餐食模板 (目标 `{{protein_target_g}}`g P / `{{kcal_rest_day}}` kcal)

| Meal slot | 内容 | Protein | Carbs | Fat | kcal |
|------|------|---------|-------|-----|------|
| Breakfast | 蛋白质早餐 + 适量碳水/脂肪 | 按 profile | 按 profile | 按 profile | 按 profile |
| Lunch | 蛋白源 + 蔬菜 + 主食 | 按 profile | 按 profile | 按 profile | 按 profile |
| Snack | 按当天目标补足营养 | 按 profile | 按 profile | 按 profile | 按 profile |
| Dinner | 瘦蛋白 + 蔬菜；是否加主食由 profile 决定 | 按 profile | 按 profile | 按 profile | 按 profile |
| **合计** | 以 `data/user_profile.md` §0 的 phase target 为准 | `{{protein_target_g}}` | — | — | `{{kcal_rest_day}}` |

> 休息日仍高于 BMR 底线 (`{{bmr_floor_kcal}}` kcal)。距 `{{kcal_rest_day}}` 目标约 300 kcal 缺口，
> 同训练日：用碳水/脂肪补，不加蛋白。

## 每日蛋白质校验

- **当前目标: `{{protein_target_g}}`g/天 (`{{protein_per_kg}}` g/kg × `{{body_weight_kg}}`kg)** — 从
  `data/user_profile.md` §0 解析。训练日/休息日统一，不再分开。
- 排餐后应快速加总蛋白质，确认接近 `{{protein_target_g}}`g（±5-10g 容差即可，不必卡死）
- **总量 > 分布**: 凑到日总量优先，单餐 30-50g 即可，不需要刻意堆量
- **Pre-sleep casein 是否安排由 private profile/protocol 决定**；本文件不假定最后一餐时间

### 阶段切换映射

**不要在本文件里维护阶段数值** —— 蛋白/热量目标全部从 `data/user_profile.md` §0 的
`nutrition.<phase.current>` 解析，切换阶段只需改 §0 的 `phase.current`。

| 需要的值 | 键路径 |
|---|---|
| 当前阶段 | `phase.current` |
| 蛋白目标 | `nutrition.<phase.current>.protein_g_target` |
| 训练日 kcal | `nutrition.<phase.current>.training_day_kcal` |
| 休息日 kcal | `nutrition.<phase.current>.rest_day_kcal` |

## 饮食红线

- 大复合动作日（Leg Day / 超大训练量日）**前 2 小时内**，避免大体积慢碳水与高脂食物 — 防范消化负荷引发血管迷走反应。训练前 1h 可摄入轻食（香蕉、饭团等快碳）
- 咖啡因截止时间: 14:00（超过 16:00 视为严重违规，强关联失眠）
- **热量底线**: 休息日摄入 ≥ `{{bmr_floor_kcal}}`，具体值从 private profile 解析
- **脂肪底线**: ≥ `{{fat_floor_g}}`，具体值从 private profile 解析
- **周减体重**: 遵守 private profile 中的体重变化护栏，不在本文件复制个人数值

## 弹性饮食规则

- **合理代偿 (Cheat Meal)**: 周末极度疲惫时允许弹性放纵（如火锅 Buffet），保护多巴胺防线
- **防暴食替换**: 额外零食摄入后，当餐或下一餐削减等量热量。晚餐可重置为 200g Greek Yogurt + 杏仁
- **下午茶弹性**: cut 期间可从碳水腾出 ~200 kcal 弹性预算给偶尔下午茶（甜点/零食），不吃则自动变成更大 deficit（bonus）

## 补剂 (Evidence-based only)

证据等级说明见 `repos/kelvinyou-notes/docs/health/nutrition/supplements.md`（公共 evidence，
Trommelen/Tagawa 同一批引用体系）。以下只保留剂量/时机——依赖 private
profile/protocol，不可剥离：

| 补剂 | 剂量 | 时机 | 月成本 |
|------|------|------|--------|
| **Creatine Monohydrate** | 5g/天 | Pre-workout shake 一起 | ~RM40（见 `nutrition.py food creatine_monohydrate`） |
| **Magnesium Glycinate** | 按 profile/protocol | pre-sleep slot from private protocol | market estimate（见 `nutrition.py food magnesium_glycinate`） |
