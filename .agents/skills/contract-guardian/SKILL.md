---
name: contract-guardian
description: >
  Review semantic contracts in Personal-OS whenever a change touches schemas,
  templates, scripts/lib, thresholds, wealth reports, Python/TypeScript
  boundaries, public/private data paths, agent skills, or architecture and plan
  documents. Use this skill whenever the user asks whether a cross-layer change
  is complete, whether a schema or field rename is safe, whether docs and code
  agree, whether data may be public, or whether a report/skill contract needs
  tests or migration—even if they do not say "contract" or "schema". Build an
  owner → consumer → migration/test impact map, classify drift with the
  project's Status vocabulary, and block unsafe semantic changes. This skill
  reviews contracts; repo-orchestrator owns multi-repo release order and
  git-commit owns explicit staging and commits.
allowed-tools: Bash, Read, Glob, Grep
---

# Contract Guardian

Personal-OS deliberately stores human-readable Markdown/YAML, deterministic
Python metrics, AI narrative, and public/private repositories side by side. A
change can pass a local typecheck while silently changing the meaning of a
score, breaking an old log, duplicating a calculation in TypeScript, or leaking
private facts into a public catalog. This skill makes those semantic contracts
explicit before the change is accepted.

## Ownership boundary

This skill owns contract discovery, drift analysis, migration/test impact, and
the read-only review report. It does not own repository release sequencing or
domain recommendations.

- Use `repo-orchestrator` when the main question is submodule state, child
  commits, parent gitlinks, or release order.
- Use `tdd` when implementing a missing guard or regression test.
- Use `diagnose` for a reproduced runtime bug or performance regression.
- Use `improve-codebase-architecture` for a larger ownership or dependency
  refactor.
- Use `git-commit` only after the user explicitly requests a commit and the
  contract review has no unresolved Critical blocker.

## Operating contract

1. Default to read-only. Do not edit, stage, commit, push, migrate with apply,
   checkout, reset, clean, stash, fetch, initialize private data, or rewrite a
   historical audit document unless the user explicitly authorizes that action.
2. Inspect the actual diff before judging completeness. A file mentioned in a
   prompt but absent from `git diff` is not a pending change; report that fact
   instead of treating history as the user's change set.
3. Read `AGENTS.md` and `ARCHITECTURE.md` first. Then read only the relevant
   plan, schema, tests, skills, and consumers. Preserve historical documents;
   flag stale claims rather than silently rewriting them.
4. Treat missing, null, stale, unpriced, and zero as different states unless a
   contract explicitly says otherwise. Never recommend filling a gap with an
   invented personal baseline or market value.
5. Use `[Status: OK]`, `[Status: Warning]`, `[Status: Critical]`, and
   `[Status: Expected]`. An unavailable private `data/` checkout is Expected
   only when the requested check does not need private facts.
6. A contract is not complete because a typecheck passes. Check runtime
   consumers, fixtures, migrations, provenance, and privacy boundaries too.

## When to trigger

Trigger for requests such as:

- "Will this schema change break old logs?"
- "Help me check the Python/TS report contract"
- "What needs to change for this field rename?"
- "Can this market data go in the public repo?"
- "Which one is right: architecture, plan, or code?"
- "Help me review whether this skill leaks a personal baseline"
- "Did this change miss a migration / fixture / test?"
- "Is this YAML actually consumed by the system?"

Do not trigger for an isolated prose edit, a pure timetable request, or a
normal one-repo commit where no schema, ownership, privacy, or cross-layer
meaning changes.

## Contract classes

Review only the classes touched by the change, but always state which ones were
out of scope.

### A. Schema and data lifecycle

For daily logs, decisions, finance inputs, or reports, identify:

| Question | Evidence to locate |
|---|---|
| Who defines the shape? | template, Pydantic model, JSON schema, or fixture |
| Who writes it? | script, skill, user, or submodule owner |
| Who reads it? | aggregators, checkers, web bridge, skills, reports |
| Does an old record still load? | migration, compatibility rule, dry-run output |
| What does missing mean? | null, unavailable, default, low coverage, or error |

