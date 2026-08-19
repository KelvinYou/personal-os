---
name: git-commit
description: Coordinate safe, atomic Git commits across the current repository and its parent/submodule graph. Use whenever the user asks to commit, save work to Git, prepare commits, split changes into commits, update submodule pointers, or write a commit message. Default to a bounded quick preflight of about 10 seconds; use full validation only when requested or selected after a timeout. Inspect all relevant repositories, build a commit plan, commit child repositories before parents, and verify the final state.
allowed-tools: Bash, Read, Glob, Grep
---

# Git Commit / Version Control Coordinator

Treat a commit request as a version-control operation, not as a request to run
`git add . && git commit`. Discover the repository graph, classify the actual
diff, produce an atomic commit plan, execute only that plan, and verify every
repository involved.

`repo-orchestrator` owns read-only integration preflight when the user asks for
an inspection, release check, or submodule analysis without committing. This
skill owns the commit path and must perform the relevant preflight itself when
the user explicitly asks to commit.

## Operating contract

- Default to `split=auto`, `scope=reachable repositories`, and `push=never`.
- Default to `check_mode=quick` with a 10-second wall-clock budget. Do not
  silently turn a normal commit into a full test/build pipeline.
- Interpret “commit everything” as “commit every attributable change using the
  normal split policy,” not as permission to collapse unrelated work into one
  commit.
- Treat repository boundaries as hard commit boundaries. A parent repository,
  each initialized submodule, and each nested submodule are separate commit
  domains.
- Never commit a change whose ownership or intent cannot be explained from the
  user request, the diff, or repository-local instructions. Put it in an
  `unattributed` bucket and ask one consolidated question when necessary.
- Never stage secrets or likely secrets: `.env*`, credentials, tokens, private
  keys, signing material, or files whose contents reveal secrets.
- Never use `git reset`, `git checkout`, `git clean`, `git stash`, `git amend`,
  `--no-verify`, force push, or any operation that discards or rewrites work
  unless the user explicitly requests that exact operation.
- Never push automatically. A commit request authorizes local commits only.
- Preserve existing staged selections. Do not silently unstage them or add
  unrelated files.
- Write every commit message in English only, including its subject, body, and
  any manually supplied trailers. Do not use Chinese or other non-English prose
  in commit messages.

## Check modes and latency budget

The commit path has two deliberately different guarantees:

| Mode | Default | What it checks | When to use |
|---|---:|---|---|
| `quick` | yes | repository graph, status, staged whitespace, secret-like paths, and pointer state | normal local commits; target about 10 seconds |
| `full` | no | quick checks plus relevant instructions, semantic diff review, tests, lint, typecheck, build, and final recursive verification | release, risky changes, explicit `full`/`strict` request, or user selection after timeout |

Run the bounded quick lane with the bundled read-only preflight:

```bash
python3 <git-commit-skill>/scripts/preflight.py <path> --scope workspace --budget 10
```

Replace `workspace` with `ancestors` or `current` when the scope rules call for
it.

The quick lane is a safety gate, not a claim that project tests passed. In
quick mode, skip expensive `make test`, web builds, full-history reads, and
unrelated sibling-repository instruction loading unless the change map shows
that repository is dirty or selected. A quick preflight warning still needs
inspection; it is not permission to stage a secret candidate or ambiguous
change.

Classify known boundaries instead of escalating them unnecessarily: an
unavailable private `data/` checkout can be `[Status: Expected]` when it is not
needed, and a child `HEAD` differing from the parent gitlink can be part of the
planned child-before-parent sequence. Unresolved ownership, protected paths,
conflicts, or pointer state outside the plan still stop the commit.

If the preflight returns `status=timeout` or `status=error`, stop before
staging or committing and report the completed checks and elapsed time. Ask the
user to choose exactly one of: continue with `full`, continue with the
completed `quick` checks while explicitly accepting skipped validation, or
cancel. Never infer that timeout means approval to bypass checks.

