# 审计复核 —— 修订章节 (2026-08-11)

> 用途：替换《Personal-OS 审计复核 (2026-08-10)》中的 §0、§1 第四步、§2b、§2c、§4a、§4d，
> 并新增附录 A（集中收纳原文散落在正文里的「修正初版」段落）。
> 修订原因：原文 §0「复核环境」的三项观测（`data/` 未初始化、`submodule.data.update = none`、
> `.venv` 不存在）在 2026-08-11 复测中全部不成立，而 §2b/§2c/§4a/§4d 的论证建立在这三项之上。
>
> 本文件 untracked，正文只含文件路径、行号与仓库公开属性，不含个人数据。

---

## 0. 复核元信息（重写）

被复核的材料：由用户在会话中粘贴的两份审计文本。其中第二份自述为三份独立审计的综合，
但原始三份未提供给本次复核。因此下文的「审计声称」指的是粘贴文本中的表述，
无法追溯到具体的生成工具、模型或时间。

### 0.1 复核环境（2026-08-11 实测）

| 项 | 值 | 采集命令 |
|---|---|---|
| 分支 / commit | `main` @ `f54387c` | `git rev-parse --short HEAD` |
| 平台 | macOS (darwin 25.1.0) | — |
| working tree | 3 项改动：`M .agents/skills/coach-planner/references/meal-library.md`、`m data`（submodule 内容有改动）、`M repos/portfolio-website`（指针） | `git status --short` |
| `docs/` | **不存在** | `ls docs` → No such file or directory |
| `data/` submodule | **已初始化并 checkout 到 `heads/main`**（`75556509`）。内含 `daily/ decisions/ finance/ fitness/ jobs/` + `.git` | `git submodule status` / `ls -a data` |
| `submodule.data.update` | **未设置**（`git config --get` exit 1） | `git config --get submodule.data.update` |
| `.venv` | **存在**，`.venv/bin/python3` 可用 | `ls .venv/bin/python3` |
| 主仓库可见性 | `"private": false` | GitHub API `/repos/KelvinYou/personal-os` |
| 主仓库 fork 数 | `0` | 同上，`forks_count` |
| `data/` submodule remote | `https://github.com/KelvinYou/personal-os-data.git`，**private**（未授权 API 返回 404） | `.gitmodules` + GitHub API |

### 0.2 本次复核未执行的操作

未运行任何 `make` 目标，未运行 `git filter-repo`，未修改任何被 tracked 的文件。
所有结论来自只读命令（`git config/status/ls-files/submodule status`、`grep`、`sed`、`ls`、
GitHub 只读 API）。

### 0.3 相对上一版环境描述的四处撤回

| 上一版声称 | 实测 | 受影响章节 |
|---|---|---|
| `data/` 未初始化，目录存在但为空且无 `.git` | 已初始化，有内容 | §2b、§4a |
| 隐私隔离靠本机 `.git/config` 的 `submodule.data.update = none` | 该配置不存在 | §2c（结论方向要改） |
| 本机 `.venv` 不存在，`make report` 在 lint 环节即失败 | `.venv` 存在，`make report` 可跑到底 | §4a、§4d |
| `/Users/kelvin/...` 是「旧用户名 + 旧路径」 | 用户名与路径均为当前值；问题是不可移植，不是失效 | §4b、§4c |

### 0.4 脱敏说明

初版复核报告直接引用了真实 HRV 数值与逐笔消费金额，这与它自身的 P0 结论矛盾。
本版已全部替换为占位描述。

---

## 1（第四步）. 历史清洗 —— 定论（重写）

原文把这一步留作「需独立评估」，并列出三条判断依据，但三条都没去查。现已全部查明：

| 依据 | 实测值 | 采集方式 |
|---|---|---|
| 是否存在已知 fork | **0** | API `forks_count` |
| star / watch / subscribe | **0 / 0 / 0** | API `stargazers_count`、`watchers_count`、`subscribers_count` |
| 公开暴露时长 | **约 4.5 个月**（`d88d9c0` @ 2026-03-27 → 2026-08-11） | `git log --diff-filter=A -- '.claude/skills/coach-planner-workspace/*'` |
| 仓库年龄 / 提交数 / 远端分支 | 2026-03-23 创建 / 99 commits / 仅 `refs/heads/main` | API `created_at`、`git rev-list --count`、`git ls-remote --heads` |

