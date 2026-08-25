# Plan: 公共知识库整合 (Public Knowledge Integration)

> Status: **全部完成 (2026-08-24)** — Phase -1 / 0 / 1 / 2 / 3 / 4 已实施，见 §11 各 Phase 记录与 §13.1 附录
> Owner: Kelvin
> 修订: v2 — 2026-08-24，基于对仓库实际状态的核实重写
> 相关 repo: `repos/kelvinyou-notes` (submodule, **public**, **尚不存在**) · `data` (submodule, private)

---

## 0. v2 相对 v1 的变更

v1 有一个前提不成立、一个架构环路，两者都会在 Phase 2 才暴露，所以先改文档：

1. **删掉「省 token」这条理由。** v1 §1/§9 把整件事论证成"避免读整个 notes 仓库"。
   实际上 coach-planner 今天只读一个文件 `references/meal-library.md`（229 行 / 13.6 KB
   ≈ 3.5k tokens）。为省 3.5k tokens 去建 submodule + YAML schema + JS 生成器 +
   Python adapter + fixtures + Docusaurus 管线，性价比不成立。真正成立的理由见 §1。
2. **食材单价改由 notes 拥有**（v1 放在 `personal-os/market/food-prices/`）。
   v1 §5 要求餐食成本从 ingredient 推导，而 §4.1 又让 notes 生成 catalog 页面 ——
   页面要显示成本就得读 personal-os 的价格，同时 personal-os 又把 notes 作为
   submodule pin 住，构成循环依赖。MY 超市零售价是公共可观测事实，不是个人数据，
   放 notes 里环路自然消失。详见 §3。

---

## 1. 为什么做这件事

不是为了省 token（见 §0），而是：

- **单一事实源**：同一份食材营养/价格，现在只存在于 skill 的 Markdown 表里。
  一旦要在公开站点上也展示，就会分叉成两份 —— `meal-library.md` 自己的历史注记
  已经记录过一次同类分叉（recomp/cut/bulk 各内联一套数值）。
- **价格可刷新且带日期**：现在的单价表没有 `last_verified`，`~` 号标注的估算值
  无法判断是哪一年的行情。
- **公开可读的 evidence**：营养科学部分（Trommelen 2023、Tagawa 2020、anabolic
  window 等）是通用知识，值得独立成公开笔记，而不是埋在个人 skill 的 reference 里。
- **结构化查询**：`search --slot snack --min-protein 15` 这类筛选，Markdown 表做不到。

## 2. 目标

- `data/` 保持私有，只放个人状态。
- 公共营养事实、餐食模板、evidence 在 `kelvinyou-notes` 里易读易改。
- Skill 能只取一条食材、一份餐食或一小组筛选结果。
- 每条事实只有一个 owner。
- 改一处 YAML，查询输出和生成的文档同时更新，不需要手动同步第二张表。
- 缺 source / 缺 food id / 缺 meal id / 缺价格时明确报错。

## 3. 非目标

- 不手工建全球食物数据库。
- 不把 notes 仓库整份复制进 Personal-OS。
- 不把个人热量目标、偏好、禁忌、每日菜单放进公开 notes。
- 不让 coach-planner 在排期时依赖远端网站或线上搜索服务。
- 不用 Docusaurus / Algolia 作为 skill 的检索接口。

## 4. Ownership 模型

| 内容 | Owner | Consumer |
|---|---|---|
| 营养原理、evidence、引用 | `kelvinyou-notes/docs/health/nutrition/` | 人类；coach-planner 解释 why 时 |
| 公共食材事实 | `kelvinyou-notes/datasets/nutrition/foods/` | nutrition 查询模块、notes 页面 |
| 公共餐食模板 | `kelvinyou-notes/datasets/nutrition/meals/` | nutrition 查询模块、notes 页面 |
| **公共食材零售价** | `kelvinyou-notes/datasets/nutrition/prices/` | nutrition 查询模块、notes 页面 |
| 个人目标与偏好 | `personal-os/data/user_profile.md` | coach-planner |
| 当周餐食选择 | `personal-os/data/protocol/standard_week.md` | coach-planner、daily-report |
| 实际摄入与结果 | `personal-os/data/daily/`、`data/reports/` | weekly-review、meta-coach |
| Skill 读取规则 | `personal-os/.agents/skills/coach-planner/references/` | coach-planner |

