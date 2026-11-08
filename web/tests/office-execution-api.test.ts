import assert from "node:assert/strict";
import { test, vi } from "vitest";

let reads = 0, sends = 0, fail = false;
class ExecutionError extends Error {
 code: string; status: number;
 constructor(code: string, status = 503) { super(code); this.code = code; this.status = status; }
}
vi.mock("@/lib/office-execution", () => ({
 ExecutionError,
 execution: async () => { reads++; if (fail) throw new Error("PRIVATE_SECRET"); return { snapshot: () => ({ status: "ready" }), send: async () => { sends++; return { status: "starting" }; } }; },
}));
const route = await import("@/app/api/office/execution/route");
const request = (body?: unknown, headers: Record<string, string> = {}) => new Request("http://127.0.0.1:3003/api/office/execution", { method: body === undefined ? "GET" : "POST", headers: { host: "127.0.0.1:3003", origin: "http://127.0.0.1:3003", "content-type": "application/json", ...headers }, ...(body === undefined ? {} : { body: typeof body === "string" ? body : JSON.stringify(body) }) });
test('local GET never starts work; explicit valid send is private and uncached',async()=>{
 assert.equal((await route.GET(request())).status,200);assert.equal(sends,0);
 const value=await route.POST(request({action:'send',request_id:'request-1',text:'Inspect fixture'}));
 assert.equal(value.status,200);assert.match(value.headers.get('cache-control')!,/private, no-store/);assert.equal(sends,1);
});
test('host/origin/cross-site/content-type protections reject before accessing execution',async()=>{
 const before=reads;
 for(const headers of [{host:'attacker.invalid'},{origin:'https://attacker.invalid'},{origin:''},{'sec-fetch-site':'cross-site'}] as Record<string,string>[])assert.equal((await route.POST(request({action:'stop',request_id:'request-1'},headers))).status,403);
 assert.equal((await route.GET(request(undefined,{host:'attacker.invalid'}))).status,403);
 assert.equal((await route.POST(request('{}',{'content-type':'text/plain'}))).status,415);
 assert.equal(reads,before);
});
test('malformed/oversized/arbitrary thread or command input never reaches runtime',async()=>{
 const before=reads;
 for(const body of ['{',[],{action:'send',request_id:'request-1',text:'task',thread_id:'desktop-thread'},{action:'exec',request_id:'request-1',command:'shell'}])assert.equal((await route.POST(request(body))).status,400);
 assert.equal((await route.POST(request('x'.repeat(512*1024+1)))).status,413);
 assert.equal(reads,before);
});
test('backend diagnostics stay private and never become a successful empty state',async()=>{
 fail=true;try{const response=await route.GET(request());assert.equal(response.status,503);assert.doesNotMatch(await response.text(),/PRIVATE_SECRET/);}finally{fail=false;}
});
test('explicit team mode is accepted while unknown modes fail before runtime access',async()=>{
 const before=reads;
 assert.equal((await route.POST(request({action:'send',request_id:'request-team',text:'Inspect fixture',collaboration:'swarm'}))).status,400);
 assert.equal(reads,before);
 assert.equal((await route.POST(request({action:'send',request_id:'request-team',text:'Inspect fixture',collaboration:'team'}))).status,200);
});