**结论：做，但要拆成两件难度完全不同的事。**

### 1d-i. eval workspace（廉价，直接做）

`.claude/skills/coach-planner-workspace/` 在历史里**只被一个 commit 触碰过**（`d88d9c0`，
新增后从未修改）。所以这是一次纯路径删除，`--invert-paths` 即可，无需内容级替换：

```bash
git filter-repo --invert-paths \
  --path .claude/skills/coach-planner-workspace \
  --path .agents/skills/coach-planner-workspace
git push --force-with-lease origin main
```

代价评估：0 fork、0 watcher、单分支、99 commits——没有任何第三方需要 rebase，
唯一受影响的是用户自己其他机器上的 clone（重新 clone 即可）。**代价接近零，收益明确，直接做。**

### 1d-ii. SKILL.md 里的个人画像（昂贵，需先做产品决定）

`.agents/skills/*` 被 **33 个 commit** 触碰。这些文件是系统本身的代码，不能删路径，
只能做内容级替换（`git filter-repo --replace-text`），而且：

- 替换规则要逐个数值手写，漏一个就等于没洗；
- 33 个 commit 的 diff 全部改写，等于整条历史的 SHA 变更（这一点与 1d-i 共享，做一次即可）；
- 更关键：**只有先决定 §1b 的三选一（搬进 `data/`、占位符注入、或明确接受公开），
  才知道要替换成什么**。在那之前洗历史是无意义的——修完代码还会再写回同类数据。

**所以顺序是**：§1b 定案 → 改代码 → 一次性 `filter-repo`（同时带上 1d-i 的路径删除）→ force push。
不要为了赶 P0 先洗一遍再洗第二遍。

### 1d-iii. 三条必须写进 ADR 的限制

洗历史**不等于**收回已发布的数据。以下三点无法通过任何操作解决，只能记录并接受：

1. **GitHub 侧的孤立对象**：force push 后旧 commit 在一段时间内仍可通过 SHA 直接访问，
   直到 GitHub GC。要立即失效需联系 GitHub Support 手动清理。
2. **4.5 个月的抓取窗口不可知**：搜索引擎、AI 爬虫、第三方镜像站在此期间是否取走过副本，
   无法验证也无法撤回。0 star / 0 fork 只说明**没有人类主动关注**，不说明没有机器抓取。
3. **`git filter-repo` 会重写全部 99 个 commit 的 SHA**。仓库里任何引用旧 SHA 的地方
   （本文件、`plan.md`、commit message 里的交叉引用、submodule 指针记录）都会失效。
   本文件引用的 `f54387c` / `d88d9c0` 在洗完之后即为历史值——建议洗完后在 ADR 里
   记一张旧→新 SHA 对照表，或直接标注「以下 SHA 属清洗前历史」。

第 2 点是这个决定的真正性质：**洗历史降低的是未来被偶然发现的概率，不是已发生暴露的事实。**
判断依据因此不是"能否收回"，而是"这批数据（健康读数、消费明细、体重、现金流）
继续以零成本可检索的形式挂在 public 仓库上，是否可接受"。答案显然是否，所以做。

---

## 2b. mkdir 会污染 `data/` 下的目录树（重写）

**确认代码事实，但危害论证要换前提。**

三处在 `data/` 子树下无条件 `mkdir(parents=True, exist_ok=True)`：

| 位置 | 目标 | 触发时机 |
|---|---|---|
| `scripts/lib/logger.py:33` | `LOG_DIR = ROOT / "data" / "logs"`（`:10`） | 每次 `make check` / `make weekly` |
| `scripts/decision_new.py:32` | `DECISIONS_DIR = PROJECT_ROOT / "data" / "decisions"`（`:12`） | `make decision-new` |
| `scripts/sync_coros.py:137` | `FITNESS_DIR = ROOT / "data" / "fitness"`（`:24`） | `make sync-coros` |

（`lib/gcal.py:52` 的 `CRED_DIR` 指向仓库根 `.credentials/`，不在 `data/` 下，不受影响。）

