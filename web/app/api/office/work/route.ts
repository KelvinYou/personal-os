import path from "node:path";
import { OfficeWorkStore, WorkError } from "@/lib/office-work-store";
import { localWorkRequest, workHeaders as headers } from "@/lib/office-work-http";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const store = () => new OfficeWorkStore(path.resolve(process.cwd(), ".."));
const error = (code: string, status: number) => Response.json({ error: { code } }, { status, headers });
export async function GET(request: Request) {
  if (!localWorkRequest(request)) return error("local_only", 403);
  try { return Response.json(store().list(), { headers }); }
  catch (cause) { return error(cause instanceof WorkError ? cause.code : "history_unavailable", cause instanceof WorkError ? cause.status : 503); }
}
export async function POST(request: Request) {
  if (!localWorkRequest(request, true)) return error("local_only", 403);
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) return error("json_required", 415);
  try {
    const reader = request.body?.getReader();
    if (!reader) return error("invalid_review", 400);
    const chunks: Uint8Array[] = []; let size = 0;
    try {
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        size += value.byteLength;
        if (size > 4096) { await reader.cancel(); return error("request_too_large", 413); }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    let value;
    try { value = JSON.parse(Buffer.concat(chunks).toString("utf8")); } catch { return error("invalid_review", 400); }
    if (!value || value.action !== "review" || Object.keys(value).sort().join(",") !== "action,review,revision,task_id"
      || typeof value.task_id !== "string" || !value.task_id || value.task_id.length > 100 || !Number.isSafeInteger(value.revision)
      || !["accepted", "rework"].includes(value.review)) return error("invalid_review", 400);
    return Response.json(store().review(value.task_id, value.revision, value.review), { headers });
  } catch (cause) { return error(cause instanceof WorkError ? cause.code : "history_unavailable", cause instanceof WorkError ? cause.status : 503); }
}