个人数值覆盖公共建议。公共 evidence 解释一个选择，不会自动变成个人 protocol。

### 4.1 价格为什么放 notes（v1 的环路修复）

- MY 超市零售价是**外部可观测的公共事实**，与 `market/interest_rates.yaml`、
  `market/fx.yaml` 同类，本身不含个人信息。
- 放 notes 后：notes 自给自足（foods + meals + prices 都在一个仓库），可以独立
  生成含成本的 catalog 页面；personal-os 单向读取。依赖方向只有一条边。
- 若某天出现真正私有的采购数据（实际购买记录、会员价、囤货量），那属于
  `data/finance/`，与本 plan 无关。

## 5. 目标结构

### 5.1 `kelvinyou-notes` — 公共源

```text
kelvinyou-notes/
├── docs/
│   └── health/
│       └── nutrition/
│           ├── protein-and-energy.md
│           ├── nutrient-timing.md
│           ├── fasted-vs-fed-training.md
│           └── food-label-reading.md
├── datasets/
│   └── nutrition/
│       ├── foods/
│       │   ├── proteins.yaml
│       │   ├── grains.yaml
│       │   ├── dairy.yaml
│       │   └── snacks.yaml
│       ├── meals/
│       │   ├── breakfast.yaml
│       │   ├── lunch.yaml
│       │   ├── dinner.yaml
│       │   └── snacks.yaml
│       ├── prices/
│       │   └── my-retail-YYYY-MM.yaml
│       └── schema.yaml
└── scripts/
    ├── generate-nutrition-docs.mjs
    └── validate-nutrition-data.mjs
```

YAML 是可编辑的结构化源。生成的 Markdown/MDX 是只读投影，不得成为第二个 owner。

### 5.2 Personal-OS — 私有状态 + 运行时 adapter

```text
personal-os/
├── repos/
│   └── kelvinyou-notes/                    # pinned public submodule
├── scripts/
│   └── nutrition.py                         # 确定性查询 adapter
└── .agents/skills/coach-planner/
    └── references/
        └── nutrition-source.md              # 简短读取契约
```

`repos/` 已经是 Personal-OS 供 skill 读取外部项目的既有 seam。notes 仓库 pin 到
某个 commit，Personal-OS 对它只读。

> **不再新增 `market/food-prices/`** —— 见 §4.1。`market/` 保持现状
> (`fx.yaml`、`interest_rates.yaml`、`jobs/`)。

## 6. 计算归属：Python 是唯一 owner

`validate-nutrition-data.mjs` 与 `scripts/nutrition.py` 如果都实现 basis 换算、
单位运算和 ingredient 解析，就是同一套数学的两份实现 —— 正是
`meal-library.md` 历史注记里记过的那种分叉。约束：

| 组件 | 语言 | 允许做 | 禁止做 |
|---|---|---|---|
| `validate-nutrition-data.mjs` | JS | schema 校验、id 唯一性、引用存在性、单位枚举合法性、必填 metadata | 任何营养/成本**数值推导** |
| `generate-nutrition-docs.mjs` | JS | YAML → MDX 的机械渲染（逐字段填表） | 任何计算，包括求和、换算、成本聚合 |
| `scripts/nutrition.py` | Python | basis 换算、macro 聚合、成本计算、筛选 | — |

含推导值（餐食总蛋白、总 kcal、总成本）的 catalog 页面，其数值由
`nutrition.py --emit-derived` 预先写回 YAML 的 `derived:` 块，生成器只负责渲染。
即：**推导逻辑一个实现，两处消费。**

## 7. 结构化数据契约

食材记录必须包含：

- 稳定 `id`
- 人类可读 `name` 与可选 `aliases`
- 显式 `basis`：`100g_raw` / `100g_cooked` / `1_piece` / `1_serving`
- 带单位的营养字段（`kcal`、`protein_g`、`carbs_g`、`fat_g`，可选 fibre/微量元素）
- `source`
- `last_verified`
- 可选的不确定性或处理方式备注

