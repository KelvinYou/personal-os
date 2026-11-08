# Office

## Sub-features

- Header "A little space for big ideas." with a source badge (`DEMO · SIMULATED EVENTS` in demo).
- Source select (`Demo office` or live Codex observation), skill-employee count, observed time.
- Studio card: `3D room` / `Worker list` view toggle, `Meet the cast ↗`, side-panel toggle,
  `Fullscreen`.
- 3D room: `Overview` / `First person` / `Third person` camera modes, `Name labels` toggle,
  zoom/reset controls, one labelled station per skill employee plus the owner desk.
- Worker list: "Your team at a glance." rows with status (`Working`, `Standby`).
- Team tasks / collaboration panels (scenario `team`), posts, workbench — covered by the
  dedicated `office-*.spec.ts` suites.

## How to get to it (user POV)

Top nav **Office**, or open `/`. Demo without private config: `/office?mode=demo`.
Team scenario: `/office?mode=demo&scenario=team`.

## Driving it with drive.mjs

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route "/office?mode=demo" --wait-for canvas --wait-for .office-host-label \
  --click "Worker list" --expect-text "Your team at a glance." --label office-demo
```

Proof: `before.png` shows labelled stations in the 3D room; `after.png` shows the worker list;
`writes` is empty.

## Gotchas

- Without `--wait-for canvas --wait-for .office-host-label` the screenshot is taken before the
  WebGL scene renders: an empty beige room that still reports `pass`. Always wait for both.
- The page has no `level: 1` heading matching a short name; do not pass `--heading` here.
- Live mode reads the owner's Codex sessions; screenshots may contain task text. Prefer demo
  mode unless the change is about live observation.
- Movement/camera changes need `make test-browser SUITES="office-player office-camera"` before
  and after (AGENTS.md); this journey only proves the page renders.