**危害的正确范围**：在这台机器上，`data/` 已经初始化，所以 `parents=True` 只会在一个
合法的 submodule 工作树里补建子目录——不构成即时故障。真正的风险场景有两个，都不是当前状态：

1. **新机器 / CI，克隆时未 `--init data`**：此时 `data/` 是空挂载点。任一脚本跑过之后
   目录变为非空，`git submodule update --init data` 会拒绝检出，且报错不指向真正原因。
2. **无 `data/` 仓库访问权限的协作者**：同上，且他们会在本地静默生成一棵伪 `data/` 树，
   后续所有脚本"成功"地读到空数据集（与 §4a 同一个失败模式）。

**guard 的正确写法**：`data/` 作为挂载点时目录可能存在，所以 `DATA_DIR.is_dir()` 会放行，
起不到保护作用。必须检测 submodule 是否真正初始化：

```python
# scripts/lib/paths.py（见 §6 第 1 项，与路径常量收敛一起做）
DATA_DIR = ROOT / "data"

def require_data_dir() -> Path:
    """data/ 是 submodule 挂载点：目录存在 ≠ 已初始化。"""
    if not (DATA_DIR / ".git").exists():
        raise SystemExit(
            "[Status: Critical] data/ submodule 未初始化。\n"
            "  有权限：git submodule update --init data\n"
            "  无权限：本仓库的代码路径需要 data/ 才能运行，见 README「两种 setup 模式」。"
        )
    return DATA_DIR
```

调用点：三处 `mkdir` 之前，以及 `daily_log.py:17`（`DAILY_DIR`）、`migrate.py:24` 的模块
加载路径上。Makefile 的 `today` / `daily` 是纯 `sed`，不经过 Python，需单独加一行目录检查。

**附带项**：`weekly_synthesis.py:215` 往仓库根写 `weekly_report_prompt.md`——已在
`.gitignore` 里，不是泄漏风险，但生成物不该落在 repo root。

---

## 2c. 隐私隔离机制没有文档化（重写；原结论方向错误）

**原文声称**：隔离靠本机 `.git/config` 里的 `submodule.data.update = none`，不可复现。
**实测**：该配置不存在。原文的因果链是虚构的。

**实际的隔离机制**是 `.gitmodules` 里 `data` 的 remote 指向
`https://github.com/KelvinYou/personal-os-data.git`，而**该仓库是 private**
（未授权 API 返回 404）。也就是说：

- 主仓库 public，但 `git clone --recurse-submodules` 在无凭证时**拿不到** `data/`——
  隔离是由 remote 的 ACL 提供的，不是由任何本地配置提供的；
- 这个契约是隐式的。`.gitmodules` 只写了 URL，没有任何地方说明「`data` 必须保持 private，
  它是本系统唯一的隐私边界」；
- 反过来，一旦 `personal-os-data` 被误改为 public，整个隐私模型无声失效，
  且没有任何检查会发现。

**修正后的动作（优先级仍为 P0，但内容不同）**：

1. 在 `.gitmodules` 的 `data` 段加注释，并在 README 写明：**`personal-os-data` 的 private
   属性是本系统的隐私边界，不得改为 public**；对应地，主仓库里的任何文件都不得内联个人数据
   （这条与 §1b 是同一条约束的两半）。
2. `make scan-privacy`（§1 第三步）除了扫描明文，额外断言 `data` submodule 的 remote
   可见性——`gh repo view KelvinYou/personal-os-data --json isPrivate`，非 private 即 fail。
   这是唯一能防住第 3 点那种无声失效的机制。
3. 文档化两种 setup，各配一个 make 目标：

   | 模式 | 用途 | 命令 |
   |---|---|---|
   | `privacy-isolated` | 工作机 / 公开协作 / CI。只要代码 | `git clone <url>` → `git submodule update --init repos/`。`data/` 保持未初始化，脚本按 §2b 的 guard 明确失败 |
   | `authorized data` | 个人机。完整闭环 | `git clone --recurse-submodules <url>`（需 `personal-os-data` 读权限） |