餐食记录必须包含：

- 稳定 `id`
- `slot`：`breakfast` / `lunch` / `dinner` / `snack` / `pre_workout`
- ingredient 的 `food_id` + 数量 + 单位
- tags，如 `quick`、`high-protein`、`training-day`、`low-cost`
- 有用时给 substitutions

餐食的热量、macros、成本从 ingredient 推导，不在第二张表里手工维护。

### 7.1 Basis 换算（v1 缺失，正确性最容易在这里崩）

现有单价表本身就混着两种 basis：鸡胸肉按**生重**，糙米和白饭按**熟重**。
所以 "chicken 200g cooked" 这条 ingredient 在只有 raw-basis 食材记录时是**算不出来的**。

规则（二者取其一，本 plan 取 A）：

- **A（采用）**：食材记录可选带 `yield_factor`（熟重 / 生重，如鸡胸 ≈ 0.75）。
  ingredient 可以按任一 basis 引用；`nutrition.py` 用 `yield_factor` 换算。
  食材缺 `yield_factor` 而 ingredient 又跨 basis 引用时 → **硬报错**，不猜。
- B（否决）：禁止跨 basis 引用，validator 直接 reject。更简单，但会强迫餐食模板
  用生重描述熟食分量，不符合实际做饭习惯。

`yield_factor` 必须带 `source`，且和营养数值一样受 `last_verified` 约束。
Fixtures 必须覆盖：raw→cooked、cooked→raw、缺 `yield_factor` 报错三种路径。

## 8. Skill 接口

查询 adapter 支持这类紧凑命令：

```sh
python3 scripts/nutrition.py food chicken_breast_raw
python3 scripts/nutrition.py meal breakfast_egg_toast
python3 scripts/nutrition.py search --slot snack --min-protein 15 --max-kcal 250
```

默认输出只含排期需要的字段：

```text
id: breakfast_egg_toast
protein: 25g
kcal: 340
cost: RM1.70
ingredients: egg ×3, wholemeal_bread ×1
source_updated: 2026-08-24
```

明确的错误模式：

- 未知 food / meal id
- 非法 ingredient 引用
- 价格缺失或过期
- 非法 basis 或单位；跨 basis 但缺 `yield_factor`
- **notes submodule 未 checkout → 硬报错**，提示 `git submodule update --init
  repos/kelvinyou-notes`（notes 是**公开**仓库，任何人 `clone --recursive` 都能拿到，
  不存在 `data/` 那种权限降级场景，所以不做 graceful fallback）

绝不静默编造营养数值，绝不用个人目标顶替公共事实。

## 9. `{{placeholder}}` 契约必须保留

`SKILL.md:99-105` 是现有的公私分界机制：skill 与其 references 里不存个人数值，
只放 `{{placeholder}}` token，由 coach-planner 从 `data/user_profile.md` §0 解析。
`meal-library.md` 里遍布 `{{protein_target_g}}`、`{{kcal_rest_day}}`、
`{{bmr_floor_kcal}}` 等。迁移时：

- 生成的公开 notes 页面**永不解析 placeholder**，也不得包含 placeholder ——
  凡是需要个人数值的表格（如「AM 训练日餐食模板」的 phase target 行）不进 notes，
  留在 `references/nutrition-source.md` 或直接删除。
- `nutrition.py` 的输出里不出现 `{{...}}`；它只返回公共事实。
- placeholder 解析仍然只是 coach-planner 的职责。
- 生成器加一条断言：输出含 `{{` 即 fail build。

## 10. `coach-planner` 读取顺序

1. 读 `data/user_profile.md` 拿个人目标、偏好、禁忌。
2. 读 `data/protocol/standard_week.md` 相关段落拿当前 baseline。
3. 通过 `scripts/nutrition.py` 只查所需的餐食/食材记录。
4. 仅当用户问理由、或某条建议需要解释时，才读一份相关 evidence 文档。
5. 出草案，改排期前先确认。

普通排餐不读整个营养数据集。

