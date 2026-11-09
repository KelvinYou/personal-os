import { readFile } from "node:fs/promises";
import path from "node:path";
import { isLocalPreviewRequest } from "@/lib/home-preview";
import { characterProfile, characterWardrobe } from "@/lib/office-character";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Serves the shared 3D modules to the standalone home viewer. Fixed allowlist; no other file is readable.
const allowed = new Set(["scene-standard.mjs", "scene-floor.mjs", "character-builder.mjs", "kenney-mini-data.mjs"]);

export async function GET(request: Request, context: { params: Promise<{ name: string }> }) {
  if (!isLocalPreviewRequest(request)) return new Response("Local dashboard access only.", { status: 403 });
  const { name } = await context.params;
  if (name === "kelvin-look.json") {
    // The office owns this identity; the home viewer draws the same person.
    const look = characterWardrobe("kelvin.ai", undefined, true);
    return Response.json({ profile: { ...characterProfile("kelvin.ai"), feminine: false, shirt: look.shirt }, look }, { headers: { "Cache-Control": "private, no-cache" } });
  }
  if (!allowed.has(name)) return new Response("Not found", { status: 404 });
  try {
    return new Response(await readFile(path.join(process.cwd(), "lib", name), "utf8"), { headers: {
      "Content-Type": "text/javascript; charset=utf-8", "Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff",
    } });
  } catch { return new Response("Shared 3D module unavailable.", { status: 503 }); }
}
