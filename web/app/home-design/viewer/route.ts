import { isLocalPreviewRequest, loadHomePreview } from "@/lib/home-preview";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = {
  "Content-Type": "text/html; charset=utf-8",
  "Cache-Control": "private, no-store, max-age=0",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "same-origin",
  "Content-Security-Policy": "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'",
};

export async function GET(request: Request) {
  if (!isLocalPreviewRequest(request)) return new Response("Local dashboard access only.", { status: 403, headers });
  try { return new Response(await loadHomePreview(), { headers }); }
  catch {
    return new Response('<!doctype html><html lang="en"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Preview unavailable</title><body><h1>Home preview unavailable</h1><p>The apartment model is missing or cannot be loaded. Restore the home preview source and reload.</p><script>parent.postMessage({type:"home-preview-error"},location.origin)</script></body></html>', { status: 503, headers });
  }
}