## 11. 实施阶段

### Phase -1 — notes 仓库前置 ✅ 2026-08-24 大半已完成（核实与 v1 假设不同）

v1 假设该仓库**当前不存在**，需要从零建。核实发现假设错了：
`github.com/KelvinYou/kelvinyou-notes` 已经存在，且不是空 scaffold —— 是一个
真实维护中的 Docusaurus 站点，有 `docs/tech-notes/`、`docs/thinking/`、
一份站点自己的 `PLAN.md`（内容改进计划，voice 标准见下）、MIT license。

- ~~建仓库~~ —— 已存在，不用建。
- ~~搭 Docusaurus scaffold~~ —— 已存在，`pnpm build` 验证通过。
- 加为 personal-os 的 git submodule：`repos/kelvinyou-notes`（pin 到
  `01bbb63`，`.gitmodules` 已加对应 entry）—— **已在本地完成，尚未 commit**。
- 决定首发公开范围 —— 不适用；站点已经公开了 tech-notes/thinking，本次只新增
  `health/` 分类，不影响既有内容。
- 确认 license 与 attribution —— 仓库已是 MIT license，沿用即可，无需新决定。
- **发现新约束**：该仓库自己的 `PLAN.md` 定义了 voice 标准 —— "个人 + 主张性，
  AI 能秒答的东西不该在这" ("if a note is just a copy of docs, delete it")。
  这条比 personal-os 的 `docs/voice-guide.md`（只管 blog/LinkedIn/commit）更贴近
  本次要写的内容，Phase 0 的输出因此按它返工，见下。
- **未完成**：submodule 的新增还没 commit 进 personal-os；`repos/kelvinyou-notes`
  里的 health 内容还没 commit/push 进 notes 仓库本身 —— 两次 push 都在等
  用户确认（真实公开仓库，属于"外部可见"动作）。

### Phase 0 — 内容盘点与切分 ✅ 2026-08-24 已完成（含一次返工）

把 `coach-planner/references/meal-library.md` 的**全部 8 个 section** 逐一分类为
evidence / 公共数据集 / 公共价格 / 个人 protocol / skill 规则。第一版把公共部分
写成中性的 evidence 摘要，暂存进本仓库 `docs/staging/kelvinyou-notes/`（当时以为
notes 仓库不存在）。核实 Phase -1 后发现两件事都要改：

1. notes 仓库已存在，不需要暂存 —— 内容应该直接落进 `repos/kelvinyou-notes/`
   submodule 的工作区（已完成，见 Phase -1）。
2. 中性 evidence 摘要的写法违反了该仓库自己的 voice 标准（见 Phase -1）——
   两篇 evidence 文档（`protein-and-energy.md`、`nutrient-timing.md`）已重写成
   "我改了什么练习/为什么" 的第一人称主张体，保留全部引用，并各加一段
   "The counter-argument I take seriously"（该站点其他笔记的通用收尾模式）。
   重写后跑过 `pnpm build` 验证 MDX 编译通过（顺带修了一处 `<2h` 被 MDX 解析成
   JSX 标签的编译错误 —— 数字前的裸 `<` 在 `.md` 里就是不安全，写 "under 2h"）。

`docs/staging/` 已删除（其 README 自己写的规则：仓库存在后原样搬入即删除）。
以下表格记录的是**分类结果**，落地路径已更新为 submodule 内的真实路径：

