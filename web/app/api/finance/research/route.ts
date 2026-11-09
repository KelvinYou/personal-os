import { ResearchError, researchCommand } from "@/lib/finance-research-server";
import { parsePostIdea, parseResearchSnapshot, parseWhatif } from "@/lib/finance-research-contract";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "private, no-store, max-age=0", "Vary": "Origin", "X-Content-Type-Options": "nosniff" };
function permitted(request: Request, write = false) {
  const host = request.headers.get("host") ?? "", origin = request.headers.get("origin");
  return /^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(host) && request.headers.get("sec-fetch-site") !== "cross-site"
    && (!origin ? !write : ["http://", "https://"].some(protocol => origin === protocol + host));
}
const error = (code: string, status: number) => Response.json({ error: { code } }, { status, headers });
const failed = (cause: unknown) => error(cause instanceof ResearchError ? cause.code : "research_unavailable", cause instanceof ResearchError ? cause.status : 503);
const demo = (request: Request) => new URL(request.url).searchParams.get("mode") === "demo";

export async function GET(request: Request) {
  if (!permitted(request)) return error("local_only", 403);
  try { return Response.json(parseResearchSnapshot(await researchCommand("read", undefined, demo(request))), { headers }); }
  catch (cause) { return failed(cause); }
}

/** `whatif` recomputes without saving; `review` appends the owner's decision; `post_idea` files a Content Lab idea. */
export async function POST(request: Request) {
  if (!permitted(request, true)) return error("same_origin_required", 403);
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) return error("json_required", 415);
  const text = await request.text();
  if (text.length > 16384) return error("payload_too_large", 413);
  let payload: unknown;
  try { payload = JSON.parse(text); } catch { return error("invalid_payload", 400); }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return error("invalid_payload", 400);
  const op = (payload as { op?: unknown }).op;
  if (op !== "whatif" && op !== "review" && op !== "post_idea") return error("invalid_payload", 400);
  try {
    const value = await researchCommand("apply", payload, demo(request));
    if (op === "post_idea") return Response.json(parsePostIdea(value), { headers });
    return Response.json(op === "whatif" ? parseWhatif(value) : parseResearchSnapshot(value), { headers });
  } catch (cause) { return failed(cause); }
}
