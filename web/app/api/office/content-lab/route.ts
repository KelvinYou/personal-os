import path from "node:path";
import { ContentLabError, loadContentLab } from "@/lib/content-lab-server";
import type { LabWriteCommand } from "@/lib/content-lab-write.gen";
import { localWorkRequest, workHeaders as headers } from "@/lib/office-work-http";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  if (!localWorkRequest(request)) return Response.json({ error: { code: "local_only" } }, { status: 403, headers });
  const query = new URL(request.url).searchParams;
  if ([...query.keys()].some(k => k !== "mode") || query.getAll("mode").length > 1 || (query.has("mode") && query.get("mode") !== "demo")) return Response.json({ error: { code: "invalid_request" } }, { status: 400, headers });
  try { return Response.json(await loadContentLab(path.resolve(process.cwd(), ".."), query.get("mode") === "demo"), { headers }); }
  catch { return Response.json({ error: { code: "content_lab_unavailable" } }, { status: 503, headers }); }
}
export async function POST(request: Request) {
  if (!localWorkRequest(request, true)) return Response.json({ error: { code: "local_only" } }, { status: 403, headers });
  if (new URL(request.url).search) return Response.json({ error: { code: "demo_read_only" } }, { status: 403, headers });
  if (!request.headers.get("content-type")?.startsWith("application/json")) return Response.json({ error: { code: "invalid_request" } }, { status: 400, headers });
  try {
    const reader = request.body?.getReader();
    if (!reader) throw new Error();
    const chunks: Uint8Array[] = []; let size = 0;
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > 65536) { await reader.cancel(); return Response.json({ error: { code: "request_too_large" } }, { status: 413, headers }); }
      chunks.push(value);
    }
    const payload = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks))) as LabWriteCommand;
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) throw new Error();
    return Response.json(await loadContentLab(path.resolve(process.cwd(), ".."), false, payload), { headers });
  } catch (error) {
    return Response.json({ error: { code: error instanceof ContentLabError ? error.code : "invalid_request", message: error instanceof ContentLabError ? error.detail : "" } }, { status: error instanceof ContentLabError ? error.status : 400, headers });
  }
}
