# Interface design guide

[Status: OK] Active shared guidance · Updated: 2026-10-04

Use this guide when creating or reviewing Personal-OS pages, dashboards and HTML artifacts. It owns shared design principles; each application or skill owns its components and assets. Personal preferences remain in the owner's private reference files.

## Five principles

1. **Make the purpose and next action clear.** Lead with what the reader needs to understand or do. Use typography, alignment and grouped spacing to establish hierarchy. Choose the layout for the content: tables for numerical comparison, timelines for sequences, cards when items benefit from separate context.
2. **Keep information trustworthy.** Preserve amounts, dates, units, uncertainty and consequential warnings while simplifying the presentation. Use labels alongside semantic colours. Keep blockers visible; details can hold supporting explanation. A frequent or positive signal should not become a warning merely because its number is large.
3. **Let material support content.** For Apple-inspired interfaces, concentrate Liquid Glass in navigation and controls. Keep dense text and data on readable, near-opaque surfaces. A useful glass effect combines translucency, blur, edge highlights and restrained depth; the interface should still work with glass turned off. This web treatment is an approximation of the native material. [Apple's materials guidance](https://developer.apple.com/design/human-interface-guidelines/materials) places Liquid Glass in the functional layer above content.
4. **Make the whole experience usable.** Adapt the composition to small screens and enlarged text. Provide labelled controls, visible keyboard focus and readable contrast. Respect reduced motion and transparency; offer a solid fallback when glass is used. Keep necessary two-dimensional content, such as a wide table, in its own scroll region where practical. [W3C reflow guidance](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) explains that distinction.
5. **Reuse what already works.** Start with the product's existing components and assets. Keep recurring values in local tokens rather than scattered overrides. Extract shared code when repeated use demonstrates its value; a principles document does not require a new component library. [Material's foundations](https://m3.material.io/foundations/) describe tokens as reusable style values across design and implementation.

## Flexible defaults

For a new utility page without an established visual identity, start with system typography, calm neutral surfaces, clear numeric alignment, comfortable spacing and restrained accents. Use glass where it makes navigation distinct. Imagery, richer colour, motion or different typography can be useful when they serve the page's purpose.

For Personal-OS pages and shareable HTML, use the local web dashboard as the visual baseline unless the user requests another direction. Consistency includes palette, typography scale, spacing, card treatment, navigation and appearance controls—not just matching icons. Adapt the content layout to its purpose while keeping that visual family. Compare the actual artifact with the dashboard at the same viewport and browser zoom before calling it aligned.

These are starting points, not a fixed template or a requirement to restyle every product. An explicit user brief and the host product's design language take precedence. Choose a different treatment when the content, platform or reader benefits; briefly explain a material departure when it affects review. Ordinary design choices do not need an approval step.

## Icons and shareable HTML

Use [Lucide](https://lucide.dev/) as the default UI icon family when the host product has no established set. Choose a small consistent subset and reuse the same icon for the same meaning. Keep meaningful labels visible; decorative SVGs use `aria-hidden="true"`, and icon-only controls need an accessible name. Preserve the upstream licence when distributing icon assets. [Lucide provides SVG assets](https://lucide.dev/guide/packages/lucide-static) suitable for embedding directly.

Tailwind is a useful authoring option, especially in the existing dashboard; plain CSS remains suitable for standalone templates. The shared design comes from principles and reusable values, not a mandatory framework migration.

A shareable HTML artifact should arrive ready to open: embed only the selected SVGs, final CSS in `<style>`, and any optional interaction code in the file. When using Tailwind, compile the final content to static CSS before embedding it; the recipient needs no Node.js, build step or local server. [Tailwind's CLI](https://tailwindcss.com/docs/installation/tailwind-cli) generates static CSS; its [Play CDN](https://tailwindcss.com/docs/installation/play-cdn) is intended for development.

Keep reading and essential navigation available without JavaScript or a network connection. Bundle images if they are needed to understand the artifact; ordinary map or booking links may remain external. Before sharing, open the delivered file itself from disk with the network disabled. Some messaging apps restrict HTML previews; direct opening means a browser can render the file, not that every chat app supports it. Use a PDF or hosted view if the recipient's channel cannot open HTML.

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
| Visual baseline and dashboard implementation | [web/app/globals.css](../web/app/globals.css) and [web/components/](../web/components/) |
| Personal taste and task-specific exceptions | Owner instructions and optional private reference files |

Add guidance when it resolves a recurring design failure or a repeated need. Prefer improving an existing principle to adding another rule. Leave exact colours, sizes, class names and domain-specific behaviour with their implementation owner.
