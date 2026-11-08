import { readFile } from "node:fs/promises";
import path from "node:path";
import { designTokenRule } from "@/lib/design-tokens-css";

const source = path.resolve(process.cwd(), "components/home-design/apartment.html");

export function isLocalPreviewRequest(request: Request) {
  const host = request.headers.get("host") ?? "";
  const origin = request.headers.get("origin");
  return /^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/.test(host)
    && (!origin || origin === `http://${host}` || origin === `https://${host}`)
    && request.headers.get("sec-fetch-site") !== "cross-site";
}

export async function loadHomePreview() {
  const fragment = await readFile(source, "utf8");
  if (!fragment.includes('id="wyn-home-preview"') || !fragment.includes("<script type=\"module\">")) throw new Error("Invalid preview source");
  // Use the installed local engine. No model or dependency is fetched from a CDN.
  const local = fragment.replaceAll("https://cdn.jsdelivr.net/npm/three@0.187.0/build/three.module.js", "/home-design/three/three.module.js");
  if (/<script[^>]+src\s*=|(?:import\s*\(?\s*['"]https?:)/i.test(local)) throw new Error("Remote preview script rejected");
  const tokens = await designTokenRule();
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Home design · 3D preview</title><link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns=%27http://www.w3.org/2000/svg%27/%3E"><style>
    ${tokens}
    :root{color-scheme:light dark;--bg:var(--ds-background,light-dark(#f8f6f0,#242722));--fg:var(--ds-foreground,light-dark(#343a32,#ecece2));--muted:var(--ds-muted-foreground,light-dark(#656c60,#b9c0b1));--line:var(--ds-border,light-dark(#d4d8cd,#4a5146));--surface:var(--ds-card,var(--bg));--hover:var(--ds-muted,var(--line));--ring:var(--ds-ring,var(--fg));font:14px/1.5 system-ui,sans-serif;color:var(--fg);background:var(--bg)}
    *{box-sizing:border-box}body{margin:0;padding:12px}button,input,select{font:inherit}button,select{color:var(--fg);background:var(--surface);border:1px solid var(--line);border-radius:8px;min-height:44px;padding:8px 12px;max-width:100%}button{cursor:pointer;border-radius:10px;font-weight:500}button:hover:not(:disabled),select:hover:not(:disabled){background:var(--hover)}button[aria-pressed="true"]{background:var(--hover);border-color:var(--fg)}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--ring);outline-offset:3px}.viz-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.form-label{display:grid;gap:4px;min-width:0}.form-check{display:flex;align-items:center;gap:6px;min-height:44px}.form-range{max-width:160px;min-height:30px;accent-color:var(--fg)}.text-small{font-size:12px}.text-muted{color:var(--muted)}
    #wyn-home-preview .wyn-stage{height:max(360px,calc(100svh - 380px))!important}
    @media(max-width:480px){body{padding:8px}#wyn-home-preview .wyn-stage{height:max(360px,calc(100svh - 480px))!important}}
  </style><script>try{document.documentElement.style.colorScheme=localStorage.getItem('os-theme')||'light dark'}catch{}</script></head><body>${local}
  <script>
    const report=()=>{const root=document.getElementById('wyn-home-preview');const failed=root?.querySelector('[role="alert"]');if(root?.dataset.ready==='true'){window.parent.postMessage({type:'home-preview-ready'},location.origin);return true}if(failed){window.parent.postMessage({type:'home-preview-error'},location.origin);return true}return false};
    const watcher=new MutationObserver(()=>{if(report())watcher.disconnect()});watcher.observe(document.body,{subtree:true,attributes:true,childList:true});report();
    const syncTheme=()=>{try{document.documentElement.style.colorScheme=localStorage.getItem('os-theme')||'light dark'}catch{}};addEventListener('storage',syncTheme);
  </script></body></html>`;
}
