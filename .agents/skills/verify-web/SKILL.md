---
name: verify-web
description: >
  Drive the local Personal-OS web app (web/, Next.js) the way the owner does and capture evidence:
  isolated launch, doctor, one journey per feature, screenshots + evidence.json, cleanup. Use before
  saying a web/ change works, when the owner reports "page X looks broken / is stuck", or to prove a
  route renders with real private data. Covers Office, Finance, Home, Agent signals, Skill evals,
  Flows and Design;
  the feature map in features/ lists how to reach and drive each one. Not a replacement for
  `make test-browser` (fixed regression suites); this is for ad-hoc proof of the change in hand.
---

# verify-web

Prove web behavior by driving the real app, not by reading code. Read `features/README.md`
first and pick the feature(s) your change touches. A proof that drives one convenient route is
incomplete when the map lists other entry points for the same feature.

All commands run from the repo root unless stated. Default port 3041 (`VERIFY_PORT` or first arg).

## Launch

```bash
.agents/skills/verify-web/scripts/launch.sh 3041     # prints http://127.0.0.1:3041 when usable
```

Starts `next dev` on 127.0.0.1 with its own `NEXT_DIST_DIR=.next-verify-<port>` and its own process
group, so it never shares the owner's `make web` / `make office` instance (3000) or the Playwright
server (3027). Ready = `/design-system` returned the rendered app shell (first compile ≈ 5–30 s).
It refuses to start if another process owns the port. Needs `web/node_modules`.

## Doctor

```bash
.agents/skills/verify-web/scripts/doctor.sh 3041     # exit 0 = worth driving
```

Read-only: our process alive, port owned by our process group, app shell renders, private `data/`
present or absent. Run before the first drive and again after any failed or surprising drive.

## Drive

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /flows --heading "Flows" --expect-text "Pipeline graph" --label flows
```

Options: `--route` (path + query), `--heading` (exact h1 accessible name), `--wait-for <css>`
(repeatable; required for WebGL pages; `'iframe >> <css>'` waits inside a same-origin iframe),
`--click "<button or link name>"` (repeatable, exact accessible name), `--expect-text "<text>"`
(repeatable), `--width 320|390` (mobile), `--full` (full-page `after.png`), `--dark`, `--label`.
Every drive fails on a page error or on page-level horizontal scroll.
Uses system Chrome via `@playwright/test` from `web/` (`CHROME_PATH` overrides). Selectors are
accessible names, matching `web/tests/browser/*.spec.ts`. Per-feature commands: `features/*.md`.

## Evidence

Each drive writes `web/.verify-web/<UTC stamp>-<label>/` (gitignored). Server ownership
(`.run-<port>/pid`) lives there too. Never move either under `web/test-results/`: every
Playwright run (`make test-browser`, `make scene-check`) deletes that folder, which orphans
the server and erases evidence. Contents:
`before.png`, `after.png`, `evidence.json` with every step and its outcome, `page_errors`,
`console_errors`, `failed_responses`, and `writes` (non-GET `/api/` requests = side effects).

Proof standards:

- Exercise the real user path (nav link or URL the owner uses), not internal setters or fixtures.
- A proof is the action **and** the resulting state: `before.png` → `after.png` + the asserted text.
- Check `writes`: a read-only journey must have none; a write journey must show exactly the
  expected request and the persisted result after reload.
- Open the screenshots. A `pass` with a blank WebGL canvas or an error card is not a proof.
- Baseline noise, not a failure: one `404 (Not Found)` console error = browser favicon fetch
  (`/favicon.ico` has no route); it never appears in `failed_responses`.
- Privacy: Finance amounts are masked by default. Never click **Show amounts** in a captured
  journey, and never copy finance screenshots outside `web/.verify-web/`.

## Cleanup

```bash
.agents/skills/verify-web/scripts/cleanup.sh 3041
```

Kills only the process group `launch.sh` started, removes `.next-verify-<port>` and the run state,
and keeps every evidence folder. Run it after every failed iteration too. Never `pkill node/next`.
If the pid file is gone, it kills nothing: it names the remaining listener and, when that
matches `launch.sh`'s command, prints the exact `kill -TERM -- -<pgid>` to run after you check it.

## Feature map upkeep

`features/` is the maintained verification source. When a change adds, renames or moves a route,
control or entry point, update that feature file in the same change and drive it once. If a
journey fails because the app no longer behaves as mapped, decide: doc drift (fix the map) or
product regression (report it; never weaken the journey to make it pass).

## Warm 3D construction adapter

For repeated 3D edits use `make scene-preview SCENE=office|characters|home` and
`make scene-stop` ([workflow guide](../../../docs/design/3d-world-workflow.md)).
This reuses the launch/doctor/drive/cleanup scripts with `VERIFY_STATE_ROOT` set to
`web/.scene-preview/`, separate from the default `web/.verify-web/`. `VERIFY_KEEP_BUILD=1` keeps the owned
Next build cache on cleanup. Default verify-web behaviour and cleanup remain unchanged.

The driver also accepts `--out-root <directory>`, `--reduced-motion`, `--read-only`
(fail on API writes) and `--asset-strict` (fail on non-favicon HTTP errors).
Available `data-render-stats` values (including same-origin iframe scenes) are included in evidence.json.
Warm previews are iterative evidence; final acceptance follows the scene standard's
changed-file scope map and still requires opening the screenshots.