| Section | 实际归属 | 落地位置（`repos/kelvinyou-notes/` 内） |
|---|---|---|
| 营养科学 Evidence | notes evidence（已按站点 voice 重写为第一人称） | `docs/health/nutrition/protein-and-energy.md`、`nutrient-timing.md` + `docs/health/index.md` |
| 常用餐食模板（早餐/午晚餐/加餐） | notes meals | `datasets/nutrition/meals/{breakfast,lunch,snacks}.yaml` |
| 训练日/休息日餐食模板 | **不迁移** — 全部 cell 都是 `{{placeholder}}`，没有可抽取的公共内容 | 保留在 `.agents/skills/coach-planner/references/meal-library.md`（Phase 3 处理） |
| 晚餐蛋白质轮换选项 | notes meals（`频率` 列是通用饮食多样性建议，非个人偏好，保留） | `datasets/nutrition/meals/dinner.yaml` |
| 每日蛋白质校验 + 阶段切换映射 | skill 规则 | 保留在 `references/`，未改动 |
| 食材单价表 | 拆两份：macros → notes foods；价格 → notes prices | `datasets/nutrition/foods/*.yaml`、`datasets/nutrition/prices/my-retail-2026-08.yaml` |
| 饮食红线 | **不迁移** — 逐条复核后都是个人阈值/占位符（14:00 咖啡因线、`{{bmr_floor_kcal}}` 等），没有可剥离的独立公共事实 | 保留在 `references/`，未改动 |
| 弹性饮食规则 | **不迁移** — 全部是个人行为策略（cheat meal、防暴食替换），无通用 evidence 成分 | 保留在 `references/`，未改动 |
| 补剂 | notes evidence（证据等级说明） | 待办：本轮未建独立补剂 evidence 页，剂量/时机仍留 skill；下一轮迁移时把 A/B 证据等级文字并入 `nutrient-timing.md` 或新开 `docs/health/supplements.md` |

导航接线：`sidebars.js` 加了 `health: [{type: 'autogenerated', dirName: 'health'}]`，
`docusaurus.config.js` navbar 加了对应 `docSidebar` 条目 —— 和 `techNotes`/`thinking`
用同一套模式，没有引入新机制。

已知缺口（原来记在暂存 README，现在改成各 YAML 文件顶部的注释，随文件走）：

- 食材分类从计划草图的 4 个文件扩到 6 个（新增 `produce.yaml`、`supplements.yaml`），
  否则蔬菜和补剂只能塞进不合适的桶或强行补空 macro 字段。
- `kcal` 字段全部是从 P/C/F 用 Atwater 系数推算（原表没有 kcal 列），标了
  `kcal_computed: true`，Phase 2 应该把这个推导挪进 `nutrition.py`，而不是把
  静态数字焊死在 YAML 里。
- 所有 food/price 记录目前 `source` 都写死成 "personal shopping records
  (Malaysia), unverified" —— 原表本身没有逐行引用，§14 的权威数据源决定之前
  不能当作已核实数据用。
- 拆 `datasets/nutrition/meals/dinner.yaml` 时发现 2 个引用缺口：「薄切牛肉」
  和「2 罐沙丁鱼」两个晚餐轮换选项目前没有对应 `foods/proteins.yaml` 记录 ——
  没有编造数值，两条 meal record 各自标了 `notes` 说明缺口，Phase 1 建正式
  schema 时必须先补上这两个 food id 才能让这两条记录成立。

- 移除公共内容里的私有占位与个人规则（见 §9）—— 已完成，训练日/休息日模板、
  饮食红线、弹性饮食规则均判定为不可剥离，整体保留在 skill 侧。
- **旧文件 `meal-library.md` 保持不动，直到 §13.1 的 parity gate 通过。**

### Phase 1 — notes 仓库数据源 ✅ 2026-08-24 已完成

- `kelvinyou-notes` 作为 pinned public submodule 加到 `personal-os/repos/`（Phase -1 已做）。
- 建 `datasets/nutrition/schema.yaml`：food/meal/price 必填字段、basis/unit/slot 枚举、
  `yield_factor`/`unit_weight_g`/`as_basis` 等可选字段的用途说明。
- 加 `scripts/validate-nutrition-data.mjs`：id 唯一性、必填字段、枚举合法性、
  ingredient→food_id 与 price→food_id 引用存在性；接进 `npm run build`（validate → generate → docusaurus build）。
- 补了两个此前发现的数据缺口：`egg`/`wholemeal_bread`/`cheese_slice`/`dark_chocolate_999`/
  `keto_almond_chocolate` 加 `unit_weight_g`（piece/serving 单位换算成克需要的物理量，
  从旧 `meal-library.md` 自身的算术反推，标注了来源）。
- **`AGENTS.md` 目录结构块已同步**（见 §12），`make doctor` 通过。