4. 上一版建议的 `git config submodule.data.update none` **不要加**。它只会掩盖 §2b 的问题：
   把「明确的权限失败」变成「静默的空目录」，而空目录正是 §4a 假绿的输入。
   正确的 privacy-isolated 姿势是不递归克隆 + 让脚本硬失败。

---

## 4a. 数据缺失时 `make report` 假绿（重写：触发条件收窄）

`make report` = `lint check weekly`（`Makefile:79`），三者都走 `.venv/bin/python3`
（`Makefile:4`）。无数据时各环节行为：

| 环节 | 行为 | 退出码 |
|---|---|---|
| `lint_daily.py` | `[Status: OK] All 0 daily logs pass schema validation.` | 0 |
| `report_gen.py` | 正常打印报告，各项全 0 | 0 |
| `weekly_synthesis.py:42-44` | `[Status: Warning] No daily logs found for this week.` → `return` | 0（`main()` 无条件 `return 0`，`:247`） |

**准确的触发条件**（这是与上一版的关键差别）：需要 **`.venv` 就绪 且 `data/` 无当周日志**。
在这台机器上 `.venv` 存在、`data/` 已初始化且有数据，**当前不会触发**。会触发的是：

- 新机器按 README 装好 `.venv`、但忘了 `git submodule update --init data`；
- 无 `data/` 权限的协作者（`data/` 空 + 被 §2b 的 mkdir 补出目录树）；
- 有数据但当周为空（例如刚跨周、或补录延迟）——**这一条在个人机上也会发生**，
  是三者中最容易被忽略的。

三处都会在无人察觉的情况下产出「全 0 但退出码 0」的结论。

**附带问题**：`weekly_synthesis.py` 的早退发生在写 `prompt_path` 之前（`:215`），
所以上一次生成的 `weekly_report_prompt.md` 会原地保留。用户看到文件存在、时间戳是旧的、
终端退出码是 0——三个信号没有一个提示"这次没生成"。

**动作**：
1. `lint_daily.py` / `report_gen.py`：日志数为 0 时打 `[Status: Critical]` 并 `return 1`
   （区分「0 条日志」与「N 条日志全部通过」，当前文案把两者写成同一句）。
2. `weekly_synthesis.py`：当周无日志时 `return 1`；且在早退前**删除或改名**既有的
   `weekly_report_prompt.md`，避免旧产物被当成本次输出。
3. 三处的失败信息都应先调 §2b 的 `require_data_dir()`，让「未初始化」与「已初始化但无数据」
   给出不同的报错。

---

## 4d. `.venv` 与依赖（重写；原文归因错误）

**实测**：`.venv/bin/python3` 存在。上一版「本机 `.venv` 不存在，`make report` 会先在
lint 环节因 `No such file or directory` 失败」不成立，据此推出的「所以走不到假绿」也不成立
（假绿的真实条件见 §4a）。

仍然成立的部分：`Makefile:4` 硬编码 `PYTHON := .venv/bin/python3`，所以**所有** Python 目标
（`lint` / `check` / `weekly` / `report` / `sync-coros` / `sync-calendar` / `migrate` /
`decisions-due` / `decision-new` / `calibration`）在 `.venv` 缺失的机器上会报
`No such file or directory`，而不是一条可执行的提示。纯 shell 目标不受影响
（`help`、`quarterly` 只 echo，`today` / `daily` 用 `sed`）。

这也修正了原始审计里「系统 Python 缺 pydantic」的归因：那是绕过 Makefile 直接跑
`python3 -m unittest discover -s tests -v` 看到的现象，正常路径下根本不会用到系统 Python。
需要修的不是依赖，而是**缺 `.venv` 时的报错质量**。

**动作**：
1. README 补 setup 段：`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`。
2. Makefile 加前置检查，让缺 `.venv` 时给出上面那行命令而不是 `No such file or directory`：

   ```makefile
   PYTHON := .venv/bin/python3

   .PHONY: _venv
   _venv:
   	@test -x $(PYTHON) || { \
   	  echo "[Status: Critical] .venv 未创建。执行："; \
   	  echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; \
   	  exit 1; }
   ```
   所有 Python 目标加 `_venv` 依赖。
