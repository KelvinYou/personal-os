# Personal-OS Documentation

Durable, agent-readable docs for Personal-OS. Private personal state lives under `data/`, never here.

**Start at [`INDEX.md`](INDEX.md).** It owns routing, the source-of-truth matrix, and the agent read order. This file only orients a first-time reader and does not repeat them.

## Layout

| Path | Holds |
|---|---|
| [`VISION.md`](VISION.md) | Product direction |
| [`DECISIONS.md`](DECISIONS.md) | Settled trade-offs |
| [`ROADMAP.md`](ROADMAP.md) | Unfinished work; links into `plans/` |
| [`dev-sop.md`](dev-sop.md) | Feature and bug-fix workflow |
| [`design-system.md`](design-system.md) | Shared interface principles |
| [`design/`](design/) | Implementation-ready technical designs |
| [`plans/`](plans/) | Multi-phase plans with per-phase status |
| [`knowledge/`](knowledge/) | Evergreen, cross-project notes |
| [`analysis/`](analysis/) | Time-bound analysis; check the re-verification date before citing |
| [`drafts/`](drafts/) | Content pending external publish; copy manually, do not paste blind |

## Writing rules

- English only, CommonMark.
- No personal values: holdings, thresholds, and health data stay in `data/`.
- One owner per fact. Link to the owner instead of copying it.
- New knowledge notes follow the minimal contract; run `make kb-check` after adding one.
- Add every new durable doc to [`INDEX.md`](INDEX.md).
