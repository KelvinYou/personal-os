import { readFile } from "node:fs/promises";
import path from "node:path";

/**
 * Standalone pages (the home 3D viewer iframe) cannot load globals.css, so they used to carry a
 * private palette. This derives colour custom properties (`--ds-<token>`, full colour values using
 * light-dark()) from the real token blocks so those pages follow the design system.
 */
const files = ["app/globals.css", "app/design-controls.css"].map(name => path.resolve(process.cwd(), name));
const triple = /^[\d.]+\s+[\d.]+%\s+[\d.]+%$/;

function block(css: string, selector: RegExp): Record<string, string> {
  const out: Record<string, string> = {};
  for (const match of css.matchAll(new RegExp(`(?:^|[\\s}])${selector.source}\\s*\\{([^}]*)\\}`, "g"))) {
    const body = match[1].replace(/\/\*[\s\S]*?\*\//g, "");
    for (const [, name, value] of body.matchAll(/--([\w-]+):\s*([^;]+);/g)) out[name] = value.trim();
  }
  return out;
}

const colour = (value: string) => (triple.test(value) ? `hsl(${value})` : /^#[0-9a-f]{3,8}$/i.test(value) ? value : null);

/** Pure: build the `:root` rule from token CSS (exported for tests). */
export function tokenRule(sources: string[]): string {
  const light: Record<string, string> = {};
  const dark: Record<string, string> = {};
  for (const css of sources) {
    Object.assign(light, block(css, /:root/));
    Object.assign(dark, block(css, /\.dark/));
  }
  const decls: string[] = [];
  for (const [name, value] of Object.entries(light)) {
    const l = colour(value);
    if (!l) continue;
    const d = colour(dark[name] ?? value) ?? l;
    decls.push(`--ds-${name}:${l === d ? l : `light-dark(${l},${d})`}`);
  }
  return decls.length ? `:root{${decls.join(";")}}` : "";
}

export async function designTokenRule(): Promise<string> {
  try {
    return tokenRule(await Promise.all(files.map(file => readFile(file, "utf8"))));
  } catch {
    return "";
  }
}
