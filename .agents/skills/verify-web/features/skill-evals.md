# Skill evals

## Sub-features

- h1 "Skill regressions": stat tiles Passed runs, Failed runs, Inconclusive, Unreviewed.
- Warning card about self-reported execution logs.
- `Configuration comparison` table (with skill / without skill; conclusive pass rate).
- `Cases and execution stages`: open a case for its acceptance checks, reviewed outputs and
  evidence gaps; `Evidence requiring repair` when evidence is broken.

## How to get to it (user POV)

Top nav **Skill evals** → `/skill-regressions`. Data from
`python3 scripts/skill_regressions.py --json` (synthetic, independently reviewed cases).

## Driving it with drive.mjs

```bash
cd web && node ../.agents/skills/verify-web/scripts/drive.mjs --port 3041 \
  --route /skill-regressions --heading "Skill regressions" \
  --expect-text "Configuration comparison" --label skill-evals
```

## Gotchas

- If the script fails, the page renders a second h1-level state "Skill evidence unavailable"
  with `Try again`; the `Skill regressions` h1 still matches, so also assert
  `Configuration comparison`.
- Inconclusive is not failure: it means missing evidence. Do not read a high inconclusive count
  as a regression.
