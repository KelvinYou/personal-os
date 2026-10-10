# Correction Queue — archive

Entries moved out of `pending.md` after review, each with its outcome appended
(`merged` / `reworded` / `rejected`) and, for `merged`/`reworded`, which AGENTS.md
section changed.

## 2026-10-04 — Diagnose corrected outputs for valuable systemic improvements

**What I did:** The first HTML update matched the web's icons but retained a different visual treatment. Subsequent refinement aligned the presentation and exposed conflicting guidance in the skill entry.

**Your correction:** "如果我prompt了一次，ai出来的result不对，就思考看看是什么原因，是不是docs不够清晰，skills可以改进，值得做成script来稳定输出等的思考，如果价值非常高，就提这个意见让我同意去优化。"

**Proposed AGENTS.md change:** Add the "Learn from Corrected Outputs" section: fix the current result, diagnose the cause, and propose a minimal systemic improvement for approval when the expected value is substantial; do not generalize every correction.

**Outcome:** merged — the user approved the exact wording proposed in the conversation with "加上". Added AGENTS.md § "Learn from Corrected Outputs". Existing pending corrections remain unreviewed.

## 2026-09-29 — Travel photography advice became a shooting assignment

**What I did:** I turned an interest in spontaneous travel photos into city-by-city capture and note-taking prompts that felt too deliberate.

**Your correction:** "我打算看到什么新奇就拍什么就好，没有必要刻意。只是想要你提供下需要提前准备的拍照的风格 / 动作等"

**Proposed AGENTS.md change:** None — this is a trip-specific preference. Keep the current personal-direction rule that travel need not produce content, and answer future photography questions at the level Kelvin requests.

**Status at capture:** pending

**Outcome (2026-10-07):** rejected — no global instruction change. This is a scenario-specific preference; data/reference/personal-direction.md already allows unstructured travel without a public artifact. Retain the synthetic regression case. The owner approved this disposition during the correction-queue review.

## 2026-10-02 — Suggested extending custom sync before checking official integration

**What I did:** I recommended automating the existing COROS sync pipeline without first checking whether an official integration could remove the need to maintain it.

**Your correction:** "coros已有自己的mcp，不需要我现在这套，看看如何使用"

**Proposed AGENTS.md change:** Before proposing extensions to a custom external-service integration, check whether an official connector or MCP already covers the required capabilities. Prefer reducing maintenance when it meets the owner's needs; verify data coverage before retiring existing consumers.

**Status at capture:** pending

**Outcome (2026-10-07):** reworded — approved by the owner on 2026-10-07. Added AGENTS.md § "Key Conventions": "Before extending a custom external-service integration, check whether an official connector or MCP meets the required capabilities. Verify coverage and affected consumers before retiring the existing integration." The COROS integration is implemented in docs/design/coros-official-mcp.md and its consumers; that document still marks real live-data acceptance as pending. Archiving this correction does not certify that acceptance. The owner approved this disposition during the correction-queue review.

## 2026-10-04 — Visual reference was reduced to material effects

**What I did:** I described the requested Apple-inspired travel UI mainly through Liquid Glass effects and initially changed generated pages before recognizing that the user wanted the reusable skill updated.

**Your correction:** "我是说帮我把travel plan skill里的ui修改，让他以后都生成apple的那种UI，玻璃液态的高级感"; "不只是盲目用liquid glass就行，二十需要做的有高级感，让人看着很舒服的UI"

**Proposed AGENTS.md change:** For a reusable visual-design request, identify the requested owner (skill/template versus generated artifact) before editing. Translate style references into coherent hierarchy, typography, spacing, alignment, and visual acceptance criteria; decorative effects alone do not establish design quality.

**Status at capture:** pending

**Outcome (2026-10-07):** rejected — no additional AGENTS.md rule. The requested reusable guidance is implemented in docs/design-system.md and .agents/skills/travel-plan/SKILL.md with its shared references/assets. Actual visual verification remains required for each change; existing guidance alone does not prove execution compliance. The owner approved this disposition during the correction-queue review.

## 2026-10-04 — Restrained styling flattened consequential information

**What I did:** The travel HTML used similar neutral panels for critical pre-departure actions and ordinary context; the initial restyle also treated day warnings as generic notes.

**Your correction:** "太单调了，先确认，再出发。这种应该放个warning换个颜色等证明她重要"; "边优化边打开来看"; "尽量不要纯字段看着很boring，需要让人一看就懂的感觉"

**Proposed AGENTS.md change:** When refining a generated UI, preserve semantic emphasis with visible labels, colour and concrete actions. Compose information for a reader instead of mirroring raw fields. Open the actual outputs during iteration and verify both dense content and priority warnings before reporting completion.

**Status at capture:** pending

**Outcome (2026-10-07):** rejected — no additional AGENTS.md rule. Semantic emphasis and reader composition are implemented in docs/design-system.md, .agents/skills/travel-plan/references/share-html.md and assets/share.css. Actual desktop/mobile inspection remains required for visual changes. The owner approved this disposition during the correction-queue review.

## 2026-10-06 — Travel deliverables should be HTML only

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

**What I did:** I treated nearby dining as limited to the hotel street and prioritised convenience over worthwhile local restaurants reachable by a short trip.

**Your correction:** "不一定要酒店楼下，可以是搭地铁到隔壁春熙路还是哪里都行"

**Proposed AGENTS.md change:** None — trip-specific scope clarification. For this trip, include worthwhile dining options reachable by a short walk, metro ride, or taxi ride, while keeping departure-day timing explicit.

**Status at capture:** pending

**Outcome (2026-10-07):** rejected — no global instruction change; this was a trip-specific dining scope clarification. The owner approved archiving it. This entry was previously embedded inside the pending-file template comment and has been extracted into a normal archive entry. No claim is made here that current private dining choices were independently reverified.
