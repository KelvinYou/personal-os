# UI artifact reuse — proposed enforcement

[Status: Warning] Design-Lite · proposed 2026-10-27 · builder/checker implemented 2026-11-08; hook integration not built

## Implementation status (2026-11-08)

| Piece | State |
|---|---|
| `templates/ui/standalone.html` + `standalone.css` | Built. Shell + layout only; tokens come from `web/app/design-controls.css`. The template CSS paints `body`, because standalone pages have no `globals.css` |
| `scripts/ui_build.py`, `scripts/ui_check.py`, `scripts/lib/ui_artifact.py` | Built. `make ui-build` / `make ui-check` |
| `tests/test_ui_artifacts.py` | Built. Covers every §5 row except hook/Stop behavior |
| Proof on the real incident | The original olive page was overwritten in place, so `tests/fixtures/ui/independent-style.html` is a labelled reconstruction (fails `UI-ASSET-MISSING`). The four corrected 10-27 pages under the owner's media folder also fail: each claims reuse in a comment with sha `6dd0905e…`, while the inline CSS is an untagged copy that differs from the current upstream (`design-controls.css` is untracked, so that digest cannot be traced to any version) |
| `.codex/hooks/ui-delivery.py`, Stop integration | Not built. Needs a runtime trial in the actual client first (§5) |
| Routing | `ui-design-rules` skill, `docs/dev-sop.md` UI section, AGENTS.md Common Commands |

## 1. Context

A standalone media comparison page was generated through a Python/shell command
outside the repository with independent olive CSS. It omitted the existing
interface implementation despite the current guide and SOP requiring reuse.
The owner requested a repository-level prevention mechanism. This is an execution
failure plus an unenforced delivery contract, not evidence that the design guide
needs another list of aesthetic principles.

## 2. Scope and evidence

| Owner / contract | Current consumer or enforcement | Finding |
|---|---|---|
| `docs/design-system.md` | `docs/dev-sop.md`, `docs/design/interface-patterns.md` | OK: reuse, native HTML controls, local-copy provenance and visual acceptance already specified |
| `web/app/design-controls.css` | `web/app/layout.tsx`, React controls | OK: reusable live asset; standalone export has no generic builder |
| `.codex/hooks.json` | `.codex/hooks/post-edit-enforce.sh` | Warning: post-tool matcher omits Bash; no Stop delivery check |
| `.codex/hooks/*.sh` | `.claude/scripts/enforce` and `.claude/hooks/*` | Critical: referenced implementation absent locally; post-edit bridge silently exits 0 |
| Travel HTML builder | `scripts/travel_build.py`, travel skill assets | Existing domain owner; preserve itinerary-specific behavior rather than introducing a competing travel renderer |
| Repo-external artifacts | No registered build/check entry point found | Warning: Git-only discovery misses outputs elsewhere on disk |

Read-only reproduction: the post-edit bridge was invoked with a synthetic Write
payload. It returned exit 0 with no output because `.claude/scripts` is absent.
This proves that bridge is a no-op here; it does **not** prove which hooks the
current application loaded or whether their definitions were trusted.

## 3. Proposed architecture

```text
Existing design guide + design-controls.css [UNCHANGED owners]
    → standalone HTML builder + shell [NEW]
    → explicit artifact manifest (absolute output path) [NEW]
    → artifact checker (content and upstream digest) [NEW]
    → focused visual/interaction evidence [EXISTING requirement]
    → delivery acceptance [NEW integration]

React pages [EXISTING]
    → existing shared components/CSS [UNCHANGED]
    → project build + targeted browser evidence [EXISTING]
    → same delivery manifest/check interface [NEW integration]
```

Make correct reuse the default construction path and check the delivered output.
Hooks assist discovery and turn continuation; they are not a filesystem security
boundary or proof of aesthetic quality.

## 4. Proposed changes