3. `requirements.txt` **已经完整**（PyYAML / pydantic / pydantic-settings / python-dotenv +
   4 个 google-auth 包），不需要改。要改的是 `CLAUDE.md:25`「依赖: PyYAML」——它漏了
   pydantic 等 7 个包，而这份文件注入每个 session。这条与 §5a 的「禁止硬编码」声明失准
   属同类问题，归到 §3 一起改。

---

## 附录 A. 已撤回的结论（原文散落的「修正初版」集中收纳）

**为什么要集中**：原文在 §1 第四步、§2a、§3、§4a、§4d、§5b、§6、§7c 共 8 处夹叙夹议地
"修正初版"。作为一次性会话笔记可以，但作为留档文档，读者只需要最终判断——正文里的
"初版说 X，但 X 错了，其实是 Y" 应当只留 Y，把 X 移到这里。

下表的「最终判断」列即正文应当保留的表述；「已撤回」列不应再出现在正文任何位置。

### A.1 原文自行撤回的（8 条）

| # | 章节 | 已撤回的表述 | 最终判断 |
|---|---|---|---|
| 1 | §1 第四步 | 洗历史「仅在仓库需要保持 public 时才必要」 | 条件错。改 private 不收回已有 fork / clone，所以「是否洗历史」独立于「是否改 private」，按数据敏感度 + 暴露面判断（定论见本文件 §1 第四步） |
| 2 | §7c | Google Calendar「全仓 markdown 零次提及」 | 不成立。skill 层有完整文档（`coach-planner/references/schedule-rules.md:68-90`、`coach-planner/SKILL.md:216-218`）。准确的缺口是顶层文档未提及 |
| 3 | §7c | `knowledge-*` 空目录「删掉即可」 | 措辞错。它们 untracked，删除只影响本机。真正要判断的是「计划中未实现」还是「已废弃残留」——前者留 placeholder + TODO，后者才 rmdir |
| 4 | §5a | HRV 是「同一阈值的两个值（0.9 vs 0.85）」 | 定性错。config 里的 HRV 键**全是死配置**，代码走自己的硬编码（`daily_log.py:83`）。0.9 与 0.85 是否该是同一个值是独立的产品决定 |
| 5 | §5b | 同时主张「五个块不是脚本输入」+「断言所有 `sleep.*`/`readiness.*` 键都被消费」 | 两条规则互相打架。正确顺序是先给每个块标注 owner（engine / skill），再按 owner 分别测试 |
| 6 | §3 | `AGENTS.md` → `See CLAUDE.md.` 单向指向 | 会让 Claude 隐性成为「主 harness」。应抽公共内容到 `docs/agent-contract.md`，两份文件各自 include + 只保留 harness 差异 |
| 7 | §6 | 路径常量重复计数漏掉 `sync_calendar.py:25` | 因为它用 `ROOT = ...parent.parent`（与 `parents[N]` 系列同名但写法不同），两种 grep 模式都匹配不到。修正后合计 23 处（production 22） |
| 8 | §5c | Spending Surge 熔断器「缺 metric」 | 范围更大。`single_transaction` 是逐笔快照概念，周级条件无落脚点；且三条 action 没有一条能被 `breakers.py` 执行，全是给 agent 看的 prose → 需要 `enforcement: auto \| advisory` 字段 |

### A.2 本次（2026-08-11）新撤回的（4 条）

均因原文 §0「复核环境」观测过期，详见本文件 §0.3：

| # | 章节 | 已撤回的表述 | 最终判断 |
|---|---|---|---|
| 9 | §0 / §2b / §4a | `data/` submodule 未初始化，目录存在但为空且无 `.git` | 已初始化并 checkout 到 `heads/main`，内含 `daily/ decisions/ finance/ fitness/ jobs/` |
| 10 | §0 / §2c | 隐私隔离靠本机 `.git/config` 的 `submodule.data.update = none` | 该配置不存在。真正的隔离机制是 `personal-os-data` remote 为 private（见 §2c 重写） |
| 11 | §0 / §4a / §4d | 本机 `.venv` 不存在，`make report` 在 lint 环节即失败，所以走不到假绿 | `.venv` 存在。假绿的真实条件是「`.venv` 就绪 + 当周无日志」（见 §4a 重写） |
| 12 | §4b / §4c | `.codex/hooks.json` 与 `weekly-review/SKILL.md:32` 里的 `/Users/kelvin/...` 是「旧用户名 + 旧路径」 | 用户名与路径均为当前值。问题是**不可移植**（应改 `$CLAUDE_PROJECT_DIR`），以及 `.codex/hooks/` 目录确实不存在——后者才是真 bug |

