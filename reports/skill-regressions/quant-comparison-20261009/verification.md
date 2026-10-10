# Quant comparison skill verification — 2026-10-09

[Status: OK] Skill frontmatter, description length, six unique eval IDs, referenced
comparison owners and scoped Git whitespace checks passed. Changes are agent
guidance and evaluation prompts only; no strategy, threshold, forecast, schema,
portfolio holding or submodule code was changed for this correction.

## Root cause and contract review

The executor narrowed a broad request to the overall signal row despite available
allocator evidence. Old skill guidance described statistical review but lacked
an explicit composed-system coverage step. This is an execution omission with
a repeatable guidance gap, not proof that the skill caused the omission.
The quant skill owns comparison interpretation; wealth-manager retains holdings
decisions. Child artifacts and code retain metric ownership. No migration is
needed. Data lifecycle, cross-language schemas and deployment are out of scope.

## Controlled paired check

Two isolated agents read old/new skills and answered three prompts using the
same supplied synthetic facts. Neither saw this conversation; neither fetched
data or edited artifacts. Cases: broad comparison, no-trade diagnosis, unavailable
allocator/hybrid.

Both versions covered supplied allocator and hybrid facts, separated experiments,
partitioned all 96 calls, identified convergence failure, avoided double-counting
32 overlapping codes and marked missing arms unavailable. New guidance explicitly
requires these steps. There is no demonstrated coverage-rate improvement from
this small check: facts were supplied directly, so it does not test discovery
from repository reports or establish future reliability. The original omission
is the observed failing example; this check is a bounded instruction sanity check,
not a full live-pipeline benchmark or a statistical skill-performance claim.

No new model forecasts, paid provider calls, price refreshes or trades occurred.
The recognized behavior correction remains pending in the correction queue;
AGENTS.md was not edited.
