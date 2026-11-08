import assert from "node:assert/strict";
import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { test } from "vitest";
import { Money, Private, PrivacyProvider } from "@/components/shared/privacy";

test("amounts are masked by default, inside a provider and outside one", () => {
  for (const html of [
    renderToStaticMarkup(h(PrivacyProvider, null, h(Money, { value: 12345.67 }))),
    renderToStaticMarkup(h(Money, { value: 12345.67 })),
    renderToStaticMarkup(h(PrivacyProvider, null, h(Private, null, "USD 318.14"))),
  ]) {
    assert.doesNotMatch(html, /12,345|318\.14|RM/);
    assert.match(html, /••••••/);
    assert.match(html, /Amount hidden/);
  }
});

test("mask is identical for every value so it does not leak magnitude", () => {
  assert.equal(renderToStaticMarkup(h(Money, { value: 5 })), renderToStaticMarkup(h(Money, { value: 9_999_999.99 })));
});
