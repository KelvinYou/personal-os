import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, test, vi } from "vitest";
import { OfficePosts, PostError } from "@/lib/office-posts";
import { GET } from "@/app/api/office/posts/route";
import { GET as imageGET } from "@/app/api/office/posts/image/route";

const roots: string[] = [];
const id = "example-2026-01-02";
const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=", "base64");
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "office-posts-")); roots.push(root);
  const folder = path.join(root, "data/posts", id);
  fs.mkdirSync(path.join(folder, "images"), { recursive: true });
  fs.writeFileSync(path.join(folder, "post.md"), "# Internal heading\n\n## Title\n\nSynthetic carousel\n\n## Sources\nLiteral <script>unsafe()</script>");
  fs.writeFileSync(path.join(folder, "publish.txt"), "Synthetic publication copy");
  for (const name of ["10-end.png", "02-middle.png", "01-cover.png"]) fs.writeFileSync(path.join(folder, "images", name), png);
  fs.writeFileSync(path.join(folder, "images/source.png"), png);
  return { root, folder, store: new OfficePosts(root) };
}
afterEach(() => { vi.restoreAllMocks(); for (const root of roots.splice(0)) fs.rmSync(root, { force: true, recursive: true }); });

test("existing folder layout gives ordered final images, title, literal notes and nullable optional text", () => {
  const { store, folder } = fixture();
  const value = store.get(id);
  assert.equal(value.title, "Synthetic carousel"); assert.equal(value.date, "2026-01-02");
  assert.deepEqual(value.images.map(image => image.name), ["01-cover.png", "02-middle.png", "10-end.png"]);
  assert.equal(value.verification, null); assert.match(value.notes, /<script>/);
  assert.equal(store.list().posts[0].imageCount, 3);
  assert.equal(store.image(id, "01-cover.png").type, "image/png");
  fs.writeFileSync(path.join(folder, "publish.txt"), "【标题】\nPublication title\n\n【正文】\nCopy");
  assert.equal(store.get(id).title, "Publication title");
  assert.equal(store.list().posts[0].title, "Publication title");
  fs.rmSync(path.join(folder, "publish.txt")); fs.rmSync(path.join(folder, "images"), { recursive: true });
  assert.equal(store.get(id).copy, null); assert.deepEqual(store.get(id).images, []);
});
test("missing private source is unavailable; empty source and unreadable individual posts stay distinct", () => {
  const { root, folder, store } = fixture();
  fs.mkdirSync(path.join(root, "data/posts/broken-2026-01-01"));
  assert.equal(store.list().partial, true); assert.equal(store.list().posts.length, 1);
  fs.rmSync(path.join(root, "data/posts/broken-2026-01-01"), { recursive: true });
  fs.rmSync(folder, { recursive: true });
  assert.deepEqual(store.list(), { posts: [], partial: false });
  fs.rmSync(path.join(root, "data/posts"), { recursive: true });
  assert.throws(() => store.list(), (e: unknown) => e instanceof PostError && e.code === "posts_unavailable");
});
test("traversal, unapproved files and symlinks cannot escape the selected source", () => {
  const { root, folder, store } = fixture();
  const outside = path.join(root, "secret.png"); fs.writeFileSync(outside, png);
  assert.throws(() => store.get("../../finance"));
  for (const name of ["../../secret.png", "source.png", "01-secret.svg", "../post.md"]) assert.throws(() => store.image(id, name));
  fs.symlinkSync(outside, path.join(folder, "images/03-secret.png"));
  assert.throws(() => store.image(id, "03-secret.png"));
  assert.equal(store.list().partial, true);
  fs.rmSync(path.join(folder, "images/03-secret.png"));
  fs.symlinkSync(root, path.join(root, "data/posts/escape-2026-01-03"));
  assert.throws(() => store.get("escape-2026-01-03"));
  fs.rmSync(path.join(folder, "post.md")); fs.symlinkSync(outside, path.join(folder, "post.md"));
  assert.throws(() => store.get(id));
});
test("bounded text and image reads reject oversized files, directories and wrong signatures", () => {
  const { folder, store } = fixture();
  fs.writeFileSync(path.join(folder, "images/04-fake.png"), "<svg>not a PNG</svg>");
  assert.throws(() => store.image(id, "04-fake.png"), (e: unknown) => e instanceof PostError && e.status === 422);
  fs.writeFileSync(path.join(folder, "post.md"), "x".repeat(512 * 1024 + 1));
  assert.throws(() => store.get(id));
  const large = path.join(folder, "images/05-huge.png"); fs.writeFileSync(large, png); fs.truncateSync(large, 32 * 1024 * 1024 + 1);
  assert.throws(() => store.image(id, "05-huge.png"));
});
const request = (query = "", headers: Record<string, string> = {}) => new Request(`http://localhost:3000/api/office/posts${query}`, { headers: { host: "localhost:3000", ...headers } });
test("route guards reject cross-origin, rebinding, duplicate and arbitrary path queries before source access", async () => {
  const list = vi.spyOn(OfficePosts.prototype, "list").mockImplementation(() => { throw new Error("must not read"); });
  for (const route of [GET, imageGET]) {
    assert.equal((await route(request("", { origin: "https://example.invalid" }))).status, 403);
    assert.equal((await route(request("", { host: "example.invalid" }))).status, 403);
    assert.equal((await route(request("", { "sec-fetch-site": "cross-site" }))).status, 403);
  }
  assert.equal((await GET(request("?id=a&id=b"))).status, 400);
  assert.equal((await GET(request("?path=/secret"))).status, 400);
  assert.equal((await imageGET(request("?id=a&name=a&name=b"))).status, 400);
  assert.equal(list.mock.calls.length, 0);
});
test("route responses are private and fixed errors do not disclose diagnostics", async () => {
  vi.spyOn(OfficePosts.prototype, "list").mockReturnValue({ posts: [], partial: false });
  let response = await GET(request());
  assert.equal(response.status, 200); assert.match(response.headers.get("cache-control")!, /private, no-store/);
  vi.spyOn(OfficePosts.prototype, "image").mockReturnValue({ bytes: png, type: "image/png" });
  response = await imageGET(request(`?id=${id}&name=01-cover.png`));
  assert.equal(response.status, 200); assert.equal(response.headers.get("content-type"), "image/png"); assert.equal(response.headers.get("cross-origin-resource-policy"), "same-origin");
  vi.spyOn(OfficePosts.prototype, "get").mockImplementation(() => { throw new Error("PRIVATE_DIAGNOSTIC_PATH"); });
  response = await GET(request(`?id=${id}`)); assert.equal(response.status, 503); assert.doesNotMatch(await response.text(), /PRIVATE_DIAGNOSTIC/);
});
