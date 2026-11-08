# Correction Queue — archive

Entries moved out of `pending.md` after review, each with its outcome appended
(`merged` / `reworded` / `rejected`) and, for `merged`/`reworded`, which AGENTS.md
section changed.

## 2026-10-04 — Diagnose corrected outputs for valuable systemic improvements

**Class:** `correction-process`

**What I did:** The first HTML update matched the web's icons but retained a different visual treatment. Subsequent refinement aligned the presentation and exposed conflicting guidance in the skill entry.

**Your correction:** "如果我prompt了一次，ai出来的result不对，就思考看看是什么原因，是不是docs不够清晰，skills可以改进，值得做成script来稳定输出等的思考，如果价值非常高，就提这个意见让我同意去优化。"

**Proposed AGENTS.md change:** Add the "Learn from Corrected Outputs" section: fix the current result, diagnose the cause, and propose a minimal systemic improvement for approval when the expected value is substantial; do not generalize every correction.

**Outcome:** merged — the user approved the exact wording proposed in the conversation with "加上". Added AGENTS.md § "Learn from Corrected Outputs". Existing pending corrections remain unreviewed.

## 2026-09-29 — Travel photography advice became a shooting assignment

**Class:** `travel-photo-scope`

**What I did:** I turned an interest in spontaneous travel photos into city-by-city capture and note-taking prompts that felt too deliberate.

**Your correction:** "我打算看到什么新奇就拍什么就好，没有必要刻意。只是想要你提供下需要提前准备的拍照的风格 / 动作等"

**Proposed AGENTS.md change:** None — this is a trip-specific preference. Keep the current personal-direction rule that travel need not produce content, and answer future photography questions at the level Kelvin requests.

**Status at capture:** pending

**Outcome (2026-10-07):** rejected — no global instruction change. This is a scenario-specific preference; data/reference/personal-direction.md already allows unstructured travel without a public artifact. Retain the synthetic regression case. The owner approved this disposition during the correction-queue review.

## 2026-10-02 — Suggested extending custom sync before checking official integration

**Class:** `official-integration-first`

**What I did:** I recommended automating the existing COROS sync pipeline without first checking whether an official integration could remove the need to maintain it.

**Your correction:** "coros已有自己的mcp，不需要我现在这套，看看如何使用"

**Proposed AGENTS.md change:** Before proposing extensions to a custom external-service integration, check whether an official connector or MCP already covers the required capabilities. Prefer reducing maintenance when it meets the owner's needs; verify data coverage before retiring existing consumers.

**Status at capture:** pending

**Outcome (2026-10-07):** reworded — approved by the owner on 2026-10-07. Added AGENTS.md § "Key Conventions": "Before extending a custom external-service integration, check whether an official connector or MCP meets the required capabilities. Verify coverage and affected consumers before retiring the existing integration." The COROS integration is implemented in docs/design/coros-official-mcp.md and its consumers; that document still marks real live-data acceptance as pending. Archiving this correction does not certify that acceptance. The owner approved this disposition during the correction-queue review.

## 2026-10-04 — Visual reference was reduced to material effects

**Class:** `design-bypass`

**What I did:** I described the requested Apple-inspired travel UI mainly through Liquid Glass effects and initially changed generated pages before recognizing that the user wanted the reusable skill updated.

**Your correction:** "我是说帮我把travel plan skill里的ui修改，让他以后都生成apple的那种UI，玻璃液态的高级感"; "不只是盲目用liquid glass就行，二十需要做的有高级感，让人看着很舒服的UI"

**Proposed AGENTS.md change:** For a reusable visual-design request, identify the requested owner (skill/template versus generated artifact) before editing. Translate style references into coherent hierarchy, typography, spacing, alignment, and visual acceptance criteria; decorative effects alone do not establish design quality.

**Status at capture:** pending

**Outcome (2026-10-07):** rejected — no additional AGENTS.md rule. The requested reusable guidance is implemented in docs/design-system.md and .agents/skills/travel-plan/SKILL.md with its shared references/assets. Actual visual verification remains required for each change; existing guidance alone does not prove execution compliance. The owner approved this disposition during the correction-queue review.

## 2026-10-04 — Restrained styling flattened consequential information

**Class:** `design-bypass`

**What I did:** The travel HTML used similar neutral panels for critical pre-departure actions and ordinary context; the initial restyle also treated day warnings as generic notes.

**Your correction:** "太单调了，先确认，再出发。这种应该放个warning换个颜色等证明她重要"; "边优化边打开来看"; "尽量不要纯字段看着很boring，需要让人一看就懂的感觉"