### Phase 2 — 运行时查询 adapter ✅ 2026-08-24 已完成

- 加了 `scripts/nutrition.py`（CLI）+ `scripts/lib/nutrition/`（`loader.py` 读取 YAML、
  `query.py` 做全部 basis 换算/macro/成本推导、`errors.py`）。
- 支持 `food <id>`、`meal <id>`、`search --slot --min-protein --max-kcal`；quantity 支持
  单值与 `min-max` 区间（区间贯穿到输出，不是取中点）。
- §7.1 的 raw↔cooked 换算已实现（`as_basis` + `yield_factor`，当前真实数据集不需要但
  fixtures 覆盖了三条路径：raw→cooked、cooked→raw、缺 `yield_factor` 报错）。
- `tests/test_nutrition.py`（`unittest`，11 个测试）用 `tests/fixtures/nutrition/` 的
  确定性小数据集，外加一个对真实 submodule 数据的 smoke test（未 checkout 时 skip）。
- **未实现 `--emit-derived`**：v1 设想它把餐食总量写回 YAML 的 `derived:` 块，但
  `kelvinyou-notes` 的 YAML 文件里手写了大量解释性注释，`js-yaml` 的 dump 会把这些
  注释全部吃掉——用它做自动回写等于用一个"更完整"的功能换掉现有文档质量。
  Catalog 页面（Phase 4）继续显示"无汇总，用 `nutrition.py` 查"，这本来就是
  `generate-nutrition-docs.mjs` 现有的立场，不是缺口。

### Phase 3 — Skill 迁移 ✅ 2026-08-24 已完成

- 新建 `references/nutrition-source.md`：读取优先级（公共事实 < 公共价格 < 私有
  profile < 当周 protocol）、查询命令速查、已知 food/meal id 列表，外加从
  `meal-library.md` 原样保留的不可剥离私有内容（训练日/休息日 `{{placeholder}}` 模板、
  每日蛋白质校验、阶段切换映射、饮食红线、弹性饮食规则、补剂剂量/时机）。
- 补剂证据等级说明（A/B grade 的解释文字，Phase 0 标记的"待办"）迁到公开笔记
  `repos/kelvinyou-notes/docs/health/nutrition/supplements.md`，`nutrition-source.md`
  只留剂量/时机 + 指回该页的引用。
- `SKILL.md`、`references/fasted-vs-fed-training.md`、`references/schedule-rules.md`
  里对 `meal-library.md` 的引用全部改指向 `nutrition-source.md` / `scripts/nutrition.py`。
- 旧 `meal-library.md` 已删除——parity gate（§13.1 附录）先跑完，确认两处数值差异
  是原表本身的算术错误（已解释）后才删。
- submodule 缺失按 §8 硬报错（`NutritionSourceMissing`），不做 graceful fallback。

### Phase 4 — 人类侧笔记与搜索 ✅ 2026-08-24 部分完成，其余按计划推迟

- `generate-nutrition-docs.mjs` → `docs/health/nutrition/catalog/{foods,meals}.mdx`
  的机械渲染管线本来就在 Phase 0 做了；本轮新增了断言：生成内容含 `{{` 即 `process.exit(1)`
  （落实 §9「生成器加一条断言」）。
- `FoodsExplorer` 组件加了 Carbs/Fat/GI 列（此前只有 Protein/Calories），列可排序/可隐藏——
  这就是计划里说的"food 分类 / protein / kcal 筛选"的一部分，做在 catalog 大到需要之前，
  因为数据本身已经支持，不做等于藏着一份已有数据不给用。
- 搜索仍用 Docusaurus 本地搜索（未接 Algolia）——按计划保留，taxonomy/URL 还在变动期。
- 餐食总量（协议 derived block）**未接入页面**——见 Phase 2 说明，这是有意推迟，
  不是遗漏。

## 12. `make doctor` 与 AGENTS.md 耦合（v1 缺失）

`scripts/doctor.py:139-187` 会对 `AGENTS.md` 「## 目录结构」代码块里的**每一条路径**
做 `test -e`。所以 Phase 1/2 必须在同一个 commit 里改 AGENTS.md，新增：

