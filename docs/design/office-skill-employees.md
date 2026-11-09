# Skill employees — Design-Lite

> **Superseded / frozen (2026-11-08):** the office direction is owned by [the attention radar](office-attention-radar.md). This view remains at `/office?scene=town`; bug fixes only.

[Status: OK] Implemented contract · 2026-11-01

## 1. Context

The owner requested one permanent employee per skill, in one continuous open
floor. A new Codex conversation must not create a new person. Session identity
remains necessary as execution evidence, but is no longer the scene identity.

## 2. Scope

Repository skills under `.agents/skills/<id>/SKILL.md` define the roster. Global
and plugin skills are not scanned. Names are readable skill IDs; appearance is
seeded by `skill:<id>`. Reload discovers roster changes. No migration of session
records, database, or private data is required.

Page pattern: existing office overview and selected-employee detail.
Reused components/assets: 3D room, people, expanding floor, Select, OfficeStatus,
DataState, task composer and session evidence.
New decisions: fixed roster, explicit task assignment, standby assignment label,
and compact hover/focus labels for a dense room.

## 4. Implementation and ownership

```text
.agents/skills/*/SKILL.md
  -> office-skills.ts [NEW server roster]
  -> office/page.tsx [MODIFIED server props]
  -> projectSkillRoom [NEW stable employee projection]
       <- observation v1 [UNCHANGED]
       <- execution.task.skill_id [ADDITIVE]
  -> scene, worker list, details [MODIFIED]
```

| Contract | Owner | Consumer | Compatibility / verification |
|---|---|---|---|
| Membership and skill path | Repository skill directory; `loadOfficeSkills` | Page and execution validator | Read-only; rejects paths outside the skill directory; catalog tests |
| Employee identity and merged work | `projectSkillRoom` | Scene, list, detail | `session_id` is the legacy scene key, now `skill:<id>`; real thread IDs remain in `sessions`; projection tests |
| Task assignment | `OfficeExecution.send` | Runtime instruction, snapshot, employee projection | Optional `skill_id`, old callers may omit; execution and API tests |
| Observed session meaning | Python monitor v1 | Existing parser and projection | Unchanged schema; fixture and contract tests |

Only explicit observed `role_ids` matching a catalog ID, or the selected owned
task's coordinator, links work to an employee. Arbitrary titles, nicknames,
prompts and subagent assignment strings do not establish a skill association.
The current observation adapter emits empty role IDs; ordinary desktop sessions
therefore remain unassigned. The UI exposes these records in a disclosure rather
than inventing people or activity. Owned team children remain outside the permanent employee roster. They are
inspectable in the task panel and the separate `/office/team` 3D view; that
view shows temporary runtime participants, not new permanent employees.

| Evidence | Employee display |
|---|---|
| No linked source | Standby; no claim that a process is running or idle |
| Multiple linked sources | One employee; all source IDs retained; priority waiting, working, error, unknown, idle, completed; newest evidence breaks ties |
| Runtime disconnect | Active coordinator becomes unknown; roster remains present |
| Observation failure | Prior active observations become unknown; roster remains present |
| Demo | Synthetic sessions explicitly assigned to roster entries; no execution or observation requests |
| Missing roster | Explicit roster error; no invented default employees |

Standby uses the idle animation category, with a separate assignment label and
no fabricated event timestamp. This does not modify observed lifecycle states.

## 5. API change

`POST /api/office/execution` accepts an optional field:

```json
{"action":"send","request_id":"example-request","text":"Prepare today's log","collaboration":"solo","skill_id":"daily-report"}
```

The server validates membership before starting work. It records
`task.skill_id`, includes it in the retry signature, and instructs the real turn
to read and follow the catalog-owned skill path. Unknown IDs return
`invalid_skill` (400). No browser-supplied file path is accepted. Omitted/null
IDs preserve generic execution for existing API callers. The UI requires an
explicit employee selection. Assignment is not proof of skill compliance.

## 7. Trade-offs

A repository-only roster is deterministic and inspectable; it excludes installed
plugins and global skills intentionally. Automatic inference from arbitrary
transcript text would misclassify mentions as execution, so explicit assignment
is used. A name editor and persistent task history are outside this change.
The owned task view remains memory-only and retains its existing restart behavior.

## 8. Verification and risks

Projection tests cover standby, stable identity after thread replacement,
multiple sessions, no additional employees from unassigned sessions, and runtime
disconnection. Catalog tests cover sorted membership and rejected external
symlinks. A fake App Server executes the actual send path to verify selected
skill instructions, invalid selection, idempotency and reset. Existing execution
and observation tests remain regression gates. These do not prove a live model
complied with the skill.

Desktop native Chrome visual review: demo displays all 18 employees in one room,
including ten standby employees; names and selection remain accessible. Dense
labels were compacted after visual review. Mobile and production verification
are recorded below when completed.

## 9. Open questions

No blocking decisions. Global/plugin skill membership and user-defined nicknames
would need a separate owner and persistence contract if requested.

## Acceptance record

[Status: OK] Contract review: membership, assignment and execution evidence have
separate owners; observation v1 and private-data boundaries are unchanged.
Daily-log, finance, global/plugin skills and collaboration-board contracts were
out of scope. The selected skill is part of request idempotency; no generic
session or child thread is silently promoted to an employee.

Native Chrome review used the isolated development server at
`http://127.0.0.1:3198/office`, dark appearance, desktop default zoom, and DevTools
390px and 320px responsive viewports (fit to window). The 18-person demo rendered
in one floor; Wealth Manager selection showed the stable skill ID and no linked
work. Compact labels were visually inspected. The narrow page header, controls
and detail/footer remained readable. In live mode, 24 unassigned observation
records remained separate from 18 employees. The employee dropdown selected
Wealth Manager successfully; no live model task was submitted. Screenshots were
reviewed in the tool conversation, not saved to the public repository.

[Status: Warning] No automated Playwright run or production-build visual review
was available in this session; the browser extension connection was absent, so
native Chrome controls were used. Full theme/material and enlarged-text
acceptance are not claimed. Model compliance with the assigned skill remains
unverified; protocol tests use a synthetic App Server.

Verification: `npm --prefix web run typecheck` passed; from `web/`,
`node --test tests/office*.cjs` passed all 35 tests. `git diff --check` passed.
