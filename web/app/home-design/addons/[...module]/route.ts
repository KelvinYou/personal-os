import { readFile } from "node:fs/promises";
import path from "node:path";
import { isLocalPreviewRequest } from "@/lib/home-preview";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// Dependency closure of HDRLoader, RoundedBoxGeometry and the HQ AO pipeline.
// Pinned to installed Three.js 0.187.0. No arbitrary package or filesystem reads.
const allowed = new Set(["geometries/RoundedBoxGeometry.js", "loaders/HDRLoader.js", "math/SimplexNoise.js", "postprocessing/EffectComposer.js", "postprocessing/GTAOPass.js", "postprocessing/MaskPass.js", "postprocessing/OutputPass.js", "postprocessing/Pass.js", "postprocessing/RenderPass.js", "postprocessing/ShaderPass.js", "shaders/CopyShader.js", "shaders/GTAOShader.js", "shaders/OutputShader.js", "shaders/PoissonDenoiseShader.js"]);

export async function GET(request: Request, context: { params: Promise<{ module: string[] }> }) {
  if (!isLocalPreviewRequest(request)) return new Response("Local dashboard access only.", { status: 403 });
  const { module: parts } = await context.params;
  const name = parts.join("/");
  if (!allowed.has(name)) return new Response("Not found", { status: 404 });
  try {
    const source = await readFile(path.join(process.cwd(), "node_modules/three/examples/jsm", name), "utf8");
    const local = source.replace(/(from\s*["'])three(["'])/g, "$1/home-design/three/three.module.js$2");
    return new Response(local, { headers: { "Content-Type": "text/javascript; charset=utf-8", "Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff" } });
  } catch { return new Response("Local 3D addon unavailable.", { status: 503 }); }
}
