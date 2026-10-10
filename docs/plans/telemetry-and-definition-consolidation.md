# Plan: Telemetry-first logging and definition consolidation

> Status: phases 1–4 implemented; phase 5 decision reader deferred · 2026-09-29  
> Tracking: [ROADMAP §2](../ROADMAP.md#2-telemetry-first-logging-and-on-demand-calendar) and the Duplicate definitions item in [ROADMAP §4](../ROADMAP.md) track unfinished work; this file owns the sequence and gates.  
> Product decision: [DECISIONS §2](../DECISIONS.md#telemetry-first-logging-and-on-demand-calendar-2026-09-29) owns the logging and Calendar trade-off.

Implementation note: the active logging, scoring, Calendar, wealth contract, nutrition parity,
finance date, and command-discovery changes are in the worktree. The decision reader stays
deferred by Phase 5. The Public mirror threshold checklist remains open: the public scan found
historical threshold examples in `docs/DECISIONS.md`, which need a separate publication review.

## COROS supersession — 2026-10-02

The password-sync, staging and automatic daily-record instructions below are
historical and superseded by [the official MCP design](../design/coros-official-mcp.md).
Do not execute those COROS steps for current setup. The unknown-value and scoring
cutover remains in force.

## Goal and boundaries

An explicit COROS sync can create a useful daily record without a routine work report. Unrecorded manual fields remain unknown; an explicit `0` remains an observed zero. Weekly output shows health evidence and source coverage without inventing work, spend, or a complete `/100` score. A normal week produces no new timetable or Calendar publication. At the same time, each live rule, path, and report shape has one authoritative owner and a gate against consumer drift.

This is an implementation plan, with a semantic cutover and cross-layer gates. It does not rewrite old daily logs or reports, restart Zepp body sync, add scheduled jobs, introduce per-block work accounting, or absorb the separate `scripts/lib/paths.py` roadmap item. `data/` remains private; tests and generated contracts use fixtures and shapes only.

## Owner → consumer impact map

| Contract | Owner and current consumers | Change and compatibility gate |
|---|---|---|
| Daily record | `scripts/lib/schema.py::DailyLog` and `templates/daily.md`; `sync_coros.py` writes `data/fitness/*.yaml`, `patch_coros.py` updates daily files; weekly readers consume daily files | A successful fetch with a sleep, readiness, or training block, or at least one activity, creates a minimal valid daily file if absent. `coros_synced` preserves provenance after fitness YAML archival. An empty fetch still writes the fitness YAML as today but creates no daily file; auth failure writes neither. Preserve manual frontmatter and prose on rerun; old logs still parse. |
| Missing manual observations | Private `data/config/thresholds.yaml` currently supplies `logging_defaults`; `lib.defaults.resolve_all()` and `weekly_synthesis.py` consume them; weekly-review and coach-planner repeat the policy | Retire active baseline filling at the cutover. `None` is unknown; explicit `0` is evidence. Update template and skills. Do not add the interim equality guard between `logging_defaults.caffeine_cutoff` and `caffeine.cutoff_time` or retain the resolved-silent-week test. |
| Metrics, score, and events | `lib.metrics`, `lib.score`, `weekly_synthesis.py`, `report_gen.py`, engine events, weekly-review | Report observed totals with observed-day counts. Mark unavailable criteria and spend as unavailable; issue a full `/100` only when every required criterion has evidence. Keep raw-log breaker evaluation. No code currently reads engine JSONL; change emitted fields and update the `ARCHITECTURE.md` §9 logger row so `base_score_total` and old coverage fields cannot imply a complete score. Mark new reports with the policy cutover; leave historical reports unchanged. |
| Caffeine rule | `data/config/thresholds.yaml` owns the cutoff; `lib.score` currently hardcodes `14:00`; weekly-review copies the value | Pass `cfg.caffeine.cutoff_time` explicitly to scoring, score only recorded caffeine times, and remove numeric copies from the public skill. Test a non-default cutoff and no-observation state. |
| Body measurements | User-entered `body.*`; `lib.metrics` and weekly synthesis read it | Keep manual ownership. Surface a weight-only measurement and its date without inventing other body fields. |
| Schedule and Calendar | `data/protocol/standard_week.md` owns the standing schedule; `standard_week.yaml` and `*-calendar.yaml` are projections; coach-planner and `sync_calendar.py` consume them | A meaningful exception may create a short delta. Generate a sidecar and call explicit `make sync-calendar`/`make sync-protocol` only on a publication request. Require a target week before weekly publication and refresh the projection; update `ARCHITECTURE.md` §11 when this contract changes. |
| Live instructions | `AGENTS.md` directory/command contract; `Makefile` recipes; weekly-review and coach-planner skills | Fix wrong `daily/` paths, `make report` description, copied scoring values, and conflicting delta rules. Agent checks evidence and citations; code owns deterministic arithmetic. Scan public paths before marking the Public mirror threshold item complete. |
| Wealth report shape | `scripts/lib/wealth/report_models.py::WealthReport`; `web/lib/report.ts`, its fixture, and dashboard consume JSON | Generate committed TypeScript shape and schema version from Python serialization schema; retain fixture and runtime version check. No valuation logic moves to TypeScript. |
| Smaller repeated definitions | Nutrition schema in `repos/notes`; decision template/parser; finance validator/edit policy; Makefile targets | Add parity or focused shared readers only where needed, with missing-submodule, malformed-input, local-date, and command-discovery gates described below. |

## Implementation sequence

### Phase 1 — Fix live instructions and make telemetry records possible

1. In `.agents/skills/weekly-review/SKILL.md`, correct `data/daily/YYYY-MM-DD.md` references and use `make weekly DATE=...` for a requested ISO week. Remove copied rubric numbers, personal targets, caffeine time, spending baseline, sleep-stage range, and HRV ratio throughout the skill. Keep source-evidence and citation checks; deterministic arithmetic belongs to code. In `AGENTS.md`, describe `make report` as lint + logic check + synthesis that prepares an AI-authored report, matching the recipe. Link the public-skill cleanup to the Public mirror checklist, but complete that item only after scanning public skills, docs, and fixtures for private thresholds.
2. Put one plain create-if-missing-then-patch function in `patch_coros.py`, called by both its standalone `main()` and `sync_coros.py` after fetch; this also gives `make today` a reusable path to apply already fetched COROS data to an existing file without a network call. Create a minimal schema-valid daily file only when the fetch has a sleep, readiness, or training block, or at least one activity (`activities: []` alone does not qualify). Preserve the current empty-fetch write to `data/fitness/*.yaml` but create no daily file; auth failure writes neither. Avoid a second handwritten full template. Keep `make today` and `/daily-report` as optional manual entry points. A body measurement can be recorded without work.
3. In coach-planner, put one complete delta/protocol decision rule in `SKILL.md`; make `references/schedule-rules.md` point to it. Weight progression changes the standing protocol; a weekly delta records only a dated execution exception.

**Gate:** Correct paths and commands in active instructions; test the plain `patch_coros.py` function with fixtures for first sync, idempotent rerun, preserved manual content, and empty fetch, validating created files with `lib.daily_log.load()` (`make lint` reads only real `data/daily/`). For auth failure, stub `coros_api` in `sys.modules` before importing `sync_coros.py` and assert no writes. A public-path scan, rather than a single skill edit, gates the mirror checklist.

### Phase 2 — Cut over weekly meaning in one change

1. Remove `lib.defaults.resolve_all()` from the active weekly scoring path and change template, weekly-review, and coach-planner language to say blank optional fields are unknown. Preserve old-log parsing and archived reports. Keep breakers on raw observations. Do not add a transitional `logging_defaults` cutoff equality rule or a second baseline-filled scoring test that this phase would immediately delete.
2. Thread `cfg.caffeine.cutoff_time` through a required keyword-only scoring argument; remove the fixed `14:00` and update all callers/tests. Score caffeine only when a time was recorded. Audit every criterion in `lib.score`: missing means unavailable, explicit `0` can score zero, and a missing subjective judgment cannot silently become a zero-point judgment. Show measured components without rescaling the denominator; publish a full `/100` only with all required evidence.
3. In `lib.metrics`, `weekly_synthesis.py`, `report_gen.py`, and the weekly-review skill, separate recorded totals from complete-week claims. Show recorded deep work across N recorded days; N=0 means unavailable. Show unrecorded spend as unavailable, not `RM0`. Replace the six-field baseline coverage ratio and `~` markers with source counts: COROS days, body-measurement days, and explicitly recorded work days. Distinguish no daily file, no COROS data, and no optional work entry. Include weight-only body snapshots. No code currently reads `data/logs/engine-*.jsonl`; update the emitted `base_score_total`/coverage fields and the `ARCHITECTURE.md` §9 logger row, without a reader migration.
4. Put a cutover marker in new weekly reports and do not compare old and new scores as one uninterrupted rubric. Leave historical files untouched; retrospective rescore requires a separate version decision.

**Gate:** A telemetry-only week has health analysis, no invented work or spend, and no full score. Explicit zero work differs from missing work; a written work note is analyzed; a weight-only measurement appears. A non-default cutoff changes observed caffeine compliance and missing caffeine remains unavailable. Update `tests/test_defaults.py` to reject its current silent-week baseline expectation. Historical fixtures still parse; `make test` and `make lint` pass.

### Phase 3 — Publish Calendar on demand

1. A standard week creates no new timetable, delta, Calendar sidecar, or network action. A meaningful exception may create a short delta without a sidecar. Only an explicit publication request builds or refreshes the projection and runs `make sync-calendar WEEK=...` for that week; a standing-protocol publication uses the separate `make sync-protocol` command. Require `--week` in `sync_calendar.py` unless `--protocol` is set: deliberately drop its current fallback to the latest sidecar and update the Makefile help/usage text.
2. Remove routine Calendar steps from active skills. Update `ARCHITECTURE.md` §11's projection freshness rule at the same time as the behavior. Preserve the explicit week and protocol modes and the Google Calendar integration.

**Gate:** Standard and delta-only weeks make no Calendar file or network call. Week mode without `--week` fails before any sync; explicit publication produces the existing sidecar shape from the requested schedule and uses that week. Review the projection diff before sync.

### Phase 4 — Generate the wealth report contract (separate PR)

1. Make `WealthReport.report_schema_version` a `Literal[3] = 3` and export `WealthReport.model_json_schema(mode="serialization")` with a deterministic script such as `scripts/export_wealth_report_schema.py`. The schema must require the root version with `const: 3` and nested defaulted `WealthCfg` threshold fields that `model_dump(mode="json")` emits. Set serialization-default-required behavior on both models, or use an equivalent required-field design; root settings do not propagate to `$defs.WealthCfg` in the currently observed Pydantic 2.13.3 behavior.
2. Pin `json-schema-to-typescript` as a web development dependency with a lockfile change. Generate a committed `web/lib/report.gen.ts` with a provenance header and a check mode that fails on drift. Inspect the candidate generator's handling of required, nullable, and literal fields before adoption.
3. Make `web/lib/report.ts` import the generated type and version. Keep `tests/test_report_contract.py` and its JSON fixture as integration checks; validate the fixture with `WealthReport` in Python. Remove `web/lib/report.contract.ts` and its `Loose<>` workaround only after generation and fixture gates replace them. Preserve the runtime schema-version check.

**Gate:** A Python-only field change regenerates the TypeScript contract; stale generation fails. Tests cover nested nullable fields and a deliberate rename. `make test` and `cd web && npm run typecheck` pass. Generated files and fixtures contain no private holdings.

### Phase 5 — Consolidate smaller definitions when touched

1. Add exact micronutrient-field parity between `repos/notes/datasets/nutrition/schema.yaml` and `scripts/lib/nutrition/query.py` to `scripts/doctor.py`. Missing notes checkout is `[Status: Expected]`; present-but-drifted is `[Status: Error]`. Keep doctor standard-library-only, using the existing `.venv` for YAML parsing if available. Keep unit tests fixture-only and runtime adapter behavior independent of the submodule. Generate fields only if parity checks later show continuing drift.
2. Defer decision-reader refactoring until capture value is reassessed or a reader needs change. If triggered, extract only shared frontmatter parsing into `scripts/lib/decisions.py`; leave due filtering, calibration, and weekly counting with callers. Preserve current absent-frontmatter skip and malformed YAML/date error behavior unless a separate decision changes it. The available `data/` copy has no journal entries despite the April 2026 capture launch; DECISIONS §3's 12-week capture criterion should be reviewed before polishing readers.
3. Use `today_kl()` instead of `date.today()` in `finance_edit.py` write paths. Keep Pydantic record validation separate from editor allowlists; test web/CLI editable-field parity without exposing every model field.
4. Reconcile Makefile target comments, `make help`, and the short `AGENTS.md` command summary. Make `kb-check`, `kb-index`, `kb-eval`, `kb-graph`, `check-mermaid`, and `doctor-web` discoverable without maintaining three exhaustive command lists.

**Gate:** Focused tests for each touched item, plus `make test`, `make doctor`, and web typecheck at integration. Doctor tests cover absent notes and drifted schema; a clock test covers UTC/local-date disagreement. Decision tests retain fail-versus-skip semantics if its reader changes. Tests do not rewrite real finance or decision files.

## Risks and open decisions

- A COROS-created file changes `days_logged`: it no longer proves a human reviewed that day. Source counts must accompany it.
- Unknown criteria will make complete scores rarer. A normalized partial score would be a new rubric decision with a version boundary; this plan does not introduce one.
- A sidecar may be stale until requested. Rebuild from the requested schedule before publication and do not send an old `latest` file.
- The wealth generator is still a candidate: verify whether its output preserves required fields, nulls, and literal unions. If not, decide on an equivalent generator before replacing the handwritten interface.
- For web edit parity, prefer a focused test that inspects forms; use a checked-in manifest only if a second editor makes the test unwieldy.

## Completion

Phases 1–3 complete the telemetry and Calendar cutover; Phase 4 independently completes the Python → TypeScript report contract; Phase 5 items close only when individually touched and gated. At integration, review the diff and run the focused gates for each changed phase plus `make test`. Remove finished tasks from `ROADMAP.md`; retain the product trade-off in `DECISIONS.md` and the historical reports unchanged.