For a breaking field removal or rename, require a complete chain:

```text
source schema → typed model → migration/compatibility → every consumer
→ fixtures/golden outputs → focused tests → lint or runtime gate
```

Do not accept `extra="allow"`, a wider TypeScript type, or a default value as
a substitute for deciding the contract. Those can hide drift.

### B. Cross-language report contract

When Python produces JSON consumed by TypeScript:

- identify the canonical Python builder and keep all valuation/math in Python;
- inspect the report schema/version, JSON fixture, recursive contract tests,
  TypeScript interface, and web consumers together;
- check key presence, nested shape, numeric/boolean/null semantics, and exit
  code behavior, not just compile success;
- require a schema-version decision for intentional breaking changes;
- reject a TS-side reimplementation of Python calculations, because it creates
  two owners and allows silent divergence.

For Personal-OS wealth specifically, verify that `allocation.incomplete`,
unpriced holdings, FX age, maturity versus renewal rate, and tracked-assets
scope remain explicit. Do not silently turn an incomplete total into net worth.

### C. Configuration and evidence provenance

Separate executable configuration from external facts:

- `config/thresholds.yaml` owns engine thresholds and breaker rules;
- `config/wealth_rules.yaml` contains public regulatory facts only, with
  `source` and `verified_at`, and must have an actual consumer if its file
  header promises freshness behavior;
- `market/` contains public observed facts, not personal holdings or policy;
- a stale, missing, or unverified observation should lower confidence or block
  a conclusion according to its contract, not be treated as current truth.

When a YAML file changes, confirm both static shape and application-level use.
Finding `source` metadata is not proof that freshness is enforced.

### D. Public/private boundary

Treat `data/` as private and `market/` plus public submodules as public. Inspect
the changed paths and references for:

- balances, holdings, account identifiers, personal policy, user profile,
  private targets, or real transaction facts in tracked public files;
- real private values copied into fixtures, README examples, screenshots,
  share cards, generated JSON, logs, or skill prose;
- public skills containing personal baselines instead of placeholders resolved
  from private data at runtime;
- a public child repository reading or writing `data/finance/`.

Do not use value matching alone: a public legal cap can equal a private cash
flow number. Use path, context, and an explicit allowlist when classifying a
possible leak.

### E. Agent skill and documentation contract

