export const workHeaders = { "Cache-Control": "private, no-store, max-age=0", "Vary": "Origin", "X-Content-Type-Options": "nosniff" };
export function localWorkRequest(request: Request, write = false) {
  const host = request.headers.get("host") ?? "";
  const origin = request.headers.get("origin");
  return /^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(host)
    && request.headers.get("sec-fetch-site") !== "cross-site"
    && (!origin ? !write : origin === `http://${host}` || origin === `https://${host}`);
}
