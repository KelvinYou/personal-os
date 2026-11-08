# Correction Queue — pending review

See AGENTS.md § "Correction Queue" for the protocol. Entries here await owner review;
accepted, reworded or rejected entries move to `archive.md` with their outcome.

The owner approved the previous queue dispositions on 2026-10-07;
historical corrections and implementation caveats remain in `archive.md`.

<!-- Template for a new entry:

## YYYY-MM-DD — <one-line summary>

**Class:** `<slug from enforcement.md, or a new kebab-case slug for a first occurrence>`

**What I did:** <the behavior that needed correcting>

**Your correction:** "<quoted>"

**Proposed AGENTS.md change:** <concrete wording, or "none — one-off, don't generalize">

**Enforcement level:** <architecture | types | lint/hook/CI | test | docs> — <why a higher level
doesn't work; which class in enforcement.md this joins, if any>

**Status:** pending

-->

## 2026-10-08 — Keep grocery cost presentation simple

**Class:** `over-detailed-output`

**What I did:** Expanded a grocery-cost update into detailed tables, scenarios,
price bases and repeated accounting explanations.

**Your correction:** "不需要那么specific吧，直接写 xxx - xxx 就行"

**Proposed AGENTS.md change:** none — apply the requested item - quantity - cost
format to this checklist; do not generalize a local formatting preference yet.

**Status:** pending

## 2026-10-08 — Preserve existing tables during targeted content updates

**Class:** `content-loss`

**What I did:** Replaced the full nutrient table with a five-row check and
changed meal/grocery presentation while implementing the nutrient update.

**Your correction:** "我的nutrient表怎么不见了，食物也按之前的格式来，别瞎改"

**Proposed AGENTS.md change:** "For targeted updates to an existing document,
preserve its tables, section coverage and presentation unless the user explicitly
requests a structural change. Scope a request to simplify one part to that part."

**Status:** pending

## 2026-10-09 — Cover composed backtest strategies before concluding

**Class:** `scope-truncation`

**What I did:** Reported only AI overall versus hold and technical rows, omitting
available momentum allocator and hybrid results from a broad comparison.

**Your correction:** "为什么会漏掉**动量配置器**？如果是skill的缺陷，把skill给优化掉"

**Proposed AGENTS.md change:** none — keep the scoped fix in quant-backtest-review:
establish comparison scope and report allocator, AI and hybrid attribution separately.
The user authorized the skill improvement; no AGENTS.md edit is proposed.

**Status:** pending


## 2026-10-09 — Search the confirmed hotel requirements before narrowing the shortlist

**Class:** `scope-truncation`

**What I did:** Rechecked a limited existing shortlist and stopped the expanded-budget search with incomplete Rayfont evidence, instead of browsing a dated, filtered station-area search and inspecting nearby candidates individually.

**Your correction:** "按需求search过，一个一个看"

**Proposed AGENTS.md change:** none — the travel-plan hotel workflow already requires search coverage and individual room-offer verification; correct execution and preserve the evidence without adding another rule.

**Status:** pending

## 2026-10-27 — Apply design-system reuse to standalone UI artifacts

**Class:** `design-bypass`

**What I did:** Generated a standalone HTML media comparison outside the repo
through Python/shell with independent CSS instead of reusing the current design
implementation. Existing interface guidance was sufficient but was not followed.

**Your correction:** "html没有复用到design system这是个问题，需要看看这个repo怎样优化才能保证每次生成的html / ui都会用design system"

**Proposed AGENTS.md change:** none at this stage — existing UI guidance already
requires reuse. Review `docs/design/ui-artifact-enforcement.md` for a minimal
builder, content/provenance checker and runtime-verified delivery integration.
Any later behavioral wording or hook change requires owner agreement; do not
claim arbitrary external writes are automatically covered.

**Status:** pending

## 2026-10-27 — Execute authorized work before claiming it is underway

**Class:** `claimed-not-executed`

**What I did:** Ended a turn saying I was now re-editing the video without
starting an editing tool or rendering a new artifact. The owner had to ask again.

**Your correction:** "你有在剪吗"

**Proposed AGENTS.md change:** none — the existing action, persistence and honest
progress requirements already cover this. Correct execution rather than add a
new rule. A new video was actually rendered and technically checked before this
entry was appended; subjective approval is still pending.

**Status:** pending

## 2026-10-28 — Ask for image style and archive generated images together

**Class:** `image-workflow`

**What I did:** Used the built-in image tool's default output directory initially, and the owner subsequently established a common repository destination and a style-selection workflow for future image requests.

**Your correction:** "记录这个规范，让ai记得以后generate image时都问要卡通3d还是抽象编辑，然后记录到 data/reference/photo-editing 里"

**Proposed AGENTS.md change:** "For image generation requests, read `data/reference/photo-editing/STYLE-PREFERENCES.md` if present. Ask whether the owner wants cartoon 3D or abstract editorial before generating when the style is unspecified. If the current request or ongoing task already specifies a style or requests both, proceed without asking again. Honor other explicit image instructions. Save all generated variants and revisions under `data/reference/photo-editing/<YYYY-MM-DD>-<subject>/`, preserve source inputs, and link the saved outputs when delivering."

**Status:** pending

The owner-requested workflow is recorded in the private preference file now. The proposed global routing rule has not been merged into AGENTS.md; it remains subject to the Correction Queue review process.

## 2026-11-05 — Social post copy and image text use Malaysian colloquial wording

**Class:** `post-conventions`

**What I did:** Wrote the DuitNow and double-11 captions in neutral Mandarin, then an over-stuffed slang version that the owner called forced.

**Your correction:** "也是没马来西亚口语的文案。以后每个post都需要有马来西亚slang的文案，图片也同理"

**Proposed AGENTS.md change:** "Write every social post's title, caption, pinned comment and in-image text in moderate Malaysian Chinese colloquial wording (e.g. scan, e-wallet, lah/leh used sparingly). Slang must not alter verified facts or disclaimers." Currently kept in agent memory only; not merged.

**Status:** pending

## 2026-11-05 — Pinned comments solicit the next post topic

**Class:** `post-conventions`

**What I did:** Used a policy-opinion A/B poll as the double-11 pinned comment,
instead of following the established DuitNow format asking what to explain next.

**Your correction:** "我的publish里面，定义的置顶评论问题永远是下一篇要看什么 而不是random问题"

**Proposed AGENTS.md change:** "Every social post's publish.txt pinned comment
must ask which topic readers want covered in the next post. Follow the established
next-topic A/B format when applicable; do not substitute an opinion poll or an
unrelated engagement question. Keep the pinned-comment draft in post.md aligned."

**Status:** pending

Corrected the current double-11 publish.txt and post.md. The proposed instruction
has not been merged into AGENTS.md.
