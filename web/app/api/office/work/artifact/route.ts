import path from "node:path";
import { OfficeWorkStore, WorkError } from "@/lib/office-work-store";
import { localWorkRequest, workHeaders as headers } from "@/lib/office-work-http";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  if (!localWorkRequest(request)) return Response.json({ error: { code: "local_only" } }, { status: 403, headers });
  const query = new URL(request.url).searchParams;
  const task = query.get("task_id"), index = query.get("index");
  if (!task || task.length > 100 || !index || !/^\d+$/.test(index) || [...query.keys()].some(key => !["task_id", "index"].includes(key))) return Response.json({ error: { code: "invalid_artifact" } }, { status: 400, headers });
  try {
    const value = new OfficeWorkStore(path.resolve(process.cwd(), "..")).artifact(task, Number(index));
    return new Response(value.text, { headers: { ...headers, "Content-Type": "text/plain; charset=utf-8", "Content-Security-Policy": "default-src 'none'; sandbox" } });
  } catch (cause) { return Response.json({ error: { code: cause instanceof WorkError ? cause.code : "artifact_unavailable" } }, { status: cause instanceof WorkError ? cause.status : 503, headers }); }
}
