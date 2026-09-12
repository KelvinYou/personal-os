# Renderer contracts

Look up the target's family before applying any target-specific portability
rule. Identify the family with the discovery commands in `SKILL.md` Step 1.

## Contents

- [A. GitHub server-side Mermaid](#a-github-server-side-mermaid)
- [B. Client-side mermaid.js in an app](#b-client-side-mermaidjs-in-an-app)
- [C. Mermaid inside MDX or JSX-flavored docs](#c-mermaid-inside-mdx-or-jsx-flavored-docs)
- [D. Static site generators](#d-static-site-generators)
- [E. Generated Mermaid, model-owned](#e-generated-mermaid-model-owned)
- [Choosing a gate](#choosing-a-gate)

---

## A. GitHub server-side Mermaid

**Identify:** a ```` ```mermaid ```` fence in a `.md` file that is read on
github.com — README, docs, architecture files. No app code renders it.

| Property | Contract |
| --- | --- |
| Version | Pinned by GitHub; not controlled by your repo. Lags upstream. |
| `<br/>` in labels | Supported. The safe choice. |
| `\n` in labels | **Renders literally.** Never use. |
| Richer HTML (`<b>`, `<i>`) | Unreliable. Avoid unless verified on the live page. |
| Undeclared `classDef` | Renders unstyled, no error. |
| Failure mode | Diagram is replaced by an error box, or renders subtly wrong. |

**Gate:** none exists server-side. A repo-local lint is the only gate. Newer
Mermaid syntax that works in a local preview can fail here — verify on the
rendered page for anything beyond basic flowchart syntax.

---

## B. Client-side mermaid.js in an app

**Identify:** `mermaid` in `package.json`; a call to `mermaid.initialize` in app
source.

| Property | Contract |
| --- | --- |
| Version | Whatever the lockfile pins. Check it — v10 and v11 differ. |
| `securityLevel: "strict"` | **Strips or fails on HTML in labels.** `<br/>` only. |
| `securityLevel: "loose"` | Richer HTML passes, but do not rely on it without a test. |
| Failure mode | Runtime. Often hidden behind a source-code or error fallback. |

**The fallback trap.** A wrapper component that catches a parse error and
displays raw source keeps the page loading, so a broken diagram ships silently
and is discovered by a reader, not by CI. Find the fallback before assuming a
diagram is fine:

```bash
grep -rn 'catch\|fallback' --include='*mermaid*' src app components 2>/dev/null
```

**Gate:** build-time parse check, or a lint over the source files. A build that
succeeds proves nothing about diagram validity.

---

## C. Mermaid inside MDX or JSX-flavored docs

**Identify:** ```` ```mermaid ```` fences in `.mdx` files.

Everything in family B applies, plus:

- **A checker defaulting to `*.md` silently misses every diagram here.** This is
  the single most common way an MDX repo ends up with a gate that reports clean
  while checking nothing. Pass `--ext md,mdx` or explicit paths.
- MDX may interpret braces and JSX-like syntax inside the fence depending on the
  toolchain version. Verify that a label containing `{` or `<` survives the
  build.

---

## D. Static site generators

**Identify:** Docusaurus, VitePress, MkDocs, Astro, or similar, with a Mermaid
plugin configured.

- The plugin pins its own Mermaid version, independent of any `mermaid` entry in
  `package.json`. Read the plugin config, not the top-level dependency.
- Most fail the **build** on a diagram error, which makes the build itself an
  adequate gate. Confirm this rather than assuming it — some render diagrams
  client-side and inherit family B's runtime failure mode instead.
- Theme variables are usually set in site config, not per-diagram. Do not
  hand-set colors in a diagram that a site theme already governs.

---

## E. Generated Mermaid, model-owned

**Identify:** the Mermaid block carries a "generated, do not edit" marker, or a
generator script writes the file.

| Property | Contract |
| --- | --- |
| Editable | **No.** Edit the model; regenerate. |
| Label markup | Set by the generator. Read the generator, not neighbouring diagrams. |
| Gate | The generator's own `--check` mode, run in CI. |

A generator may legitimately emit markup that a hand-written diagram in the same
repository must avoid, because the generator targets a renderer that accepts it.
**Never copy label markup from a generated block into a hand-written one.** This
is the specific mistake the "do not generalize one target's tolerance" rule in
`SKILL.md` exists to prevent.

---

## Choosing a gate

| Situation | Gate |
| --- | --- |
| Markdown read on GitHub | repo-local lint in `make test` or CI |
| Client-side render, any framework | lint plus a build-time parse check |
| MDX | same, with `--ext md,mdx` |
| SSG that fails the build | the build, once verified it actually fails |
| Generated | generator `--check` in CI |

Two constraints hold in every case:

1. The gate is a **repo-local file**. CI cannot reach across a repository or
   submodule boundary to a checker living elsewhere.
2. A parse gate alone is insufficient. The highest-frequency failures — literal
   `\n` in a label, a class with no `classDef` — are *syntactically valid*
   Mermaid. Rule checking is what catches them, which is why
   `scripts/check_mermaid.py` is a lint rather than a parser wrapper.
