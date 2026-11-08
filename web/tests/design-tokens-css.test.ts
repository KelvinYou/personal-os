import assert from "node:assert/strict";
import { test } from "vitest";
import { tokenRule } from "@/lib/design-tokens-css";

const globals = `@layer base {
  :root { --background: 0 0% 100%; --border: 30 9% 87%; --radius: 8px; --brand-fill: #00f0ff; }
  .dark { --background: 24 5% 9%; }
}`;

test("tokens become light-dark colours under --ds-*", () => {
  const rule = tokenRule([globals]);
  assert.match(rule, /--ds-background:light-dark\(hsl\(0 0% 100%\),hsl\(24 5% 9%\)\)/);
  assert.match(rule, /--ds-border:hsl\(30 9% 87%\)/); // no dark value: same in both themes
  assert.match(rule, /--ds-brand-fill:#00f0ff/);
  assert.ok(!rule.includes("--ds-radius")); // non-colour tokens are skipped
});

test("later stylesheets override earlier ones", () => {
  const rule = tokenRule([globals, ":root { --border: 0 0% 50%; }"]);
  assert.match(rule, /--ds-border:hsl\(0 0% 50%\)/);
});

test("unreadable or empty token source yields no rule", () => {
  assert.equal(tokenRule(["export { Color } from 'three';"]), "");
});
