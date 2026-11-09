import { WorkbenchError, workbenchCommand } from "@/lib/finance-workbench-server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "private, no-store, max-age=0", "Vary": "Origin", "X-Content-Type-Options": "nosniff" };
function permitted(request: Request, write = false) {
  const host = request.headers.get("host") ?? "", origin = request.headers.get("origin");
  return /^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(host) && request.headers.get("sec-fetch-site") !== "cross-site"
    && (!origin ? !write : ["http://", "https://"].some(protocol => origin === protocol + host));
}
const error = (code: string, status: number) => Response.json({ error: { code } }, { status, headers });
const failed = (cause: unknown) => error(cause instanceof WorkbenchError ? cause.code : "workbench_unavailable", cause instanceof WorkbenchError ? cause.status : 503);
export async function GET(request: Request) {
  if (!permitted(request)) return error("local_only", 403);
  try { return Response.json(await workbenchCommand("read", undefined, new URL(request.url).searchParams.get("mode") === "demo"), { headers }); }
  catch (cause) { return failed(cause); }
}
export async function POST(request: Request) {
  if (!permitted(request, true)) return error("same_origin_required", 403);
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) return error("json_required", 415);
  try {
    const reader = request.body?.getReader(); if (!reader) return error("invalid_payload", 400);
    let size = 0; const chunks: Uint8Array[] = [];
    try {
      while (true) { const { value, done } = await reader.read(); if (done) break; size += value.byteLength; if (size > 65536) { await reader.cancel(); return error("payload_too_large", 413); } chunks.push(value); }
    } finally { reader.releaseLock(); }
    let payload: unknown;
    try { payload = JSON.parse(Buffer.concat(chunks).toString("utf8")); } catch { return error("invalid_payload", 400); }
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return error("invalid_payload", 400);
    return Response.json(await workbenchCommand("apply", payload, new URL(request.url).searchParams.get("mode") === "demo"), { headers });
  } catch (cause) { return failed(cause); }
}