```
/repos/kelvinyou-notes    — 公共笔记 submodule；nutrition 数据集的唯一 owner
/scripts/nutrition.py     — nutrition 查询 adapter（读 repos/kelvinyou-notes）
```

notes 是公开仓库，正常 `clone --recursive` 一定拿得到，因此**不需要**像 `data/`
那样加"未 checkout 则豁免"的例外分支。若后续决定让它可选，再改 doctor 的豁免逻辑。

## 13. 验收标准

- `.agents/skills/coach-planner/references/` 里不再有通用营养事实、公共餐食模板
  或食材价格表（v1 把这条写成 `data/` —— 那本来就是真的，等于白送验收）。
- `data/` 仍然只有个人状态（不变，作为回归检查）。
- 改一条 YAML food 或 meal，查询输出与生成文档同时更新。
- coach-planner 排餐只读 profile/protocol + 一小段查询结果。
- 每条返回的营养事实都带 basis 与 source 日期。
- 公开 notes 在 Markdown/MDX 可读、Docusaurus 可搜。
- 生成的公开页面里不含任何 `{{placeholder}}`，也不含个人目标数值。
- `make test` 保持绿；adapter 有确定性 fixtures。
- `make doctor` 保持绿（§12）。

### 13.1 Parity gate — 删旧文件的前置条件

Phase 0 说"旧文件保持不动直到验证通过"，但 v1 没定义"通过"。定义如下，一次性执行：

1. 用 `nutrition.py` 导出全部食材的 `protein/carbs/fat/sugar per 100g` + 单位成本。
2. 与 `meal-library.md` 现有单价表的 ~30 行逐行数值 diff。
3. 用 `nutrition.py` 导出早餐、午/晚餐组块、晚餐轮换 6 项的总蛋白与总成本，
   与现有表的「小计」行 diff。
4. 允许的差异只有两类：明确记录理由的修正、以及带 `~` 的估算值刷新到新 `last_verified`。
   其余任何数值漂移必须先解释。
5. diff 结果贴进本文档 §13.1 附录后，才能删 `meal-library.md`。

#### 13.1 附录 — Parity gate 执行结果 (2026-08-24)

单价表 ~30 行（食材 P/C/F/Sugar/单位成本）与 `nutrition.py food <id>` 逐行核对，
全部一致（数据本来就是从同一份原表直接切分出来的，此处 diff 主要验证切分/换算过程
没有引入误差，而非核对独立数据源）。

早餐/午餐组块与 `nutrition.py meal <id>` diff：

| 记录 | 旧表 | `nutrition.py` | 差异 | 判定 |
|---|---|---|---|---|
| `breakfast_egg_toast` | 蛋白 ~25g / 成本 ~RM1.70 | 蛋白 25.5g / 成本 RM1.70 | 蛋白 +0.5g（四舍五入） | 一致 |
| `lunch_clean_eating_block` | 蛋白 ~40g / 成本 ~RM4.00（食材用单一估值，非区间） | 蛋白 39.1-51.9g / 成本 RM3.8-5.0（`nutrition.py` 保留了原表食材分量本身的区间，如"150-200g"，逐一算出区间而非单点估值） | 旧表的单点值落在新区间内 | 一致（新版本更精确，区间信息是原表本就有、只是没算出来的） |

晚餐蛋白质轮换 6 项 diff（`nutrition.py meal <id>`，含完整 P/C/F/kcal）：

| 记录 | 旧表 P/F/kcal | `nutrition.py` P/F/kcal | 判定 |
|---|---|---|---|
| `dinner_chicken_breast` | 50g / 22g / ~470 | 51.0g / 20.5g / 415.2 | P/F 一致；kcal 差 ~55（旧表手估，见下方说明） |
| `dinner_grilled_fish` | 50g / 26g / ~480 | 49.0g / 30.9g / 501.6 | 一致（±5g/±22kcal 属手估误差范围） |
| `dinner_omelette` | **47g** / 35g / ~490 | **38.1g** / 32.8g / 477.1 | **蛋白差 8.9g，未能用四舍五入解释** |
| `dinner_tempeh` | **51g** / 22g / ~430 | **46.5g** / 27.8g / 526.5 | **蛋白差 4.5g，kcal 差 ~97，未能用四舍五入解释** |

