import { readFile } from "node:fs/promises";
import path from "node:path";
import { isLocalPreviewRequest } from "@/lib/home-preview";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ asset: string }> }) {
  if (!isLocalPreviewRequest(request)) return new Response("Local dashboard access only.", { status: 403 });
  const { asset } = await context.params;
  if (asset !== "three.module.js" && asset !== "three.core.js") return new Response("Not found", { status: 404 });
  try {
    return new Response(await readFile(path.join(process.cwd(), "node_modules/three/build", asset), "utf8"), { headers: {
      "Content-Type": "text/javascript; charset=utf-8", "Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff",
    } });
  } catch { return new Response("Local 3D engine unavailable.", { status: 503 }); }
}
