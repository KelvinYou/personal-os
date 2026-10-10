# Correction Queue — pending review

See AGENTS.md § "Correction Queue" for the protocol. Entries here await owner review;
accepted, reworded or rejected entries move to `archive.md` with their outcome.

The owner approved the previous queue dispositions on 2026-10-07;
historical corrections and implementation caveats remain in `archive.md`.

<!-- Template for a new entry:

## YYYY-MM-DD — <one-line summary>

**What I did:** <the behavior that needed correcting>

**Your correction:** "<quoted>"

**Proposed AGENTS.md change:** <concrete wording, or "none — one-off, don't generalize">

**Status:** pending

-->

## 2026-10-08 — Keep grocery cost presentation simple

**What I did:** Expanded a grocery-cost update into detailed tables, scenarios,
price bases and repeated accounting explanations.

**Your correction:** "不需要那么specific吧，直接写 xxx - xxx 就行"

**Proposed AGENTS.md change:** none — apply the requested item - quantity - cost
format to this checklist; do not generalize a local formatting preference yet.

**Status:** pending

## 2026-10-08 — Preserve existing tables during targeted content updates

**What I did:** Replaced the full nutrient table with a five-row check and
changed meal/grocery presentation while implementing the nutrient update.

**Your correction:** "我的nutrient表怎么不见了，食物也按之前的格式来，别瞎改"

**Proposed AGENTS.md change:** "For targeted updates to an existing document,
preserve its tables, section coverage and presentation unless the user explicitly
requests a structural change. Scope a request to simplify one part to that part."

**Status:** pending

## 2026-10-09 — Cover composed backtest strategies before concluding

**What I did:** Reported only AI overall versus hold and technical rows, omitting
available momentum allocator and hybrid results from a broad comparison.

**Your correction:** "为什么会漏掉**动量配置器**？如果是skill的缺陷，把skill给优化掉"

**Proposed AGENTS.md change:** none — keep the scoped fix in quant-backtest-review:
establish comparison scope and report allocator, AI and hybrid attribution separately.
The user authorized the skill improvement; no AGENTS.md edit is proposed.

**Status:** pending


## 2026-10-09 — Search the confirmed hotel requirements before narrowing the shortlist

**What I did:** Rechecked a limited existing shortlist and stopped the expanded-budget search with incomplete Rayfont evidence, instead of browsing a dated, filtered station-area search and inspecting nearby candidates individually.

**Your correction:** "按需求search过，一个一个看"

**Proposed AGENTS.md change:** none — the travel-plan hotel workflow already requires search coverage and individual room-offer verification; correct execution and preserve the evidence without adding another rule.

**Status:** pending
