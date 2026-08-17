---
name: repo-orchestrator
description: >
  Coordinate multi-repository development in Personal-OS, especially changes that
  span the main repo, private data, ai-stock-analysis, portfolio-website, market
  data, or agent skills. Use this skill whenever the user asks to sync or bump
  submodules, prepare a release or integration check, review whether a change is
  safe to commit, finish work across repositories, inspect dirty submodule state,
  or verify the correct order of tests and parent-pointer updates—even when they
  do not explicitly say "orchestrate" or "release". This skill prepares and
  validates the integration; explicit commit or push requests hand off to
  git-commit after the checks pass.
allowed-tools: Bash, Read, Glob, Grep
---

# Repo Orchestrator

Personal-OS is a multi-repository system, not just the root checkout. A parent
commit records submodule pointers, while the real implementation may live in
`data/`, `repos/ai-stock-analysis/`, or `repos/portfolio-website/`. The purpose
of this skill is to make that integration state visible and verifiable before
any irreversible Git operation.

## Ownership boundary

This skill owns integration preflight, dependency mapping, verification planning,
and handoff. It does not own domain analysis, timetable generation, or generic
single-repository commit writing.

- Use `wealth-manager`, `learning-agent`, or `profile-optimizer` for domain
  analysis after the repository state is understood.
- Use `tdd`, `diagnose`, or `improve-codebase-architecture` for implementation
  work when those skills are applicable.
- When the user explicitly asks to commit, hand the clean, verified change set
  to `git-commit`; do not silently stage, commit, amend, or push here.

## Operating contract

1. Default to read-only inspection. Do not run `git add`, `git commit`, `git
   reset`, `git checkout`, `git clean`, `git push`, or `git submodule update`
   unless the user explicitly authorizes that exact state change.
2. Preserve user work. A dirty submodule is evidence to report, not a reason to
   reset, stash, discard, or overwrite it.
3. Do not fetch from the network or ask for credentials as part of a normal
   preflight. Report unavailable remotes or missing private data as a boundary,
   then continue with checks that can run locally.
4. Read `AGENTS.md` and `ARCHITECTURE.md` before judging a cross-layer change.
   Treat them as the repository contract, while flagging contradictions in
   plans, README files, or skill references.
5. Use the project's status vocabulary: `[Status: OK]`, `[Status: Warning]`,
   `[Status: Critical]`, and `[Status: Expected]` for an intentional boundary
   such as an unavailable private `data` submodule.
6. Never report a parent pointer as clean merely because the gitlink changed.
   Inspect the child worktree separately and distinguish committed child HEAD
   from uncommitted files.

## When to trigger

Trigger for requests such as:

- "帮我检查这次改动能不能提交"
- "同步 / bump submodule"
- "我在两个 repo 都改了，帮我收尾"
- "prepare the release / integration check"
- "检查 parent pointer 是否正确"
- "run a preflight before commit"
- "why is the main repo dirty after the submodule change?"

Do not trigger for an isolated code edit, a normal one-repo commit, or a
Personal-OS timetable request unless the user also asks for repository
coordination.

## Workflow

### 1. Discover the repository graph

Run the smallest set of read-only checks needed to establish the state:

```bash
git status --short --branch
git submodule status
git config --file .gitmodules --get-regexp 'path|url'
git log --oneline -8
```

For every initialized submodule, run its own status and recent-history checks:

```bash
git -C <submodule> status --short --branch
git -C <submodule> log --oneline -5
```

If a submodule is absent or uninitialized, report whether that is expected:

- `data/` is private and may be unavailable in a public-only checkout;
  classify this as `[Status: Expected]` for checks that do not require private
  data, and `[Status: Warning]` or `[Status: Critical]` only when the requested
  operation needs it.
- `market/` is public repository data and its absence is a real repository
  error, not an authorization exception.
- A missing public `repos/` submodule blocks an integration check that depends
  on it.

### 2. Build a change map

For each dirty or recently changed repository, record:

| Field | Meaning |
|---|---|
| Repo | root, data, ai-stock-analysis, or portfolio-website |
| Recorded pointer | gitlink recorded by the parent, if applicable |
| Actual HEAD | child commit currently checked out |
| Worktree | clean, modified, untracked, or unavailable |
| Changed areas | data, pipeline, web, skills, docs, config, tests |
| Next gate | the narrowest relevant validation command |

A parent pointer update is only ready when the child worktree changes are
committed in the child repository. If the child is dirty, show the files and
state that the parent can only record the current commit, not the uncommitted
files.

Use recent commit subjects and path-level diffs to infer intent; do not rely on
the submodule bump message alone. A data refresh, a pipeline change, and a web
redesign have different verification needs even if all end as one gitlink.

### 3. Check Personal-OS contracts

Before proposing a parent bump, check the relevant invariants:

- `AGENTS.md` is the single collaboration-contract owner; `CLAUDE.md` should
  not become a competing copy.