### A.3 一条元教训

12 条撤回里有 4 条（A.2 全部）源于同一个原因：**环境观测与结论撰写之间存在时间差，
而观测没有在定稿前复采一次**。这比任何单条技术债都值得先修——它决定了整份报告的可信度上限。

对应到 §6 的收敛动作：环境事实应当由脚本采集而非手写。建议加 `make audit-env`，
输出本文件 §0.1 那张表（commit、submodule status、`.venv` 是否存在、remote 可见性），
任何审计报告的环境节直接贴它的输出，不再手写。

---

## 附录 B. 其余章节的核实结果（§1a–1c、§3、§5、§6、§7、§8、§9）

前一轮只重写了环境相关章节。本节把剩下的全部逐条核实，结论：**大部分成立，7 处需要修正，
其中 2 处是计数偏低、1 处是重要的方法论强化。**

### B.1 §6 路径常量 —— 计数偏低，实际比原文更严重

原文报 production 15 处路径常量 + 4 处 `sys.path` mutation。实测：

| 写法 | 原文计数 | 实测 | 位置 |
|---|---|---|---|
| `ROOT = ...parents[1]` | 3（含 test） | 3 | `sync_coros.py:23`、`patch_coros.py:15`、`tests/test_smoke.py:9` |
| `ROOT = ...parents[2]` | 5 | **6** | `lib/{config:10, logger:9, daily_log:16, migrate:23, gcal:28, **wealth:23**}` |
| `ROOT = ...parent.parent` | 1 | 1 | `sync_calendar.py:25` |
| `PROJECT_ROOT = ...parent.parent` | 6 | 6 | `weekly_synthesis:17`、`decisions_due:11`、`report_gen:14`、`decision_new:10`、`lint_daily:11`、`calibration:17` |
| **合计** | 15 | **16**（production 15 + test 1） | |
| `sys.path.insert` | 5（4 production） | **6（5 production）** | 多出 `scripts/wealth_check.py:19` |

两处遗漏都在 wealth 相关文件（`lib/wealth.py`、`wealth_check.py`）——它们用的是与其它文件
相同的写法，所以不是 grep 模式问题，纯粹是漏了。修正后**路径常量重复合计 24 处**（16 + 5 + 3），
`lib/paths.py` + `pyproject.toml` editable install 的收益比原文估计的还大一点。

**frontmatter parser 是 5 个 + 1 个变体**（原文说 5，基本对）：
`split("---", 2)` 出现在 `weekly_synthesis:30`、`decisions_due:16`、`calibration:22`、
`patch_coros:153`、`lib/daily_log:21` 共 5 处；`lib/migrate.py:50,54` 用的是
`startswith("---")` + 逐行扫描，是第 6 个**不同实现**。收敛时别漏掉它——它恰好是唯一
处理"文件没有 frontmatter"这种边界的实现。

### B.2 §1b 公开参考数据 vs 个人数据 —— 原文的区分是对的，而且比它自己说的更重要

抽查它引的四行，全部成立：

| 位置 | 内容 | 分类 |
|---|---|---|
| `coach-planner/SKILL.md:116` | `protein target 161g (recomp 2.3 g/kg @ 70kg), shutdown 22:00, training 3-day…` | **个人数据**（含体重） |
| `wealth-manager/SKILL.md:308` | `Tie it to their RM<redacted>/month cash flow…` | **个人数据**（现金流） |
| `wealth-manager/SKILL.md:42` | 指向 `data/finance/portfolio.yaml` | 引用路径（非数据本体，但暴露结构） |
| `wealth-manager/SKILL.md:306` | `PRS RM3,000 tax relief` | **公开数据**（马来西亚税务政策） |