When `.agents/skills/**`, `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, or a plan
changes:

- check frontmatter, trigger description, ownership boundaries, referenced
  paths, and whether another skill already owns the same request;
- verify `.agents/skills/` remains the source tree and `.claude/skills/` links
  do not become a competing copy;
- search for stale field names, old paths, personal numbers, and contradictory
  terminology;
- distinguish a stale historical/audit statement (Warning) from a live
  instruction that can cause wrong writes or wrong analysis (Critical);
- keep user-specific baselines as runtime placeholders when the skill is public.

## Workflow

### 1. Establish scope

Run read-only inspection appropriate to the request:

```bash
git status --short --branch
git diff --name-status
git diff --cached --name-status
```

Include untracked files explicitly when they are in scope. Map each changed
path to one or more contract classes. If the user describes a change that is
not present in the current worktree, say so and review the current implementation
only as a baseline; do not invent a pending diff.

### 2. Load authorities and consumers

Read `AGENTS.md` and `ARCHITECTURE.md`, then follow the relevant source-of-truth
chain. Use `rg` to find:

- old and new field names;
- imports and file-path references;
- report keys and schema/version strings;
- `yaml.safe_load`, Pydantic models, JSON interfaces, fixture paths;
- writes to `market/`, public submodules, `data/finance/`, and skill prose.

For each claim, distinguish direct evidence from an inference. A document saying
"freshness checked" must be confirmed by a code path and a test or be marked as
an unimplemented contract.

### 3. Build the impact matrix

Return a matrix like this before making a decision:

| Contract | Source/owner | Consumers | Migration/version | Tests/gates | Result |
|---|---|---|---|---|---|
| daily log schema | ... | ... | ... | ... | OK/Warning/Critical |

Every changed source must have its consumers listed. Every changed consumer
must point back to its owner. If the owner is ambiguous, that is a Critical
finding even if the current tests pass.

### 4. Select focused verification

Do not run every pipeline by default. Select gates from changed paths:

- template/schema/daily log: `make lint`, focused tests, and migration dry-run
  (`make migrate` without `APPLY=1`) when available;
- thresholds/breakers/defaults: focused Python tests plus `make check` when
  logs are available; verify raw-vs-default and null semantics;
- wealth/report/JSON: wealth tests, report-contract fixture tests, golden render
  tests, and web typecheck;
- `wealth_rules.yaml`: YAML/schema metadata plus a search for an executable
  loader, freshness check, report consumer, and tests;
- public/private movement: inspect `git diff`, tracked public paths, fixtures,
  references, and child-repo imports; never initialize private data merely to
  complete a public-only review;
- skill/docs: quick-validate frontmatter, check references and trigger overlap,
  scan stale paths/terms/placeholders, and preserve historical audit text.

Report every gate as passed, failed, blocked, or skipped with its reason. A
missing `.venv` or private checkout is a boundary condition, not a test pass.

### 5. Decide severity

- **Critical**: ambiguous owner; missing migration for a breaking schema change;
  missing consumer for a promised runtime contract; report shape drift;
  private data in a public path; or a default that changes the meaning of a
  missing observation.
- **Warning**: stale historical documentation, a known temporary type gap, or
  a gate that cannot run in the current environment but is not required for the
  limited review.
- **Expected**: private data unavailable for a public-only review.
- **OK**: owner, consumers, semantics, provenance, privacy, and relevant gates
  agree.

Do not promote a Warning to Critical merely because a historical plan is stale;
do promote a stale live skill instruction when it can cause an agent to write
the wrong field or use a private value.

### 6. Produce the review report

Use this compact structure:

```markdown
## Contract review
[Status: OK/Warning/Critical/Expected] one-line conclusion

### Scope
- actual diff and changed contract classes

### Impact matrix
| Contract | Owner | Consumers | Migration/version | Tests | Result |
|---|---|---|---|---|---|

### Findings
- [Status: Critical] exact path and why it changes meaning
- [Status: Warning] exact stale or unavailable boundary

### Verification
- `command` — passed / failed / blocked / skipped (reason)

### Required next changes
1. exact file/consumer/test action
2. exact migration or version decision

### Decision
GO / CONDITIONAL GO / BLOCKED, with the reason

### Handoff
Use `repo-orchestrator` for release/submodule order. Use `tdd`,
`diagnose`, or `improve-codebase-architecture` for implementation. Use
`git-commit` only after explicit authorization and a clean contract review.
```

## Common failure patterns

- **History mistaken for a pending diff**: a commit proves the repository once
  changed; it does not prove the user's current worktree contains that change.
- **Compile success mistaken for contract success**: TypeScript can compile a
  stale interface while Python silently changes JSON shape.
- **Metadata mistaken for enforcement**: `source` and `verified_at` fields do
  nothing until a loader, freshness check, and test consume them.
- **Defaults mistaken for data**: a scoring fallback must not feed breakers or
  erase coverage uncertainty.
- **Directory separation mistaken for privacy**: search actual references and
  content; public code can still import or print private data.
- **Historical docs silently “fixed”**: preserve audit records and classify the
  discrepancy before changing current guidance.

## Completion criteria

The review is complete when the user can answer:

1. What is the canonical owner of every changed field or number?
2. Which consumers, fixtures, migrations, versions, and skills are affected?
3. What does missing, stale, or incomplete data mean at runtime?
4. Is any public/private boundary crossed?
5. Which gates passed, failed, or were unavailable?
6. Is the change GO, CONDITIONAL GO, or BLOCKED, and what exact action resolves it?
