# Interface design guide

[Status: OK] Active shared guidance · Updated: 2026-10-26

Use this guide when creating or reviewing Personal-OS pages, dashboards and HTML artifacts. It owns shared design principles; each application or skill owns its components and assets. Personal preferences remain in the owner's private reference files.

## Five principles

1. **Make the purpose and next action clear.** Lead with what the reader needs to understand or do. Use typography, alignment and grouped spacing to establish hierarchy. Choose the layout for the content: tables for numerical comparison, timelines for sequences, cards when items benefit from separate context.
2. **Keep information trustworthy.** Preserve amounts, dates, units, uncertainty and consequential warnings while simplifying the presentation. Use labels alongside semantic colours. Keep blockers visible; details can hold supporting explanation. A frequent or positive signal should not become a warning merely because its number is large.
3. **Let material support content.** For Apple-inspired interfaces, concentrate Liquid Glass in navigation and controls. Keep dense text and data on readable, near-opaque surfaces. A useful glass effect combines translucency, blur, edge highlights and restrained depth. Readability takes priority over transparency: sticky navigation needs a denser tint and stronger background diffusion once content scrolls beneath it; the interface should still work with glass turned off. This web treatment is an approximation of the native material. [Apple's materials guidance](https://developer.apple.com/design/human-interface-guidelines/materials) places Liquid Glass in the functional layer above content.
4. **Make the whole experience usable.** Adapt the composition to small screens and enlarged text. Provide labelled controls, visible keyboard focus and readable contrast. Respect reduced motion and transparency; offer a solid fallback when glass is used. Keep necessary two-dimensional content, such as a wide table, in its own scroll region where practical. [W3C reflow guidance](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) explains that distinction.
5. **Reuse what already works.** Start with the product's existing components and assets. Keep recurring values in local tokens rather than scattered overrides. Extract shared code when repeated use demonstrates its value; a principles document does not require a new component library. [Material's foundations](https://m3.material.io/foundations/) describe tokens as reusable style values across design and implementation.

## Flexible defaults

For a new utility page without an established visual identity, start with system typography, calm neutral surfaces, clear numeric alignment, comfortable spacing and restrained accents. Use glass where it makes navigation distinct. Imagery, richer colour, motion or different typography can be useful when they serve the page's purpose.

For Personal-OS pages and shareable HTML, use the local web dashboard as the visual baseline unless the user requests another direction. Consistency includes palette, typography scale, spacing, card treatment, navigation and appearance controls—not just matching icons. Adapt the content layout to its purpose while keeping that visual family. Compare the actual artifact with the dashboard at the same viewport and browser zoom before calling it aligned.

These are starting points, not a fixed template or a requirement to restyle every product. An explicit user brief and the host product's design language take precedence. Choose a different treatment when the content, platform or reader benefits; briefly explain a material departure when it affects review. Ordinary design choices do not need an approval step.

## Character and visual rhythm

The baseline is warm, clear and approachable. Airbnb's design work is a reference for typographic hierarchy, useful personality and coherent components: [Karri Saarinen's DLS account](https://karrisaarinen.com/dls/), [the Google Design case study](https://design.google/library/airbnb-invites-you-in) and [Takahiro Kawaguchi's account of DLS and Cereal](https://www.bureau415.com/work/airbnb). These describe design intent and historical work, not a current public Airbnb token specification. The following is our own adaptation.

Give each page a clear focal point, a useful next action and room to breathe. Use warm off-white backgrounds, charcoal text and white content surfaces. Let section spacing carry grouping before adding another nested card. On desktop, start with 32–46px page titles, 20–24px section headings, 14–16px body copy and 12–13px supporting text. Keep dense table text compact when comparison benefits; do not make an entire page tiny to imply sophistication. Use modest heading tracking and readable paragraph spacing. Retain system fonts with a full Chinese fallback; do not load Airbnb's proprietary typeface.

Use the personal website's cyan identity: `#00F0FF` for action fills with black text, and `#056775` for readable accent text, icons and focus in light appearance. Dark appearance can use the bright cyan as accent ink. Use pale cyan tonal surfaces for the main overview. The source palette is owned by `repos/portfolio-website/src/app/globals.css`; applications keep local copies without a runtime dependency. Airbnb informs hierarchy and approachable interaction, while the brand colour comes from the owner's website. Keep supporting links quieter. Brand colour means action or identity; failure still requires a labelled status, its reserved status colour and its own context. Do not recolour chart series or financial meanings to match the brand. Local role tokens (`--brand`, `--brand-soft`, `--space-section`, `--radius-surface`) carry the visual direction independently of status tokens.

Give different components different emphasis: an overview can have a softly tinted surface and generous spacing; a data panel is solid and calm; a Select stays compact and precise. Use rounded corners with purpose rather than the same large radius everywhere. Short hover and press responses make actions feel responsive; respect reduced motion. Preserve the established translucent navigation and the shadcn-inspired Select interaction model.

Write like a helpful guide: name the current context, the next step and any specific blocker. Empty states explain what belongs there. A pleasing layout must not conceal missing data, uncertain acceptance or environmental limits. Use real evidence thumbnails only where they help the task; decorative travel imagery does not belong in a finance or test workbench by default.

## Navigation and dropdowns

Keep translucent navigation when it improves the visual hierarchy. A floating header should have a quiet edge highlight, restrained shadow and a tinted backplate with real background blur. Once content scrolls underneath, increase material density and diffusion so underlying text and controls cannot compete with navigation labels. Do not solve this by lowering text opacity. Test both light and dark appearance over actual dense content, not only over an empty page. Reduced-transparency, increased-contrast and unsupported-blur modes use a solid fallback.

Verify computed `backdrop-filter` in the production build rather than relying on source declarations: CSS transforms can drop or rewrite vendor-prefixed declarations. Place the standard declaration after its vendor-prefixed fallback and check that the target browser actually applies the blur.

Treat dropdowns as readable content surfaces. Menus are solid or near-solid, even when their trigger sits in glass navigation. Portal content uses an explicit interface font so it does not inherit a different body default. Use the local Select and appearance-menu primitives for styled React workspaces: consistent trigger height and spacing, a quiet chevron, a clear selected mark, visible focus and hover, and restrained depth. Select styling follows the restrained [shadcn Radix Select](https://ui.shadcn.com/docs/components/radix/select) direction: 8px trigger and popup radii, 14px value text, a 40px desktop trigger (44px for touch), 4px popup inset, compact option rows and neutral hover/focus treatment. Reserve the right-side checkmark column for selection; avoid a persistent blue fill or oversized card-like rows. Keep disabled choices distinguishable and explain unavailable actions where useful. Let long labels and identifiers wrap; never turn a large ID into a number or truncate the only place it can be verified.

Portalled menus should align to their trigger, remain inside the viewport, have a bounded scroll region and sit above sticky navigation without clipping. Use tested keyboard and focus handling: Enter/Space opens, arrows and typeahead move through choices, selection commits once, Escape dismisses and restores focus, and clicking outside closes. Appearance settings stay open for consecutive toggles and expose their checked state to assistive technology. Respect reduced motion and keep touch targets comfortable on narrow screens.

The baseline implementation lives in `web/app/design-controls.css`, `web/components/shared/select.tsx` and `web/components/shared/appearance-menu.tsx`. Applications own their local copies and dependencies; copying this visual family does not require a runtime import from Personal-OS. Plain HTML exports can retain native selects when appropriate, with readable labels and the same control styling; do not hand-roll an inaccessible listbox for appearance alone.

## Icons and shareable HTML

Use [Lucide](https://lucide.dev/) as the default UI icon family when the host product has no established set. Choose a small consistent subset and reuse the same icon for the same meaning. Keep meaningful labels visible; decorative SVGs use `aria-hidden="true"`, and icon-only controls need an accessible name. Preserve the upstream licence when distributing icon assets. [Lucide provides SVG assets](https://lucide.dev/guide/packages/lucide-static) suitable for embedding directly.

Tailwind is a useful authoring option, especially in the existing dashboard; plain CSS remains suitable for standalone templates. The shared design comes from principles and reusable values, not a mandatory framework migration.

A shareable HTML artifact should arrive ready to open: embed only the selected SVGs, final CSS in `<style>`, and any optional interaction code in the file. When using Tailwind, compile the final content to static CSS before embedding it; the recipient needs no Node.js, build step or local server. [Tailwind's CLI](https://tailwindcss.com/docs/installation/tailwind-cli) generates static CSS; its [Play CDN](https://tailwindcss.com/docs/installation/play-cdn) is intended for development.

Keep reading and essential navigation available without JavaScript or a network connection. Bundle images if they are needed to understand the artifact; ordinary map or booking links may remain external. Before sharing, open the delivered file itself from disk with the network disabled. Some messaging apps restrict HTML previews; direct opening means a browser can render the file, not that every chat app supports it. Use a PDF or hosted view if the recipient's channel cannot open HTML.

## Tokens and primitives

Colour has four roles: chrome (`foreground`, `muted-foreground`, `border`), interactive
(`action`, `ring`), status (`ok`, `warning`, `critical`) and series. A colour keeps one role;
a link is never green and a buy signal is never a button colour. Text roles must reach 4.5:1 and
the focus ring 3:1 in light and dark. `make design-check` recomputes this from `globals.css`
and runs inside `make test`; change a token, then run it. Buttons come from
`components/ui/button.tsx`. The hard rules an agent must follow live in the
`ui-design-rules` skill so this guide stays principles-only.

## Short acceptance check

Inspect a real render appropriate to the change:

- Is the purpose, important information and next action easy to find?
- Are the densest section, long labels, numbers and warnings readable?
- Does it work on desktop and a narrow phone, with keyboard use and the supported appearance/material modes?
- Do controls work, and do unsupported effects fall back cleanly?

Check print or offline behaviour when the artifact promises them. Report unverified conditions honestly; a build or structural validator does not prove visual quality. This is a practical review checklist, not accessibility certification.

## Owners and evolution

| Concern | Owner |
|---|---|
| Shared design principles | This document |
| Travel composition, offline build and HTML assets | [Travel HTML reference](../.agents/skills/travel-plan/references/share-html.md) |
| Colour roles, contrast floors | [globals.css](../web/app/globals.css), checked by `make design-check` |
| Button primitive | [web/components/ui/button.tsx](../web/components/ui/button.tsx) |
| Agent-enforced hard rules | [ui-design-rules skill](../.agents/skills/ui-design-rules/SKILL.md) |
| Visual baseline and dashboard implementation | [web/app/globals.css](../web/app/globals.css), [web/app/design-controls.css](../web/app/design-controls.css) and [web/components/](../web/components/) |
| Personal taste and task-specific exceptions | Owner instructions and optional private reference files |

Add guidance when it resolves a recurring design failure or a repeated need. Prefer improving an existing principle to adding another rule. Leave exact colours, sizes, class names and domain-specific behaviour with their implementation owner.

## Start a UI task from an existing implementation

Choose the host product first. For Personal-OS, open the local `/design-system`
reference page and [reuse catalog](design/interface-patterns.md) before choosing
new styles. The reference uses synthetic data and the actual local components;
it is a review surface, not a user-approved visual baseline.

Record the chosen page pattern, reused assets, and genuinely new decisions in
the task or PR. Follow [the UI reuse step](dev-sop.md#ui-reuse-and-acceptance)
for acceptance. Use [UI-first development](knowledge/ui-first-development.md)
when states need review independently of backend integration.

Keep this guide as the principles owner. The catalog owns composition recipes,
implementation links and recurring-failure checks. Applications own exact tokens
and component APIs. Do not copy these principles into every task or skill.

For local component copies, record the upstream path, reviewed commit (or mark
it unpinned), and intentional differences beside the implementation or in its
catalog entry. On a relevant upstream fix, compare affected behavior and replay
its regression scenario; do not overwrite local product differences blindly.
