import path from "node:path";
import { OfficePosts, PostError } from "@/lib/office-posts";
import { localWorkRequest, workHeaders as headers } from "@/lib/office-work-http";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  if (!localWorkRequest(request)) return Response.json({ error: { code: "local_only" } }, { status: 403, headers });
  const query = new URL(request.url).searchParams;
  if ([...query.keys()].some(key => key !== "id") || query.getAll("id").length > 1) return Response.json({ error: { code: "invalid_post" } }, { status: 400, headers });
  try {
    const store = new OfficePosts(path.resolve(process.cwd(), ".."));
    return Response.json(query.has("id") ? { post: store.get(query.get("id")!) } : store.list(), { headers });
  } catch (cause) { return Response.json({ error: { code: cause instanceof PostError ? cause.code : "posts_unavailable" } }, { status: cause instanceof PostError ? cause.status : 503, headers }); }
}