Users may request `full` before the workflow starts. A request for `release`,
`strict`, `audit`, or CI-equivalent validation also selects `full`; otherwise
the default remains `quick`.

## Scope rules

1. Resolve the current Git repository with `git rev-parse --show-toplevel`.
2. If it has a superproject, inspect the current repository and its ancestors.
3. If the user says “all submodules,” “whole workspace,” or “finish everything,”
   inspect every initialized repository below the topmost superproject.
4. When scanning siblings, do not commit them merely because they are dirty;
   commit only changes attributable to the current request. Report unrelated
   dirty siblings separately.
5. A missing or uninitialized submodule is a boundary to report, not a reason
   to run `git submodule update` or fetch without authorization.

Use the bundled read-only scanner when available:

```bash
python3 <git-commit-skill>/scripts/scan_repositories.py <path> --scope workspace
```

Use `--scope ancestors` for a nested-repository request that does not include
sibling repositories, and `--scope current` when the user explicitly limits
the operation to one repository.

## Workflow

### 1. Run the bounded preflight before touching the index

In `quick` mode, run `preflight.py` once before staging. It emits a JSON
snapshot and uses one shared wall-clock deadline, so a slow Git command cannot
silently expand the latency budget. Then use its repository map to identify
the exact changed paths and any warnings.

In `full` mode, run the scanner or equivalent read-only commands for every
in-scope repository:

```bash
git status --short --branch --untracked-files=normal
git diff --cached --name-status
git diff --name-status
git log --oneline -10
git submodule status --recursive
```

For each repository record:

| Field | Meaning |
|---|---|
| Repo | Absolute path and role in the graph |
| HEAD | Actual child commit, if initialized |
| Branch | Branch name or `DETACHED` |
| Worktree | Clean, modified, untracked, conflicted, or unavailable |
| Staged | Exact paths already in the index |
| Unstaged | Exact modified paths |
| Untracked | Exact untracked paths |
| Parent pointer | Parent `HEAD` gitlink versus child `HEAD` |
| Recent style | Recent commit subjects and local instructions |

