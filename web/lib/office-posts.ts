// Server-only filesystem adapter. Never import this module into a client component.
import path from "node:path";
import { closeSync, constants, fstatSync, openSync, readSync, readdirSync, realpathSync, statSync } from "node:fs";
import type { PostCollection, PostDetail } from "./office-posts-contract";

export class PostError extends Error {
  constructor(public code: string, public status = 503) { super(code); }
}
const validId = (id: string) => id.length <= 180 && /^[a-z0-9][a-z0-9_-]*-\d{4}-\d{2}-\d{2}$/.test(id);
const validImage = (name: string) => name.length <= 180 && /^\d{2,}[-_][a-zA-Z0-9_-]+\.(png|jpe?g|webp)$/i.test(name);
// Technical allocation ceilings, independent of personal operating thresholds.
const TEXT_BYTES = 512 * 1024, IMAGE_BYTES = 32 * 1024 * 1024, POST_LIMIT = 500;
function confined(base: string, candidate: string) {
  const target = realpathSync(candidate), relative = path.relative(base, target);
  if (!relative || relative.startsWith(`..${path.sep}`) || relative === ".." || path.isAbsolute(relative)) throw new PostError("post_not_found", 404);
  return target;
}
function readBounded(file: string, limit: number) {
  const fd = openSync(file, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const stat = fstatSync(fd);
    if (!stat.isFile() || stat.size > limit) throw new PostError("post_file_unsupported", 422);
    const buffer = Buffer.alloc(Math.min(stat.size + 1, limit + 1));
    let count = 0;
    while (count < buffer.length) { const size = readSync(fd, buffer, count, buffer.length - count, null); if (!size) break; count += size; }
    if (count > limit || count > stat.size) throw new PostError("post_file_unsupported", 422);
    return buffer.subarray(0, count);
  } finally { closeSync(fd); }
}
export class OfficePosts {
  private base() {
    try { const base = realpathSync(path.join(this.root, "data/posts")); if (!statSync(base).isDirectory()) throw new Error(); return base; }
    catch { throw new PostError("posts_unavailable"); }
  }
  constructor(private root: string) {}
  private folder(id: string) {
    if (!validId(id)) throw new PostError("invalid_post", 400);
    try { const base = this.base(), target = confined(base, path.join(base, id)); if (!statSync(target).isDirectory()) throw new Error(); return target; }
    catch (cause) { if (cause instanceof PostError) throw cause; throw new PostError("post_not_found", 404); }
  }
  private text(folder: string, name: string, optional = false): string | null {
    try {
      const bytes = readBounded(confined(folder, path.join(folder, name)), TEXT_BYTES);
      if (bytes.includes(0)) throw new PostError("post_file_unsupported", 422);
      return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    } catch (cause) {
      if (optional && (cause as NodeJS.ErrnoException).code === "ENOENT") return null;
      if (cause instanceof PostError) throw cause;
      throw new PostError("post_file_unavailable", 404);
    }
  }
  private images(folder: string, id: string) {
    try {
      const directory = confined(folder, path.join(folder, "images"));
      return readdirSync(directory).filter(validImage).sort((a, b) => a.localeCompare(b, "en", { numeric: true })).filter(name => {
        const file = confined(directory, path.join(directory, name));
        return statSync(file).isFile();
      }).map(name => ({ name, url: `/api/office/posts/image?id=${encodeURIComponent(id)}&name=${encodeURIComponent(name)}` }));
    } catch (cause) {
      if ((cause as NodeJS.ErrnoException).code === "ENOENT") return [];
      if (cause instanceof PostError) throw cause;
      throw new PostError("post_file_unavailable", 404);
    }
  }
  private summary(id: string, notes: string, images: { url: string }[], copy: string | null) {
    const publishTitle = copy?.match(/^(?:【标题】|Title:)\s*\r?\n?([^\r\n]+)/im)?.[1];
    const sectionTitle = notes.match(/^##\s+Title\s*\r?\n+([^\r\n]+)/im)?.[1];
    const heading = notes.match(/^#\s+(.+)$/m)?.[1];
    return { id, title: (publishTitle ?? sectionTitle ?? heading ?? id).trim(), date: id.slice(-10), imageCount: images.length, cover: images[0]?.url ?? null };
  }
  list(): PostCollection {
    const base = this.base();
    try {
      const ids = readdirSync(base).filter(validId).sort((a, b) => b.slice(-10).localeCompare(a.slice(-10)) || a.localeCompare(b));
      let partial = ids.length > POST_LIMIT;
      const posts = ids.slice(0, POST_LIMIT).flatMap(id => {
        try { const folder = this.folder(id), notes = this.text(folder, "post.md")!; return [this.summary(id, notes, this.images(folder, id), this.text(folder, "publish.txt", true))]; }
        catch { partial = true; return []; }
      });
      return { posts, partial };
    } catch { throw new PostError("posts_unavailable"); }
  }
  get(id: string): PostDetail {
    const folder = this.folder(id), notes = this.text(folder, "post.md")!, images = this.images(folder, id), copy = this.text(folder, "publish.txt", true);
    return { ...this.summary(id, notes, images, copy), images, notes, copy, verification: this.text(folder, "verification.md", true) };
  }
  image(id: string, name: string) {
    if (!validImage(name)) throw new PostError("invalid_image", 400);
    try {
      const folder = this.folder(id), directory = confined(folder, path.join(folder, "images"));
      const bytes = readBounded(confined(directory, path.join(directory, name)), IMAGE_BYTES);
      const png = bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
      const jpeg = bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
      const webp = bytes.subarray(0, 4).toString() === "RIFF" && bytes.subarray(8, 12).toString() === "WEBP";
      const type = /\.png$/i.test(name) && png ? "image/png" : /\.jpe?g$/i.test(name) && jpeg ? "image/jpeg" : /\.webp$/i.test(name) && webp ? "image/webp" : null;
      if (!type) throw new PostError("image_unsupported", 422);
      return { bytes, type };
    } catch (cause) { if (cause instanceof PostError) throw cause; throw new PostError("image_unavailable", 404); }
  }
}