| Proposed path | Change and reason |
|---|---|
| `templates/ui/standalone.html` | Small shell: metadata, main/skip destination, theme support and content slots. No travel or media business logic. |
| `scripts/ui_build.py` | Embed the actual upstream CSS with a SHA-256 digest and provenance. Accept explicit `--output` outside the repository; no broad home-directory scanning. Escape text slots, distinguish trusted HTML fragments. |
| `scripts/ui_check.py` | Check the resolved artifact, embedded CSS bytes/digest, stylesheet order and static delivery dependencies. Missing or stale style content fails; a comment claiming reuse alone cannot pass. |
| `reports/ui/` | Synthetic repo fixtures/evidence only. Private output manifests and screenshots stay alongside their private artifact, not in public reports. |
| `.codex/hooks/ui-delivery.py` | Independent local implementation, not the missing Claude scaffold. Read explicit task manifests; no UI work means no action. Handle the documented hook schema and bounded continuation. |
| `.codex/hooks.json` | After owner agreement and a real runtime trial, connect relevant tool events and Stop. Preserve unrelated existing hooks; separately report broken legacy bridges. |
| `Makefile`, `docs/dev-sop.md` | Route generation and delivery to explicit build/check commands after agreement. Preserve existing diagram and unrelated procedures. |
| `tests/test_ui_artifacts.py` | Exercise the original bypass and content drift, not only generated snapshots. |

Proposed interface (not commands available today):

```text
python3 scripts/ui_build.py --input SPEC.json --output /absolute/path/index.html
python3 scripts/ui_check.py --manifest /absolute/path/ui-artifact.json
```

A manifest records schema version, host (`standalone` or `react`), artifact path,
page pattern, actual reused assets/digests, intentional differences, and evidence
status. The checker resolves and reads paths; it never executes manifest commands
or accepts self-declared `passed` flags as test evidence. Bind evidence to artifact
and asset digests so an edit invalidates earlier acceptance.

React acceptance must check actual consumers/build output rather than demand an
embedded stylesheet or a particular component on every page. Domain colors,
charts, video pixels and literal CSS values are not automatically violations.
Static override detection is advisory; browser computed styles and visual review
are needed for cascade or layout departures. Explicit alternate product design
systems remain supported when the user requested them and provenance is recorded.

## 5. Failure behavior, rollout and verification

| Scenario | Required result |
|---|---|
| Original independent-style fixture | Fail reuse check before delivery |
| Correct generated standalone page | Pass content/provenance check; visual status still separate |
| Marker copied but CSS absent or modified | Fail; metadata cannot substitute for style content |
| Upstream asset changed | Fail stale digest; rebuild and replay affected scenarios |
| Shell writes external HTML | Registered explicit output is checked, independent of Git status |
| No manifest or unregistered external output | Not covered automatically; report this limitation instead of claiming universal enforcement |
| Hook not loaded/trusted | CLI check still works; report runtime enforcement unavailable |
| Broken checker or missing asset | Fail check with a clear diagnostic; no silent success |
| No UI change | No UI check or continuation |
| Repeated Stop failure | Bounded continuation; report blocker rather than loop indefinitely |

First ship builder/checker/fixtures, then validate the hook using a synthetic
shell-generated external file in the actual client. Integrate delivery routing
only after that proof. Do not remove or repair unrelated scaffold hooks as part
of this change. Preserve user work already present in the design guide, dashboard
and hook configuration.

Regression scope: standalone light/dark, 320px/390px/desktop, enlarged text,
keyboard controls and offline relative assets; React shared-control regression
suite; existing travel renderer tests if shared export assets change. CSS inclusion
is not a screenshot test or a guarantee that every UI looks good.

## 6. Trade-offs and limits

More prose is cheap but would not catch this incident. A new skill can route work
but is also bypassable; avoid making skill discovery the only guard. A builder
plus explicit artifact checker catches concrete omissions with little runtime
cost. A universal scanner cannot reliably infer every output path from arbitrary
shell programs; strict filesystem enforcement would require a different execution
boundary and is outside this proposal.

The achievable guarantee is: **every registered artifact delivered through this
workflow must pass the reuse check**. Arbitrary unregistered writes or another
client that does not execute the workflow remain outside that guarantee.

## 7. Review decision

Proceed with the minimal builder/checker and focused fixtures first, followed by
runtime-tested delivery-hook integration? Recommended: yes. Agent behavior and
hook changes remain pending owner agreement under AGENTS.md's correction protocol.
No AGENTS.md changes, hook changes or enforcement code were applied in this review.

Official runtime contract checked through [OpenAI Docs — Hooks](https://learn.chatgpt.com/docs/hooks):
project hook trust, canonical tool aliases, PostToolUse feedback after side effects,
and Stop continuation semantics. These support the integration design; they do
not establish the active client's actual coverage.
