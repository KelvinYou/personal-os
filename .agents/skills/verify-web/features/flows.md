# Flows

## Sub-features

- h1 "Flows" with generation time and node/edge counts.
- `Pipeline graph` card: make targets, scripts, data paths, submodules; click a node for detail,
  drag/scroll to pan and zoom.

## How to get to it (user POV)

Top nav **Flows** → `/flows`. Reads `web/public/flows.json` on every request.

## Driving it with drive.mjs

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /flows --heading "Flows" --expect-text "Pipeline graph" --label flows
```

## Gotchas

- `flows.json` is a generated artifact. If a Makefile/script change should alter the graph, run
  `make flows` first; otherwise the page proves the old graph. `make doctor` warns on drift.
- Missing file renders a `flows.json 缺失` Critical badge instead of the graph; the h1 still
  appears, so also assert `Pipeline graph`.
