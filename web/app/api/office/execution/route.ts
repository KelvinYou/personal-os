import { execution, ExecutionError } from "@/lib/office-execution";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const revalidate = 0;
const headers = { "Cache-Control": "private, no-store, max-age=0", "Vary": "Origin", "X-Content-Type-Options": "nosniff" };
const error = (code: string, status: number) => Response.json({ error: { code } }, { status, headers });
function local(request: Request, write = false) {
  const host = request.headers.get("host") ?? "";
  const origin = request.headers.get("origin");
  return /^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(host)
    && (!write && !origin || origin === `http://${host}` || origin === `https://${host}`)
    && request.headers.get("sec-fetch-site") !== "cross-site";
}
export async function GET(request: Request) {
  if (!local(request)) return error("local_only", 403);
  try { return Response.json((await execution()).snapshot(), { headers }); }
  catch (cause) { return error(cause instanceof ExecutionError ? cause.code : "execution_unavailable", 503); }
}
export async function POST(request: Request) {
  if (!local(request, true)) return error("local_only", 403);
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) return error("json_required", 415);
  try {
    // Fixed transport ceiling independent of the configured prompt budget.
    const reader = request.body?.getReader();
    if (!reader) return error("invalid_request", 400);
    const chunks: Uint8Array[] = []; let size = 0;
    while (true) {
      const { value, done } = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > 512 * 1024) { await reader.cancel(); return error("request_too_large", 413); }
      chunks.push(value);
    }
    let payload;
    try { payload = JSON.parse(Buffer.concat(chunks).toString("utf8")); }
    catch { return error("invalid_request", 400); }
    if (!payload || typeof payload !== "object" || Array.isArray(payload) || typeof payload.request_id !== "string") return error("invalid_request", 400);
    const fields: Record<string, string[]> = { send: ["action", "request_id", "text", "collaboration", "skill_id"], stop: ["action", "request_id"], reset: ["action", "request_id"], answer: ["action", "request_id", "input_request_id", "answers"] };
    const allowed = Object.hasOwn(fields, payload.action) ? fields[payload.action] : undefined;
    if (!allowed || Object.keys(payload).some(k => !allowed.includes(k)) || allowed.some(k => !["collaboration", "skill_id"].includes(k) && !Object.hasOwn(payload, k))) return error("invalid_request", 400);
    if (payload.collaboration !== undefined && !["solo", "team"].includes(payload.collaboration)) return error("invalid_collaboration", 400);
    const client = await execution();
    let result;
    if (payload.action === "send") result = await client.send(payload.request_id, payload.text, payload.collaboration, payload.skill_id);
    if (payload.action === "stop") result = await client.stop(payload.request_id);
    if (payload.action === "reset") result = client.reset(payload.request_id);
    if (payload.action === "answer") {
      if (!payload.answers || typeof payload.answers !== "object" || Array.isArray(payload.answers)) return error("invalid_answer", 400);
      result = client.answer(payload.request_id, payload.input_request_id, payload.answers);
    }
    return Response.json(result, { headers });
  } catch (cause) { return error(cause instanceof ExecutionError ? cause.code : "execution_unavailable", cause instanceof ExecutionError ? cause.status : 503); }
}