Read the applicable `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and package
instructions before choosing validation commands or commit conventions. In
quick mode, load instructions only for the current repository and dirty or
selected child repositories; clean siblings do not justify a full instruction
walk. Do not assume that the current repository's commit style applies to
every child.

### 2. Build a change map

Classify each path using the diff and task context, not the filename alone.
Record one of these states:

- `selected`: explicitly named by the user or already staged;
- `attributable`: clearly part of the current task;
- `unattributed`: dirty before the current task, unrelated, or ambiguous;
- `protected`: secret candidate or otherwise unsafe to stage;
- `unavailable`: repository or submodule is not initialized.

Do not assume that all dirty files were created by the current conversation.
When timestamps, the diff, or task context cannot establish ownership, ask for
clarification instead of guessing.

### 3. Group changes into a commit plan

Apply these rules in order:

1. Never combine paths from different repositories.
2. Keep implementation and its necessary tests together when they represent
   one independently understandable change.
3. Split unrelated feature, bugfix, refactor, docs, data refresh, dependency,
   generated-output, and formatting work by default.
4. Keep a source-of-truth file and its required generated output together only
   when the repository contract requires them to move together.
5. Keep a submodule pointer update in the parent separate from the parent's
   own product/docs/config changes unless the user explicitly defines one
   integration change.
6. Group multiple parent pointer updates only when their child commits belong
   to one clearly identified integration task. Otherwise use one pointer group
   per child.

Before committing, form a plan with this shape and show it in the response:

| Order | Repository | Group | Exact paths | Rationale | Validation | Subject |
|---:|---|---|---|---|---|---|

Use one consolidated confirmation only when the plan contains an ambiguity,
protected file, mixed staged intent, an unavailable required repository, or a
potentially destructive choice. If the user explicitly authorized committing
and the plan is unambiguous, continue after presenting the plan.

### 4. Validate each group

- Stage only exact paths for the current group with `git add -- <paths>`.
- Do not use `git add .` or `git add -A` for a mixed worktree.
- If files are already staged, inspect `git diff --cached`; treat that set as
  the user's boundary and stop if it contains multiple unclear intents.
- Run `git diff --cached --check` before committing.
- In `quick` mode, do not run project tests, typechecks, lints, or builds by
  default. Report them as `[Status: Expected] skipped in quick mode`.
- In `full` mode, run the narrowest relevant test, typecheck, lint, build, or
  data/schema check documented by the repository. Report skipped expensive
  checks explicitly.
- Re-read the staged diff and confirm that every staged path belongs to the
  planned group and no protected path is present.

Do not use a passing hook as proof that the grouping is correct. Grouping and
repository-boundary checks remain mandatory.

### 5. Execute in dependency order

Commit repositories from deepest child to topmost parent:

1. Commit the actual changes inside each child repository.
2. Refresh the parent status and inspect the exact gitlink change.
3. Commit the parent pointer with a separate, precise subject such as
   `chore(submodule): update ai-stock-analysis`.
4. Commit any parent-owned files in their own planned group.
5. Repeat for nested submodules and then continue upward.

Never claim that a parent commit contains uncommitted child files. A parent can
record only the child's commit pointer.

Use the repository's recent convention for type, scope, and body format, while
keeping the entire message in English. If no convention exists, use a concise
Conventional Commit subject, lowercase after the colon, no trailing period, and
a first line under 72 characters. Describe intent rather than listing filenames.
Do not add a model-specific `Co-Authored-By` line unless the user or repository
policy explicitly requires one; use the configured Git identity otherwise.

For a hook failure, do not amend the previous commit and do not skip the hook.
Inspect the failure, make only an in-scope fix when authorized, re-stage the
same group, and create a new commit after the hook passes. If the failure is
outside scope, stop and report it.

### 6. Verify the final graph

After each commit, record the hash and subject. At the end:

```bash
git status --short --branch --untracked-files=normal
git submodule status --recursive
git log --oneline -n <number-of-new-commits>
```

In `quick` mode, rerun the bounded preflight for the affected repositories and
inspect the final `git status`/gitlink state. In `full` mode, also run the
bundled pointer verifier when available:

```bash
python3 <git-commit-skill>/scripts/verify_submodule_pointers.py <path>
```

Verify that:

- every intended group has exactly one expected commit;
- every child commit exists before its parent pointer commit;
- every parent pointer refers to the intended child `HEAD`;
- remaining dirty files are explicitly listed as `unattributed`, skipped, or
  hook-related rather than hidden behind “commit complete”;
- no push occurred.

Treat detached `HEAD` in a submodule as a warning: it is common in checked-out
submodules, but the resulting commit needs a branch or explicit push mapping
before it can be shared remotely.

## Output contract

Return a compact report in this order:

```markdown
## Commit plan
<group table>

## Commits
- `<repo>` `<hash>` `<subject>`

## Verification
- [Status: OK/Warning/Critical/Expected] `check_mode=quick|full`; ...

## Remaining work
- none, or exact repository/path and reason
```

If there is nothing attributable to commit, say so and do not create an empty
commit. If the request was only for a plan, stop after `Commit plan`.

## Common failure patterns

- **One giant batch:** re-run grouping by repository and intent; “all” does
  not mean “one commit.”
- **Parent appears dirty after child work:** inspect the child first, then treat
  the parent gitlink as a separate planned commit.
- **Parent looks clean while child is dirty:** inspect every submodule directly;
  a parent status line is not a child worktree report.
- **Staged files silently expand:** preserve the index and never add more paths
  without an explicit plan.
- **Detached child commit:** warn and record the exact hash; do not push or
  rewrite branches automatically.
- **Wrong commit style:** inspect that repository's recent log instead of using
  the Personal-OS convention everywhere.
- **Quick lane becomes a hidden full pipeline:** keep tests and builds behind
  explicit `full`; the 10-second budget is for structural preflight only.
- **Timeout treated as approval:** stop before staging and ask whether to run
  full validation, accept the quick-only risk, or cancel.