> **行号口径**：上表四个行号是 **HEAD (`f54387c`) 的值**，已逐一用
> `git show HEAD:<path> | sed -n '<n>p'` 核实。工作区的 `.agents/skills/wealth-manager/SKILL.md`
> 有 **+36/−13 未提交改动**，把这三行推到了 `:43` / `:329` / `:331`。
> 引用 skill 文件行号时必须标明是 HEAD 还是工作区——这是 §0.3 那条元教训的又一个实例。

**这里有个原文没注意到的细节，它反而强化了原文的结论**：`:306` 的公开值与 `:308` 的个人值
**曾是同一个字面量**（本文不复现该值），只隔两行。这意味着 §1 提出的 `make scan-privacy`
白名单**不能基于数值**——按值屏蔽会同时放过 `:308` 的现金流。白名单必须是
**行级 / 上下文级**（例如 `path:line` 精确豁免，或要求豁免项附一句理由注释）。
原文只说"白名单需覆盖公开参考数据"，这条约束要写得更硬。

### B.3 §3 CLAUDE.md 目录结构 —— 5 条全错成立，但其中 1 条性质不同

`CLAUDE.md:6-19` 列的 10 个条目里，5 个在仓库根不存在。但它们的**去向不同**：

| 条目 | 仓库根 | `data/` 下 | 性质 |
|---|---|---|---|
| `/daily/` | ✗ | ✓ | 路径前缀错（漏了 `data/`） |
| `/finance/` | ✗ | ✓ | 同上 |
| `/reports/` | ✗ | ✓ | 同上 |
| `/user_profile.md` | ✗ | ✓ | 同上 |
| `/prompts/` | ✗ | **✗** | **整个目录不存在于任何位置** |

前 4 条加 `data/` 前缀即可。第 5 条不行：`prompts/weekly_review_agent.md` 找不到，
而 `plan.md:143-145` 自己早就把它记为已知问题（"B3. `prompts/` 目录不存在但被引用 🟢 P2"，
`weekly_synthesis.py` 有 fallback stub 所以不崩）。所以 `CLAUDE.md` 这条应当**删除**而非修正
——它描述的是一个从未存在过的目录。

`AGENTS.md` vs `CLAUDE.md` 的 diff 也确认与原文完全一致：仅标题一行 + `/repos/` 三行。
原文"同一份内容 + 一处有意差异 + 一处已发生漂移"的定性准确。

### B.4 §5d 五个死配置块 —— 成立（附一个 grep 陷阱）

`thresholds.yaml` 的 `phase:` / `nutrition:` / `training:` / `body:` / `schedule:` 五个块
确认无任何 Python 消费，靠 `schema.py` 的 10 处 `ConfigDict(extra="allow")` 混过校验
（原文说 `:225` 一处，实际这个模式在 `schema.py` 里用了 10 次：`:139,153,160,166,173,182,195,215,221,234`）。

**grep 陷阱**：`grep "\.training\.\|\.body\."` 会命中 `lib/metrics.py:107-108`（`log.training.today_load`）
和 `:120-121`（`log.body.body_fat_pct`）。这两处读的是 **`DailyLog` 的字段**，与
`thresholds.yaml` 的同名**配置块**毫无关系。做 §5b 的 owner 一致性测试时必须区分
"配置对象属性" 与 "日志对象属性"，否则会把死配置误判为已消费。

### B.5 §7 文档口径 —— 全部成立，一处行号漂移

- **§7a `make report` 语义**：`CLAUDE.md:32` 确实写"一键生成完整周报 (聚合 + 调用 AI)"，
  而 `Makefile:79` 是 `report: lint check weekly` 纯 Python。确认会误导 agent。
- **§7a README 缺 `make lint`**：`grep -c "make lint" README.md` = **0**。确认。
- **§7b 四个来源**：`thresholds.yaml:96` = `120.0`、`README.md:114` = "累计支出 > RM120"、
  `VISION.md:43` = `state "Spend < RM200/wk"` 全部核实一致。
  唯一偏差：评分尺度在 **`:310`**（`# RM100 baseline; scales down to 0 at RM250`），
  原文写 `:301`。原文"四个不同语义的来源，只需修 README 那条"的判断正确。
