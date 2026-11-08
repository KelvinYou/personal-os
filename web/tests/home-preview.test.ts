// Route contracts use a synthetic model; never read the owner's private data.
import assert from "node:assert/strict";
import { test, vi } from "vitest";

const state = vi.hoisted(() => ({
  reads: 0,
  fail: false,
  fragment: '<div id="wyn-home-preview"></div><script type="module">const T = await import("https://cdn.jsdelivr.net/npm/three@0.187.0/build/three.module.js");</script>',
}));
vi.mock("node:fs/promises", () => ({
  default: {},
  readFile: async (name: unknown) => {
    state.reads++;
    if (state.fail) throw new Error("PRIVATE_DIAGNOSTIC");
    return String(name).endsWith(".html") ? state.fragment : "export { Color } from 'three';";
  },
}));

import * as viewer from "@/app/home-design/viewer/route";
import * as engine from "@/app/home-design/three/[asset]/route";
import * as addons from "@/app/home-design/addons/[...module]/route";

const request = (headers: Record<string, string>) => new Request("http://localhost:3000/home-design/viewer", { headers: { host: "localhost:3000", ...headers } });
const asset = (name: string) => ({ params: Promise.resolve({ asset: name }) });

test("local viewer serves the private model without remote dependencies or caching", async () => {
  const response = await viewer.GET(request({}));
  assert.equal(response.status, 200);
  assert.match(response.headers.get("cache-control") ?? "", /private, no-store/);
  assert.match(response.headers.get("content-security-policy") ?? "", /frame-ancestors 'self'/);
  const html = await response.text();
  assert.match(html, /\/home-design\/three\/three.module.js/);
  assert.doesNotMatch(html, /https:\/\/cdn/);
  assert.match(html, /home-preview-ready/);
  assert.match(html, /home-preview-error/);
});

test("cross-origin, cross-site and rebinding requests cannot read the private source", async () => {
  const before = state.reads;
  for (const headers of <Record<string, string>[]>[{ origin: "https://example.invalid" }, { host: "example.invalid" }, { "sec-fetch-site": "cross-site" }]) {
    assert.equal((await viewer.GET(request(headers))).status, 403);
    assert.equal((await engine.GET(request(headers), asset("three.core.js"))).status, 403);
  }
  assert.equal(state.reads, before);
});

test("dependency route allows only the two required module filenames", async () => {
  for (const name of ["three.module.js", "three.core.js"]) {
    const response = await engine.GET(request({}), asset(name));
    assert.equal(response.status, 200);
    assert.match(response.headers.get("content-type") ?? "", /javascript/);
  }
  const before = state.reads;
  assert.equal((await engine.GET(request({}), asset("../../private.txt"))).status, 404);
  assert.equal(state.reads, before);
});

test("missing model reports failure rather than success or private diagnostics", async () => {
  state.fail = true;
  try {
    const response = await viewer.GET(request({}));
    assert.equal(response.status, 503);
    const html = await response.text();
    assert.match(html, /home-preview-error/);
    assert.doesNotMatch(html, /PRIVATE_DIAGNOSTIC/);
  } finally { state.fail = false; }
});

test("remote model scripts are rejected", async () => {
  const original = state.fragment;
  state.fragment += '<script src="https://example.invalid/code.js"></script>';
  try { assert.equal((await viewer.GET(request({}))).status, 503); }
  finally { state.fragment = original; }
});


test("HQ addons use only local engine imports and reject arbitrary paths before reading", async () => {
  const context = (name: string) => ({ params: Promise.resolve({ module: name.split("/") }) });
  const response = await addons.GET(request({}), context("postprocessing/GTAOPass.js"));
  assert.equal(response.status, 200);
  const source = await response.text();
  assert.match(source, /from '\/home-design\/three\/three.module.js'/);
  const before = state.reads;
  for (const name of ["../../private.txt", "loaders/../private.txt", "loaders/GLTFLoader.js", "", "postprocessing/GTAOPass.js/extra"]) {
    assert.equal((await addons.GET(request({}), context(name))).status, 404);
  }
  assert.equal((await addons.GET(request({origin:"https://example.invalid"}), context("postprocessing/GTAOPass.js"))).status, 403);
  assert.equal((await addons.GET(request({host:"example.invalid"}), context("postprocessing/GTAOPass.js"))).status, 403);
  assert.equal(state.reads, before);
});
