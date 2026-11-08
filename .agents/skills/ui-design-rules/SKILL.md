---
name: ui-design-rules
description: >
  Hard NEVER/ALWAYS rules for Personal-OS web UI (web/ dashboard and shareable HTML). Load before
  writing or reviewing any component, page, CSS, or Tailwind class in web/. Covers colour roles,
  tokens, the Button primitive, focus, numbers, touch targets, and acceptance. Principles live in
  docs/design-system.md; this skill is the checklist an agent must obey, not a restatement.
user-invocable: false
---

# UI design rules — Personal-OS

Principles and rationale: [docs/design-system.md](../../../docs/design-system.md).
Reuse catalog and recipes: [docs/design/interface-patterns.md](../../../docs/design/interface-patterns.md).
Open `/design-system` in the local dashboard before choosing new styles. This file only lists
the rules that are cheap to check and expensive to get wrong.

## Colour roles (tokens in `web/app/globals.css`)

| Role | Tokens | Means |
|---|---|---|
| Chrome / text | `foreground`, `muted-foreground`, `border`, `card` | Structure; recedes |
| Interactive | `action`, `ring` | "You can click this" and focus. Nothing else |
| Status | `ok`, `warning`, `critical` | State of the data, with a text label |
| Series | `--series-1..4` | Chart categories only |

- NEVER use `ok`/`warning`/`critical` for a button, link or decoration, and NEVER use a status
  colour as a chart series. `action` is never a data direction.
- NEVER hardcode a hex or `hsl()` in a component. Add or change a token, then run `make design-check`.
- NEVER lower a token's lightness without re-running `make design-check`; text roles need 4.5:1,
  `ring` 3:1, in light and dark.
- NEVER let colour be the only carrier of meaning: pair it with a label, icon or sign.

## Components

- ALWAYS use `web/components/ui/button.tsx` for buttons. NEVER write `<button className="rounded border ...">`.
  Variants: `default` (primary), `outline` (default), `ghost`, `destructive`; sizes `default`, `sm`.
- ALWAYS reuse SectionCard, Stat, StatusBadge, DataState, Select before inventing a surface.
- NEVER write a native `<select>`, `<input>`, `<textarea>` or hand-styled `<button>` in `web/`. Use `Select`
  (`components/shared/select.tsx`), `Input` / `Textarea` (`components/ui/input.tsx`) and `Button` / `buttonClass()`
  (`components/ui/button.tsx`; `buttonClass` is for an `<a>` that must look like a button). A selectable list row
  is the one legitimate native `<button>`; update the baseline when you add one.
- NEVER restyle `.design-select-*` internals from page CSS. A page may set only the trigger's width. Pass layout
  through `className`, never colour or border.
- NEVER add a hex colour to page CSS or a Tailwind `[#hex]` class; add a token to `globals.css`.
- A standalone HTML page (e.g. `home-design/apartment.html`) cannot see the tokens: it must link the token
  stylesheet or be rewritten as React. It does not get its own palette.
- ALWAYS build a new standalone HTML deliverable (inside or outside the repo) with `make ui-build SPEC=… OUT=…`
  and deliver it only after `make ui-check MANIFEST=…` passes. A provenance comment or a hand-copied
  stylesheet fails the check; `make ui-check HTML="page.html"` audits any existing page. Domain owners
  with their own builder (travel: `scripts/travel_build.py`) keep it.
- NEVER add `outline-none` / `focus:outline-none`; the global `:focus-visible` rule owns focus.
- NEVER nest a card inside a card just to separate paragraphs; use section spacing.
- Copying a component from another repo: record upstream path, reviewed SHA (or "unpinned") and
  differences beside it.

## Content and numbers

- ALWAYS use the `num` class (tabular figures) for money and aligned columns.
- ALWAYS keep unit, scope and as-of visible; missing data is never rendered as zero.
- ALWAYS render money amounts and holding quantities on `/finance` through `Money` / `Private`
  (`web/components/shared/privacy.tsx`); they are hidden by default behind the page's eye toggle.
  NEVER print one with a bare `myr(...)` in JSX there. Rates, percentages and market prices are not masked.
- Distinguish loading / empty / no-match / error with `DataState`.

## Layout and access

- Touch targets ≥ 44px on narrow screens; icon-only controls need an accessible name;
  decorative icons use `aria-hidden="true"` (Lucide only).
- A wide table scrolls in its own labelled region; the page must not scroll horizontally at 320px.
- Respect `prefers-reduced-motion` and `prefers-reduced-transparency`; glass needs a solid fallback.

## Before saying "done"

1. `make design-check` and `make test` pass. `design-check` includes the `design_rules_check.py` ratchet; a new
   violation fails it. Lowering a count means running `python3 scripts/design_rules_check.py --update`.
2. Rendered page checked at 390px and desktop, light and dark. Say what was not checked.
3. PR/task notes list: page pattern chosen, assets reused, genuinely new decisions.