- `ARCHITECTURE.md` and `docs/plan*.md` agree on implemented versus proposed
  layers. Flag stale status claims instead of silently editing historical docs.
- `templates/daily.md`, `scripts/lib/schema.py`, and migration/lint logic move
  together for daily-log schema changes.
- `config/thresholds.yaml` owns thresholds; do not accept new magic numbers in
  scripts or skills.
- Python owns wealth valuation and report mathematics. TypeScript consumes the
  report contract and must not reimplement the calculation.
- Public `market/` facts and public submodules must not receive private
  holdings, logs, balances, or profile data.
- `.agents/skills/` is the source tree for project skills; `.claude/skills/`
  links and `skills-lock.json` must remain consistent when skill packages move.
- A missing field is not automatically zero, failure, or permission to invent a
  value. Check raw-vs-derived data and coverage semantics when logs or market
  observations change.

If a change crosses Python, TypeScript, YAML, Markdown, and a submodule, list
the source-of-truth chain, impacted consumers, fixtures, and required tests.

### 4. Select verification gates

Prefer narrow, local gates based on changed paths. Do not run a costly or
networked pipeline merely because a repository exists.

#### Root Personal-OS

- General root/config/scripts change: `make doctor` and `make test`.
- Daily schema, thresholds, logging, archive, or migration change: add
  `make lint` and the focused Python tests; use `make check` when logs are
  available.
- Wealth/report/contract change: add the wealth tests and web typecheck; verify
  the JSON/report fixture boundary and exit-code behavior.
- Calendar or external side-effect change: inspect dry-run behavior, timezone,
  idempotency, scope handling, and whether a rerun affects only the intended
  series or delta.
- Skill/docs change: check referenced paths, frontmatter, trigger ownership,
  privacy placeholders, and stale terminology.

`make report` is a synthesis step, not a substitute for `make test`; report
which gates were actually run and which were skipped.

#### `repos/ai-stock-analysis`

Read that repository's own `AGENTS.md`, README, package metadata, and test
commands before running them. Classify changes as:

- data refresh: freshness, schema, dated evidence, and watchlist scope;
- pipeline/backtest/integrity: unit tests plus the narrow backtest or invariant
  checks documented by the repository;
- web/UI: typecheck, lint/build, and browser QA when requested;
- mixed: run the union of the relevant gates and call out expensive checks not
  run.

Never treat a fresh JSON file as proof that the analysis is valid; verify its
`as_of`/source metadata and avoid fabricating missing layers.

#### `repos/portfolio-website`

Read its package scripts and local instructions. For code or UI changes, use
the documented typecheck/lint/build gates. For resume, localization, or visual
changes, call out the need for browser/mobile/PDF inspection when those tools
are available; a passing typecheck is not visual proof.

### 5. Produce the integration report

Always return a compact report in this order:

```markdown
## Integration preflight
[Status: OK/Warning/Critical/Expected] one-line conclusion

### Repository map
| Repo | Recorded pointer | Actual HEAD | Worktree | Impact |
|---|---|---|---|---|

### Contract checks
- [Status: OK] ...
- [Status: Warning] ...

### Verification
- `command` — passed / failed / skipped (reason)

### Blockers
- none, or exact file/repo and why it blocks

### Safe next actions
1. ...
2. ...

### Handoff
If the user asked to commit: `git-commit` can now stage the listed files.
Otherwise: stop after the report and wait for authorization.
```

The report must distinguish facts from recommendations. Include exact paths and
commands, but do not hide a dirty worktree behind a generic "ready to commit".

### 6. Handoff and stopping rules

Hand off to `git-commit` only when:

- the user explicitly requested a commit;
- all required child changes are committed, or the user knowingly accepts a
  pointer-only state;
- no Critical contract or verification blocker remains;
- the report names the exact files/repositories in scope.

If the user only asked for a preflight, stop after the report. If a submodule is
dirty, unavailable, or ahead of its recorded pointer, explain the smallest safe
next step; do not repair it silently.

## Common failure patterns

- **"The parent is clean"** while a child has untracked files: inspect every
  submodule independently.
- **Bumping before validating the child**: validate the child commit first, then
  record the gitlink in the parent.
- **Running the full pipeline for a data-only refresh**: use freshness/schema
  checks first and reserve expensive analysis for code/pipeline changes.
- **Calling `make report` a full CI gate**: it does not replace `make test`.
- **Fixing historical documents in place**: flag stale docs and preserve audit
  records unless the user asks for a documentation update.
- **Committing a public/private boundary violation**: stop and identify the
  offending path before any staging or pointer update.

## Completion criteria

The skill has done its job when the user can answer, from one report:

1. Which repositories changed and whether each worktree is clean.
2. Which parent pointers are recorded versus pending.
3. Which contracts and consumers are affected.
4. Which verification gates passed, failed, or were intentionally skipped.
5. What exact next action is safe, and whether `git-commit` may take over.