- **§7c 熔断器 9 个**：`circuit_breakers` 列表实测 9 项
  （Sleep Critical / Sleep Debt L1 / L2 / Energy Collapse / Mental Overload /
  Consecutive Poor Sleep / HRV Recovery Alert / **Spending Surge** / Overtraining Warning）。
  其中 Spending Surge 不可触发（§5c）。确认。
- **§7c `plan.md`**：58,196 bytes ≈ 58KB 确认。自相矛盾确认：`:15-16` 标 A3 `✅ Done (2026-04-23)`，
  紧接着 `:22` 写"剩余最大 liability：`weekly_synthesis.py` schema 未迁移"；`:106-107`
  把 `scripts/lib/`、`lint_daily.py`、`tests/` 标为 `❌ 不存在`，而三者都在。
  移入 `docs/archive/` + 加 `> historical, superseded` 抬头的建议成立。
- **§7c `knowledge-*` / `docs/adr`**：实测**均不存在于文件系统**（不只是 untracked）。
  原文"属本机 untracked 状态，不是仓库债务"的结论成立，但更准确的说法是它们已经没了
  ——所以那三个 skill 是"计划中未实现"还是"已废弃"这个问题仍然要答，只是不涉及任何删除操作。

### B.6 §8 反驳原始审计的三条 —— 全部成立

- **12 个 skill symlink 全部 tracked**：`git ls-files -s .claude/skills/` 显示
  mode `120000`（symlink）**12 个**、mode `100644`（regular file）22 个
  ——后者正是 §1a 的 eval workspace。原始审计"11/12 未 tracked"确认不成立。
- **`.claude/settings.local.json`**：被全局 gitignore 忽略、从未 tracked，是本机配置。成立。
- **`.codex/hooks.json`**：`git ls-files .codex` 命中（是仓库问题），且 `.codex/hooks/`
  目录确认不存在。成立——但按 §0.3 第 12 条，措辞应改为"不可移植 + 脚本缺失"，不是"旧路径"。

### B.7 §4c weekly-review SKILL.md 自相矛盾 —— 成立

`frontmatter :5` 写 `…output next-week P0/P1/P2 objectives (but NOT timetables — timetable
generation is coach-planner's job)`，而 `:193` 在 "Important Principles" 里写
`**Timetable must be actionable**: Every time block should be specific enough that someone
could follow it…`。同一文件内的指令冲突，确认。

### B.8 §9 Plan → Actual 闭环 —— 现状核实成立

`schema.py` 的 `Adherence` 确认只有两个字段：
`timetable: Literal["✅","⚠️","🔴"] | None` + `deviation_note: str | None`，
`model_config = ConfigDict(extra="forbid")`。确实无法回答"哪个计划块完成了多少"。
原文"判断成立，但属新功能而非修复"的定性正确，`plan.md` 也已把它列为 Wave 4（`⏸ Deferred`,
需 Wave 2.5 稳定 1 周 + 2-4 周观察期）——**这一点原文没提**：这条不是遗漏，是有意 defer 的，
所以不该与 P0/P1 修复混在同一份行动清单里。

### B.9 汇总：本轮新增的 7 处修正

| # | 章节 | 修正 |
|---|---|---|
| 13 | §6 | 路径常量 15 → 16（漏 `lib/wealth.py:23`）；`sys.path` 5 → 6（漏 `wealth_check.py:19`）；合计 23 → 24 |
| 14 | §6 | frontmatter 收敛须包含 `lib/migrate.py` 的第 6 个变体（`startswith` 实现，唯一处理无 frontmatter 边界） |
| 15 | §1b | 白名单**不能基于数值**：同一个字面量同时是公开税务额度（`:306`）与个人现金流（`:308`），必须行级豁免 |
| 16 | §3 | `/prompts/` 应删除而非修正——该目录不存在于任何位置，`plan.md:143` 早已记录 |
| 17 | §5d | `extra="allow"` 是 10 处不是 1 处；owner 测试须区分「配置对象属性」与「日志对象属性」以免误判 |
| 18 | §7b | 评分尺度在 `:310`，原文写 `:301` |
| 19 | §9 | 该条已被 `plan.md` 列为 Wave 4 `⏸ Deferred`（有前置条件），不应与 P0/P1 修复同列 |