**Proposed AGENTS.md change:** When refining a generated UI, preserve semantic emphasis with visible labels, colour and concrete actions. Compose information for a reader instead of mirroring raw fields. Open the actual outputs during iteration and verify both dense content and priority warnings before reporting completion.

**Status at capture:** pending

**Outcome (2026-10-07):** rejected — no additional AGENTS.md rule. Semantic emphasis and reader composition are implemented in docs/design-system.md, .agents/skills/travel-plan/references/share-html.md and assets/share.css. Actual desktop/mobile inspection remains required for visual changes. The owner approved this disposition during the correction-queue review.

## 2026-10-06 — Travel deliverables should be HTML only

**Class:** `content-loss`

**What I did:** I maintained the trip in Markdown and synchronized companion HTML, following the travel-plan skill's source-plan convention.

**Your correction:** "以后都不需要md file，直接改到html里就行。顺便帮我把所有的travel里的md删掉"

**Proposed AGENTS.md change:** Travel itineraries in `data/travel/` use HTML as the sole content owner and deliverable. Create and revise the HTML directly; do not create or require a companion Markdown file unless Kelvin explicitly requests one. Retain verification, route/checklist consistency, and HTML validation requirements.

**Status at capture:** pending

**Session outcome:** Applied the owner's standing HTML-only preference and deleted all three Markdown files under `data/travel/` as explicitly requested. Existing HTML files were retained. The instruction change remains queued for review; AGENTS.md was not edited.

**Follow-up correction (same entry, 2026-10-06):** "看看是不是也需要更新到skill注明这点，还是只是你笨" — Recording a preference without updating its explicitly conflicting skill leaves the next session with the same obsolete workflow. The owner authorized updating the travel-plan skill; updated its direct HTML ownership, references, legacy template routing and validation instructions. The proposed AGENTS.md wording remains pending and was not merged.

**Later owner decision (2026-10-06):** "如果md files是需要的那就恢复md files". The owner reversed HTML-only retirement after learning that the Markdown held unique version history, provenance and re-verification tasks. Restore recoverable source records, retain the current HTML itinerary, and reinstate the two-artifact skill contract. The proposed HTML-only AGENTS.md wording above is superseded; this queue entry remains pending for human review. Do not infer that display-format preferences authorize discarding unique records.

**Recovery outcome (2026-10-06):** Restored Chongqing–Jiuzhaigou–Chengdu v29 from a temporary original and reapplied the verified-in-session v30 city-route changes; restored Shanghai v4 from a recorded full Write plus matching successful Edits (the unmatched Edit was confirmed failed in its tool result). Changsha's original was not found in checked backups/history; its Markdown was reconstructed from the retained HTML and explicitly marked incomplete for version history, source index and rechecks. All existing HTML deliverables were preserved. Skill/reference guidance now retains the Markdown record and synchronizes HTML; future retirement requires preserving unique records first.

**Approved workflow (2026-10-06):** The owner accepted deterministic Markdown-to-HTML generation ("可以，改上"). Markdown now owns trip content and records; script generates the main itinerary. The owner also said "我把酒店的html删了，以后都不需要这个". Keep lodging in the main page and retire independent hotel outputs/links. The earlier HTML-only proposal remains superseded and pending; no AGENTS.md instruction was merged.

**Icon convention (2026-10-06):** "html里别用emoji，统一用svg icons应该是lucide". Convert visible source markers to bundled Lucide SVG in generated HTML and retain text labels; keep Markdown markers for semantic validation. Updated the travel skill and retained legacy pages accordingly.

**Outcome (2026-10-07):** rejected — the HTML-only proposal was superseded by the owner's later approved workflow. Markdown owns content and records; scripts generate the main HTML, lodging remains in that page, and visible icons use bundled Lucide SVG. Record-preservation guidance is in .agents/skills/travel-plan/SKILL.md. Retain the recovery account and its explicitly incomplete Changsha history; this archive does not establish that missing history was recovered. The owner approved this disposition during the correction-queue review.

## 2026-10-01 — Restaurant search was restricted to the hotel street

**Class:** `restaurant-radius`

**What I did:** I treated nearby dining as limited to the hotel street and prioritised convenience over worthwhile local restaurants reachable by a short trip.

**Your correction:** "不一定要酒店楼下，可以是搭地铁到隔壁春熙路还是哪里都行"

**Proposed AGENTS.md change:** None — trip-specific scope clarification. For this trip, include worthwhile dining options reachable by a short walk, metro ride, or taxi ride, while keeping departure-day timing explicit.