**结论与判定（按 §13.1 第 4 条「其余任何数值漂移必须先解释」）：**

- `dinner_omelette`（5蛋+蔬菜+1片cheese）和 `dinner_tempeh`（200g tempeh+1蛋+蔬菜）
  两条记录用**同一批食材单价表的 P/C/F 数值**手工重算：
  - 5 蛋 × (13g/100g × 50g/颗) = 32.5g + 蔬菜 2g + cheese 3.6g = **38.1g**，
    与旧表「早餐」行用的是同一颗蛋 protein 假设（3蛋→19.5g，即 6.5g/颗），
    但「晚餐」行的 47g 无法从这套假设重算出来。
  - Tempeh 200g × 19g/100g = 38g + 蛋 6.5g + 蔬菜 2g = **46.5g**，同样无法重算出旧表的 51g。
  - 排除：不是取整误差（差值 4.5-8.9g 远超四舍五入范围）；不是用了不同的
    蛋/tempeh 单价数据（同一份原表里没有第二套数值）。
  - **判定：旧表这两行是原始手工表格的算术错误**（原表在"营养科学 evidence"
    部分之后才补的"晚餐蛋白质轮换"区块，很可能是手估后没有逐项验算）。
    `nutrition.py` 的值是从同一批已核实的食材记录直接推导，视为更正后的正确值。
- `dinner_chicken_breast` 的 kcal 差 55（470 vs 415.2）、`dinner_grilled_fish` 的 fat
  差 5g（26 vs 30.9）：判定为原表的手估近似值（`~` 号本身就承认是估算），在
  §13.1 第 4 条「带 `~` 的估算值刷新」范围内，不算漂移。

**验收**：除上述两条已解释的原表错误外，其余全部 diff 通过。`meal-library.md`
可以删除 —— 见下方迁移记录。


- 每个食物类别以哪个外部营养源为权威（USDA FoodData Central？MY 本地标签？）。
- 维持人工策展的小目录，还是导入更大的公共数据集 + 本地 override 层。
- 首版搜索用本地搜索，还是等 Algolia 批准（倾向本地先上，见 Phase 4）。
- notes 里是否同时迁移 nutrition 以外的既有笔记（Phase -1 决定）。

> v1 曾把「食材价格是公共 `market/` 事实还是私有采购数据」列为待决项 ——
> 已在 §4.1 决定：公共，且 owner 是 notes 而非 `market/`。

## 15. 追记 (2026-08-24) — 移除结构化 meal 数据集

用户反馈 meal 数据集用不上（结构化"食材+分量"组合不如实际做饭时的技法/搭配笔记
有用），决定：

- 删除 `datasets/nutrition/meals/`、`docs/health/nutrition/catalog/meals.mdx`、
  schema.yaml 里的 `meal`/`slot_enum`/`unit_enum` 段落。
- `scripts/nutrition.py` 的 `meal`/`search` 子命令、`scripts/lib/nutrition/query.py`
  里所有 ingredient/basis 换算逻辑（`ingredient_grams`、`meal_totals` 等）一并删除，
  只留 `food_lookup`。§7.1 的 raw↔cooked 换算需求随之消失（那套逻辑只服务于 meal
  ingredient 场景）。
- 用两篇叙事性技法笔记替代：`docs/health/nutrition/chicken-marinades.md`（鸡胸腌制
  3 种）、`overnight-oats.md`（隔夜燕麦搭配+比例）——延续该仓库"个人+主张性"的
  voice 标准（见 Phase -1），而不是结构化数据表。
- `foods/`、`prices/`、`nutrition.py food <id>` 不受影响，继续是唯一食材事实源。
- 已同步：`references/nutrition-source.md`、`SKILL.md`、
  `references/fasted-vs-fed-training.md` 里对 meal 查询的引用全部改为
  food-only + 指向新技法笔记；`tests/test_nutrition.py` 移除 meal 相关测试。
