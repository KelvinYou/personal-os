import path from "node:path";
import { OfficePosts, PostError } from "@/lib/office-posts";
import { localWorkRequest, workHeaders as headers } from "@/lib/office-work-http";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  if (!localWorkRequest(request)) return Response.json({ error: { code: "local_only" } }, { status: 403, headers });
  const query = new URL(request.url).searchParams;
  if (!query.has("id") || !query.has("name") || [...query.keys()].some(key => !["id", "name"].includes(key)) || query.getAll("id").length !== 1 || query.getAll("name").length !== 1) return Response.json({ error: { code: "invalid_image" } }, { status: 400, headers });
  try {
    const image = new OfficePosts(path.resolve(process.cwd(), "..")).image(query.get("id")!, query.get("name")!);
    return new Response(new Uint8Array(image.bytes), { headers: { ...headers, "Content-Type": image.type, "Content-Security-Policy": "default-src 'none'; sandbox", "Cross-Origin-Resource-Policy": "same-origin" } });
  } catch (cause) { return Response.json({ error: { code: cause instanceof PostError ? cause.code : "image_unavailable" } }, { status: cause instanceof PostError ? cause.status : 503, headers }); }
}
