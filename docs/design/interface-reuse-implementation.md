# Interface reuse — implementation plan

[Status: OK] Implemented; scoped engineering checks passed · 2026-10-27

## Goal

New UI tasks can find reusable implementations, choose a common page composition,
and replay known failure scenarios without reconstructing earlier design decisions.

## Approach

Extend the shared guide with a route to `docs/design/interface-patterns.md`.
Keep principles in the guide and exact styles in existing application owners.
Add a synthetic `/design-system` page using the actual local components, reachable
from dashboard navigation. Use an implementation plan because there is no new
API, data model or business rule. A catalog and a local reference route meet this
need without a new shared package or component framework.

## Implementation

1. Add the catalog: implementation links, overview/comparison/detail compositions,
   known-failure replays and local-copy provenance.
2. Link the guide, index and UI section of `docs/dev-sop.md`; preserve its Mermaid.
3. Add `web/app/design-system/page.tsx`, a local interactive reference with fixture
   states and stress content. Add one link to existing dashboard navigation.
4. Extract DataState for the reference and actual Skill regressions page; move
   long-value handling into Stat and enlarged-text wrapping into shared styles.
5. Typecheck/build, run branch regression checks, and inspect production renders
   and keyboard interactions.

## Verification

Run `npm run typecheck` and `npm run build` in `web/`. Run the repository Mermaid
checker against `docs/dev-sop.md`. Inspect the reference at 320px, 390px and desktop,
light/dark, glass/solid, enlarged text, Select keyboard/Escape focus, disabled
choices, all five data states and local table scrolling. Record actual evidence
and gaps at delivery; this plan does not assert those checks have passed.

## Risks and boundaries

The workspace already contains uncommitted design changes; preserve them.
Only synthetic fixture data is used, with no private finance reads. The page
reviews current components and is not a claim of user-approved visual quality.
No production data flow or existing business behavior is changed.

## Verification record — 2026-10-27

Implementation is in the working tree above base commit
`bece090a867eba8913be759cb8d5fe72d7ad3711`; it is not committed.
Final production build ID: `WKDrNMcjhv6IXjxLp0wZ1`.
Preview: `http://127.0.0.1:3047/design-system`.
Existing unrelated changes were preserved.

### Shared implementation and actual consumer

- `web/components/shared/data-state.tsx` provides complete/loading/empty/error/
  partial presentation. Callers own meanings, triggering conditions and recovery.
  Recovery controls are outside the live region; headings support page hierarchy.
- `web/components/shared/stat.tsx` owns long-value wrapping; the reference no
  longer patches numeric overflow with a page-specific selector.
- `web/app/design-controls.css` provides inherited text wrapping, including
  headings, paragraphs and action labels at enlarged text sizes.
- `web/app/skill-regressions/page.tsx` adopts the catalog's comparison recipe,
  DataState for report failure/empty configurations, a recovery link, optional
  diagnostics and a labelled keyboard-focusable table scroll region.
- The [catalog trial](interface-patterns.md#reuse-trial--skill-regressions) records
  the page pattern, reused assets and new decisions. No time-saving claim is made.

### Automated checks

| Command / check | Result |
|---|---|
| `npm run typecheck` in `web/` | Pass; final production build also repeats type validation |
| `npm run build` in `web/` | Pass on final source; reference statically prerendered |
| `node --test tests/interface-reuse.cjs` in `web/` | 2/2 pass: actual report page with an independent empty fixture and a throwing report source |
| `python3 scripts/check_mermaid.py docs/dev-sop.md` | Pass; existing Mermaid preserved byte-for-byte |
| Relative links in guide/catalog/plan/SOP/index | No missing local file targets |
| `git diff --check` | Pass |
| Actual `/skill-regressions` request | HTTP 200; normal configuration comparison and case sections retained |

The two Node checks render the actual page with synthetic source results; they
verify error/empty branch presentation, heading/skip destination, recovery link,
and preserved diagnostics. They do not prove a real backend failure/recovery.

### Browser checks

Safari 27.0.1 completed the checks after Chrome's native input became unreliable.
Use the responsive width field and the native View → Make Text Bigger command;
Safari reports one CSS pixel less than the nominal 320/390px preset in this setup.
Screenshots were visually inspected in the session; numerical observations and
replay steps are retained here. No durable screenshot files were saved.

| Scenario | Observation |
|---|---|
| Reference, nominal 320px / normal text | `innerWidth=319`, document width `319`; all five Stat surfaces contain their values |
| Reference, nominal 390px / normal text | `innerWidth=389`, document width `389` |
| Reference, nominal 320px / enlarged text | Body text `39.813122px` versus normal `16px` (about 249%); final document width `319`, viewport `319`, no Stat overflow |
| Local table scroll | Table width `640`, region width `247`, region scrollLeft `200`, window scrollX `0` |
| Actual Skill regressions page, nominal 320px | Viewport/document both `319`; labelled comparison region present; normal report rendered |
| Light/dark and glass/solid | All four combinations inspected during the run; menu stays open for consecutive toggles and exposes checked states |
| Production glass over scrolled content | Computed `backdrop-filter: blur(32px) saturate(1.15)`; light backplate alpha `0.93`, `data-scrolled=true` |
| Solid mode | Computed `backdrop-filter: none` in both light and dark |
| DataState fixtures, final component | Complete zero, loading, no records, failure and partial subtotal all replayed through keyboard selection |
| Retry | Error fixture's Retry returns to confirmed-zero/complete state |
| Filter | End skips disabled archived choice and selects the last enabled option; no-match state appears; Reset restores all three results |
| Exact ID | Arrow/Enter preserves `900719925474099312345678901234567890` in the trigger/output |
| Typeahead and focus | Typing `a` selects All sample accounts; Escape closes and restores trigger focus |
| End of page | Chinese copy, expanded warning and final footer inspected at nominal 320px; footer reachable and readable |
| Desktop | Final reference inspected after exiting responsive mode; normal text size and original dark/glass preferences restored |

### Reproduced defect and regression

At nominal 390px with text enlarged to about 249%, long headings made the document
`446px` wide for a `389px` viewport. Wrapping headings removed that source.
At nominal 320px the same enlargement also exposed long prose/action labels:
the document was `390px` wide for a `319px` viewport. Applying inherited
`overflow-wrap: anywhere` made viewport and document both `319px`.
The final production build was refreshed, removing all temporary inspector styles,
and the original narrow/enlarged scenario passed with the shared source rule.

Replay after changing typography or surfaces:

1. Open `/design-system` at nominal 320px and 390px, normal text. Check the
   stress section, table, state example and footer.
2. Use Safari's Make Text Bigger five times from 16px; verify computed body text
   is about 39.8px, then compare document scrollWidth with innerWidth (allow only
   1px rounding). Long titles, action labels and Stat values must wrap.
3. Restore text size. Cycle Complete → Loading → Empty → Error → Partial via
   the Data state Select. Retry Error; it must return to confirmed zero.
4. In Sample account, use End/Enter for the last enabled long label; reset the
   no-match result. Select the long ID by arrows; reopen, type `a`, commit, then
   reopen/Escape and inspect trigger focus.
5. Check Appearance in both themes and both material modes while scrolled.
   Inspect computed production blur; scroll the comparison locally and verify
   window scrollX stays zero. Restore the original settings afterward.
6. Open `/skill-regressions` to check the real comparison composition, then run
   the two Node checks for the synthetic empty/failing report branches.

This is scoped engineering verification. User aesthetic approval remains a
separate judgment; the reference is not labelled a user-approved visual baseline.