**Status at capture:** pending

**Outcome (2026-10-07):** rejected — no global instruction change; this was a trip-specific dining scope clarification. The owner approved archiving it. This entry was previously embedded inside the pending-file template comment and has been extracted into a normal archive entry. No claim is made here that current private dining choices were independently reverified.

## 2026-11-04 — Office and home UI bypassed the design system's controls

**Class:** `design-bypass`

**What I did:** Generated office / office-collaboration / home UI with native `<select>`, `<input>`, `<textarea>`, hand-styled `<button>` and page-level hex palettes. The design system only said "reuse Select"; it had no NEVER rule for native controls, no Input/Textarea primitive, and `make design-check` only checked colour contrast, so nothing failed.

**Your correction:** "目前web里，感觉很多样式都没有按规范来，例如select。看看是design system漏掉了还是什么个事情，在office和home都是有这个问题" / "主要先确保每次生成的ui都严格根据规范"

**Proposed `ui-design-rules` skill change (Components section):**
- "NEVER write a native `<select>`, `<input>`, `<textarea>` or hand-styled `<button>` in `web/`; use `Select`, `Input` / `Textarea` (`components/ui/input.tsx`) and `Button` / `buttonClass()` (`components/ui/button.tsx`)."
- "NEVER restyle `.design-select-*` internals from page CSS; only width on the trigger is allowed."
- "NEVER add a hex colour to page CSS or a Tailwind `[#hex]` class; add a token to `globals.css`."
- "A standalone HTML page (e.g. `home-design/apartment.html`) must import the design tokens or be rewritten as React."
- "Before saying done, `make design-check` must pass; it now includes the `design_rules_check.py` ratchet."

**Already applied (code, not behavior wording):** `Input` / `Textarea` primitives, `buttonClass()`, office + office-collaboration + home-preview buttons migrated to `Button`, and `scripts/design_rules_check.py` with `scripts/design_rules_baseline.json` (194 baselined violations, new ones fail `make design-check` and `make test`). Remaining baseline: native buttons in office (chips, toggles, rows), 100 hex values in `office.css`, `apartment.html` controls, finance table inputs.

**Status at capture:** pending

**Outcome (2026-11-04):** accepted — the NEVER rules landed in `.agents/skills/ui-design-rules/SKILL.md` (Components section and the done-checklist). A `PreToolUse` / `PostToolUse` hook on Write|Edit in `.claude/settings.json` (`scripts/design_hook.sh`) injects the rules before a `web/` edit and reports ratchet failures right after it. The owner approved this in-session ("都做"). `apartment.html` is still on the baseline; it needs a separate decision (token stylesheet vs React).

## 2026-11-06 — Shared 3D style must be realized in presentation artwork

**Class:** `design-bypass`

**What I did:** Extracted a shared artifact style with a rounded matte 3D default,
but described generated illustrations as optional and added no explicit artwork
acceptance criterion. Claimed PPT would inherit the shared style without a trial
deck. Inspection of the first dtc-e2e overview PPT and its v2 found 12 slides each,
zero embedded media and zero picture elements; the contact sheet shows flat text
and shapes. This confirms the output mismatch, but does not establish which
instructions the generating session read.

**Your correction:** "我生成的第一版ppt没有3d图片的？规范没立对吗"

**Proposed AGENTS.md change:** none pending owner agreement on the smallest
source-level clarification. Proposed shared-style wording: "When the shared 3D
style applies, include actual topic-relevant rounded matte 3D artwork on the cover
and representative mechanism/explanation pages. Text, tables and charts can remain
editable and flat; they do not replace the required artwork. A deck with zero 3D
artwork does not pass shared-style acceptance unless explicitly overridden by the
owner or a supplied template." The shared guide would require checking visible
artwork, and the PPT adapter would describe editable text plus image assets.
No instruction changes or PPT regeneration were applied in this review.

**Status at capture:** pending

**Outcome (2026-11-06):** accepted — the owner approved the proposed definition
with "做". Applied the requirement in `data/reference/artifact-style.md`,
`docs/artifact-design-guide.md` and `docs/presentation-guide.md`: actual 3D artwork
on the cover and main mechanism/explanation pages, combined with editable text and
diagrams; zero-artwork drafts fail the selected style unless explicitly overridden.
Production notes must identify artwork pages/assets, and rendered output must be
visually checked. Existing AGENTS.md routing already loads these owners, so no
additional AGENTS.md wording was needed. No PPT regeneration was requested or
performed as part of this specification update.
