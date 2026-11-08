import { NextRequest, NextResponse } from "next/server";
import { loadOfficeSnapshot } from "@/lib/office";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const revalidate = 0;
const headers = { "Cache-Control": "private, no-store, max-age=0", "Vary": "Origin", "X-Content-Type-Options": "nosniff" };

export async function GET(request: NextRequest) {
  const host = request.headers.get("host") ?? "";
  const origin = request.headers.get("origin");
  // Local-only API. No forwarded host trust, CORS, input paths or write actions.
  if (!/^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(host) || (origin && origin !== `http://${host}` && origin !== `https://${host}`)) {
    return NextResponse.json({ error: { code: "local_only", message: "Office evidence is available only from the local dashboard." } }, { status: 403, headers });
  }
  try { return NextResponse.json(await loadOfficeSnapshot(), { headers }); }
  catch {
    return NextResponse.json({ error: { code: "source_unavailable", message: "Cannot read local Codex evidence. Check office configuration and session access, then retry." } }, { status: 503, headers });
  }
}
