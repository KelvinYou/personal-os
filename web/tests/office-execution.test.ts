// Protocol expectations: official App Server lifecycle + CLI 0.164 generated schema.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "vitest";
import type { ExecutionConfig } from "@/lib/office-execution-contract";
import { OfficeExecution } from "@/lib/office-execution-runtime";

type RunEvidenceRecord = Parameters<NonNullable<ConstructorParameters<typeof OfficeExecution>[0]["archive"]>["record"]>[0];
interface Call {
 id?: number; method?: string; result?: unknown;
 params: { threadId?: string; turnId?: string; approvalPolicy?: string; sandboxPolicy: { type: string; networkAccess: boolean }; input: { text: string }[] };
}
type Calls = () => Call[];
const config: ExecutionConfig = { enabled: true, poll_interval_ms: 1000, max_prompt_chars: 8000, max_messages: 40, max_message_chars: 32000, rpc_timeout_seconds: 5, turn_timeout_seconds: 30 };
const fake = `#!/usr/bin/env node
const readline = require('node:readline');
const fs = require('node:fs');
let turn = 0;
const emit = x => process.stdout.write(JSON.stringify(x)+'\\n');
readline.createInterface({input:process.stdin}).on('line', line => {
 const m = JSON.parse(line); fs.appendFileSync(__filename+'.calls', line+'\\n');
 if(m.method==='initialized')return;
 let result = {};
 if(['thread/start','thread/resume'].includes(m.method)) result={thread:{id:'owned-thread'},sandbox:{type:'workspaceWrite'},approvalPolicy:'never'};
 if(m.method==='turn/start') result={turn:{id:'turn-'+(++turn),status:'inProgress'}};
 if(m.method==='turn/interrupt') {emit({id:m.id,result});emit({method:'turn/completed',params:{threadId:'owned-thread',turn:{id:m.params.turnId,status:'interrupted'}}});return;}
 emit({id:m.id,result});
 if(m.method==='turn/start') {
  const id='turn-'+turn;
  emit({method:'item/agentMessage/delta',params:{threadId:'foreign-thread',turnId:id,itemId:'foreign',delta:'FOREIGN SECRET'}});
  emit({method:'item/agentMessage/delta',params:{threadId:'owned-thread',turnId:id,itemId:'answer-'+turn,delta:'Live reply'}});
  if(m.params.input[0].text==='wait') return;
  const complete=()=>{emit({method:'item/completed',params:{threadId:'owned-thread',turnId:id,item:{id:'answer-'+turn,type:'agentMessage',text:'Final reply'}}});emit({method:'turn/completed',params:{threadId:'owned-thread',turn:{id,status:'completed'}}});};
  if(m.params.input[0].text==='Inspect fixture'){const timer=setInterval(()=>{if(fs.existsSync(__filename+'.finish')){clearInterval(timer);complete();}},20);}else setTimeout(complete,50);
 }
});
`;
async function until(fn: () => boolean) { for(let i=0;i<500;i++){if(fn())return;await new Promise(r=>setTimeout(r,20));}throw Error('condition timed out'); }
async function fixture(run: (client: OfficeExecution, calls: Calls, dir: string) => Promise<void>, source: string = fake, overrides: Partial<ExecutionConfig> = {}) {
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'office-execution-'));
 const binary=path.join(dir,'codex');fs.writeFileSync(binary,source,{mode:0o700});
 const client=new OfficeExecution({root:dir,binary,config:{...config,...overrides}});
 try{await run(client,()=>fs.readFileSync(binary+'.calls','utf8').trim().split('\n').map((l)=>JSON.parse(l) as Call),dir);}finally{client.close();fs.rmSync(dir,{recursive:true,force:true});}
}
test('web task streams replies, continues only its owned thread and excludes foreign content', async()=>{
 await fixture(async(client,calls,dir)=>{
  await client.send('request-1','Inspect fixture');
  await until(()=>client.snapshot().messages.some(m=>m.text==='Live reply'));
  fs.writeFileSync(path.join(dir,'codex.finish'),'finish');
  await until(()=>client.snapshot().status==='idle');
  assert.equal(client.snapshot().messages.at(-1)!.text,'Final reply');
  await client.send('request-2','Follow up');
  await until(()=>client.snapshot().status==='idle');
  assert.equal(calls().filter(c=>c.method==='thread/start').length,1);
  const starts=calls().filter(c=>c.method==='turn/start');
  assert.equal(starts.length,2);
  assert.equal(starts[1]!.params.threadId,'owned-thread');
  assert.equal(starts[0]!.params.sandboxPolicy.type,'workspaceWrite');
  assert.equal(starts[0]!.params.sandboxPolicy.networkAccess,false);
  assert.equal(calls().find(c=>c.method==='thread/start')!.params.approvalPolicy,'never');
  assert.doesNotMatch(JSON.stringify(client.snapshot()),/FOREIGN SECRET/);
  assert.equal(calls().some(c=>c.method==='thread/resume'),false);
 });
});
test('duplicate sends never execute twice; concurrent tasks and resetting active work are refused', async()=>{
 await fixture(async(client,calls)=>{
  await client.send('request-1','wait');
  await client.send('request-1','wait');
  await assert.rejects(client.send('request-2','other'),/task_busy/);
  assert.throws(()=>client.reset('request-3'),/task_busy/);
  await until(()=>!!client.snapshot().turn_id);
  assert.equal(calls().filter(c=>c.method==='turn/start').length,1);
  await client.stop('request-stop');
  await until(()=>client.snapshot().status==='interrupted');
  assert.equal(calls().find(c=>c.method==='turn/interrupt')!.params.threadId,'owned-thread');
 });
});
test('stop during initialization stays interrupted and never launches a late task', async()=>{
 await fixture(async(client,calls)=>{
  await client.send('request-1','wait');
  await client.stop('request-stop');
  await new Promise(r=>setTimeout(r,150));
  assert.equal(client.snapshot().status,'interrupted');
  assert.equal(client.snapshot().turn_id,null);
 });
});
test('runtime loss and turn deadline remain errors and hide private diagnostics',async()=>{
 for(const source of [fake.replace("if(m.params.input[0].text==='wait') return;","if(m.params.input[0].text==='wait') {process.stderr.write('PRIVATE_SECRET'); process.exit(2);}"),fake]) {
  await fixture(async client=>{
   await client.send('request-1','wait');
   await until(()=>client.snapshot().status==='error');
   assert.ok(['runtime_disconnected','turn_timeout'].includes(client.snapshot().error as string));
   assert.doesNotMatch(JSON.stringify(client.snapshot()),/PRIVATE_SECRET/);
  },source,{turn_timeout_seconds:0.8});
 }
});
test('web answers owned questions; unknown permission requests fail without approval',async()=>{
 for(const method of ['item/tool/requestUserInput','item/commandExecution/requestApproval']) {
  const source=fake.replace("if(m.params.input[0].text==='wait') return;",`if(m.params.input[0].text==='wait') {emit({id:77,method:'${method}',params:{threadId:'owned-thread',turnId:id,questions:[{id:'choice',header:'Pick',question:'Which fixture?',options:[{label:'A',description:'First'}]}]}});return;}`);
  await fixture(async(client,calls)=>{
   await client.send('request-1','wait');
   if(method==='item/tool/requestUserInput') {
    await until(()=>client.snapshot().status==='waiting');
    assert.equal(client.snapshot().input_request!.questions[0].question,'Which fixture?');
    assert.throws(()=>client.answer('request-2','old',{choice:{answers:['A']}}),/input_expired/);
    client.answer('request-3','77',{choice:{answers:['A']}});
    client.answer('request-3','77',{choice:{answers:['A']}});
    await until(()=>calls().some(c=>c.id===77&&c.result));
    assert.deepEqual(calls().find(c=>c.id===77&&c.result)!.result,{answers:{choice:{answers:['A']}}});
    assert.equal(calls().filter(c=>c.id===77&&c.result).length,1);
    await client.stop('request-stop');
   }else{
    await until(()=>client.snapshot().status==='error');
    assert.equal(client.snapshot().error,'additional_permission_required');
    assert.equal(calls().some(c=>c.id===77&&c.result),false);
   }
  },source);
 }
});
test('stop terminates detached tool processes owned by this runtime',async()=>{
 const source=fake.replace("if(m.params.input[0].text==='wait') return;",`if(m.params.input[0].text==='wait') { const p=require('node:child_process').spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{detached:true,stdio:'ignore'});fs.writeFileSync(__filename+'.pid',String(p.pid));return;}`);
 await fixture(async(client,calls,dir)=>{
  await client.send('request-1','wait');
  await until(()=>!!client.snapshot().turn_id);
  await until(()=>fs.existsSync(path.join(dir,'codex.pid')));
  const pid=Number(fs.readFileSync(path.join(dir,'codex.pid'),'utf8'));
  try{
   await client.stop('request-stop');
   await until(()=>{try{process.kill(pid,0);return false;}catch{return true;}});
   assert.equal(client.snapshot().status,'interrupted');
   await client.send('request-followup','Continue');
   await until(()=>client.snapshot().status==='idle');
   assert.equal(calls().find(c=>c.method==='thread/resume')!.params.threadId,'owned-thread');
  }finally{try{process.kill(pid,'SIGKILL');}catch{}}
 },source);
});

// Native 0.164.0 smoke emits subAgentActivity on the parent and child
// turn/completed with rootTurnId, rather than a spawn collab tool item.
const nativeTeam = fake.replace("if(m.params.input[0].text==='wait') return;", `
  if(m.params.input[0].text.includes('TEAM_SMOKE')) {
   const activity=(kind,thread,name)=>emit({method:'item/completed',params:{threadId:'owned-thread',turnId:id,item:{type:'subAgentActivity',id:kind+thread,kind,agentThreadId:thread,agentPath:'/root/'+name}}});
   activity('started','child-alpha','explore'); activity('started','child-beta','review');
   activity('started','child-alpha','explore');
   emit({method:'item/completed',params:{threadId:'foreign-thread',turnId:id,item:{type:'subAgentActivity',id:'bad',kind:'started',agentThreadId:'foreign-child',agentPath:'/root/secret'}}});
   emit({method:'turn/completed',params:{threadId:'child-alpha',turn:{id:'old-child-turn',rootTurnId:'old-root',status:'completed',items:[{type:'agentMessage',text:'STALE SECRET'}]}}});
   setTimeout(()=>{for(const [thread,text] of [['child-alpha','ALPHA'],['child-beta','BETA']]) {
    activity('completed',thread,thread==='child-alpha'?'explore':'review');
    emit({method:'turn/completed',params:{threadId:thread,turn:{id:thread+'-turn',rootTurnId:id,status:'completed',items:[{type:'agentMessage',text,phase:'final_answer'}]}}});
   }
   emit({method:'item/completed',params:{threadId:'owned-thread',turnId:id,item:{id:'summary',type:'agentMessage',text:'ALPHA + BETA',phase:'final_answer'}}});
   emit({method:'turn/completed',params:{threadId:'owned-thread',turn:{id,status:'completed'}}});},100);
   return;
  }
  if(m.params.input[0].text==='wait') return;`);
test('native team is derived from owned events, deduplicates participants and keeps child results out of root chat', async()=>{
 await fixture(async(client,calls)=>{
  await client.send('request-team','TEAM_SMOKE','team');
  await until(()=>client.snapshot().status==='idle');
  const state=client.snapshot();
  assert.equal(state.task!.collaboration,'team');
  assert.equal(state.task!.status,'completed');
  assert.equal(state.agents.length,3);
  const children=state.agents.filter(a=>a.parent_id);
  assert.deepEqual(children.map(a=>a.result),['ALPHA','BETA']);
  assert.ok(children.every(a=>a.status==='completed' && a.parent_id===state.agents[0]!.id && a.task_id===state.task!.id));
  assert.equal(state.messages.at(-1)!.text,'ALPHA + BETA');
  assert.doesNotMatch(JSON.stringify(state),/FOREIGN SECRET|STALE SECRET|foreign-child/);
  assert.match(calls().find(c=>c.method==='turn/start')!.params.input[0].text,/two.*subagents/i);
  await assert.rejects(client.send('request-team','TEAM_SMOKE','solo'),/request_id_reused/);
 },nativeTeam);
});
test('missing delegation, failed child and early parent completion cannot claim team success', async()=>{
 const variants=[fake,nativeTeam.replace("status:'completed',items:[{type:'agentMessage',text,phase", "status:'failed',items:[{type:'agentMessage',text,phase"),nativeTeam.replace("for(const [thread,text] of [['child-alpha','ALPHA'],['child-beta','BETA']])", "for(const [thread,text] of [])")];
 for(const source of variants) await fixture(async client=>{
  await client.send('request-team','TEAM_SMOKE','team');
  await until(()=>client.snapshot().status==='idle');
  assert.equal(client.snapshot().task!.status,'incomplete');
  assert.ok(client.snapshot().agents.every(a=>a.status!=='working'));
 },source);
});
test('stopping a native team marks its active participants interrupted and retains identities',async()=>{
 const source=nativeTeam.replace('},100);','},100000);');
 await fixture(async client=>{
  await client.send('request-team','TEAM_SMOKE','team');
  await until(()=>client.snapshot().agents?.length===3);
  await client.stop('request-stop');
  assert.equal(client.snapshot().task!.status,'interrupted');
  assert.ok(client.snapshot().agents.every(a=>a.status==='interrupted'));
 },source);
});
test('early parent completion shuts down still-running child tools',async()=>{
 const source=nativeTeam.replace("activity('started','child-alpha','explore'); activity('started','child-beta','review');", `activity('started','child-alpha','explore'); activity('started','child-beta','review'); const tool=require('node:child_process').spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{detached:true,stdio:'ignore'});fs.writeFileSync(__filename+'.pid',String(tool.pid));`).replace("for(const [thread,text] of [['child-alpha','ALPHA'],['child-beta','BETA']])", "for(const [thread,text] of [])");
 await fixture(async(client,calls,dir)=>{
  await client.send('request-team','TEAM_SMOKE','team');
  await until(()=>client.snapshot().status==='idle');
  const pid=Number(fs.readFileSync(path.join(dir,'codex.pid'),'utf8'));
  try { await until(()=>{try{process.kill(pid,0);return false;}catch{return true;}}); assert.equal(client.snapshot().task!.status,'incomplete'); } finally {try{process.kill(pid,'SIGKILL');}catch{}}
 },source);
});
test('an empty follow-up cannot reuse the previous task result as completion evidence',async()=>{
 const source=fake.replace("if(m.params.input[0].text==='wait') return;", "if(m.params.input[0].text==='empty') {emit({method:'turn/completed',params:{threadId:'owned-thread',turn:{id,status:'completed'}}});return;} if(m.params.input[0].text==='wait') return;");
 await fixture(async client=>{
  await client.send('request-first','First');await until(()=>client.snapshot().status==='idle');
  assert.equal(client.snapshot().task!.status,'completed');
  await client.send('request-empty','empty');await until(()=>client.snapshot().status==='idle');
  assert.equal(client.snapshot().task!.status,'incomplete');
  assert.equal(client.snapshot().agents[0]!.result,null);
 },source);
});

test('skill assignment is server validated, reaches the actual turn, and participates in idempotency', async()=>{
 await fixture(async(client,calls,dir)=>{
  fs.mkdirSync(path.join(dir,'.agents/skills/daily-report'),{recursive:true});
  fs.writeFileSync(path.join(dir,'.agents/skills/daily-report/SKILL.md'),'---\nname: daily-report\n---\nFixture skill.');
  for(const id of ['missing','../../private',{},'daily-report/SKILL.md']) await assert.rejects(client.send('bad-skill','Fixture task','solo',id as string),/invalid_skill/);
  assert.equal(client.snapshot().task,null);
  await client.send('skill-request','Fixture task','solo','daily-report');
  await until(()=>client.snapshot().status==='idle');
  assert.equal(client.snapshot().task!.skill_id,'daily-report');
  assert.match(calls().find(c=>c.method==='turn/start')!.params.input[0].text,/Read and follow .agents\/skills\/daily-report\/SKILL.md/);
  await client.send('skill-request','Fixture task','solo','daily-report');
  await assert.rejects(client.send('skill-request','Fixture task','solo'),/request_id_reused/);
  assert.equal(calls().filter(c=>c.method==='turn/start').length,1);
  client.reset('skill-reset'); assert.equal(client.snapshot().task,null);
 });
});

test('owned final evidence is archived before reset; missing history refuses model dispatch', async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'office-archive-'));
 const binary=path.join(dir,'codex');fs.writeFileSync(binary,fake,{mode:0o700});
 const records=new Map<string, RunEvidenceRecord>();
 const archive={record(record: RunEvidenceRecord){records.set(record.task.id,structuredClone(record));},find(id: string){return records.get(id)??null;}};
 const client=new OfficeExecution({root:dir,binary,config,archive});
 try{
  await client.send('archive-first','Follow up');
  await until(()=>client.snapshot().status==='idle');
  const id=client.snapshot().task!.id;
  assert.equal(records.get(id)!.result,'Final reply');
  assert.equal(records.get(id)!.task.status,'completed');
  assert.doesNotMatch(JSON.stringify([...records.values()]),/FOREIGN SECRET|messages|reasoning/);
  client.reset('archive-reset');
  assert.equal(records.get(id)!.result,'Final reply');
  const reopened=new OfficeExecution({root:dir,binary,config,archive});
  try { await assert.rejects(reopened.send('archive-first','Follow up'),/task_already_recorded/); } finally { reopened.close(); }
  const refused=new OfficeExecution({root:dir,binary,config,archive:{record(){throw Error('storage failed');}}});
  const before=fs.readFileSync(binary+'.calls','utf8');
  try{await assert.rejects(refused.send('archive-refused','Do work'),/history_unavailable/);assert.equal(fs.readFileSync(binary+'.calls','utf8'),before);}finally{refused.close();}
 }finally{client.close();fs.rmSync(dir,{recursive:true,force:true});}
});

test('only completed owned file-change events create artifact references', async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'office-files-'));
 const binary=path.join(dir,'codex');
 const event=(thread: string,status: string,file: string)=>`emit({method:'item/completed',params:{threadId:'${thread}',turnId:id,item:{id:'files',type:'fileChange',status:'${status}',changes:[{path:'${file}'}]}}});`;
 const source=fake.replace("const complete=()=>{",`const complete=()=>{${event('foreign-thread','completed','secret.md')}${event('owned-thread','failed','failed.md')}${event('owned-thread','completed','docs/result.md')}`);
 fs.writeFileSync(binary,source,{mode:0o700});
 const saved: RunEvidenceRecord[]=[];const client=new OfficeExecution({root:dir,binary,config,archive:{record(r){saved.push(structuredClone(r));}}});
 try{await client.send('files-request','Follow up');await until(()=>client.snapshot().status==='idle');assert.deepEqual(saved.at(-1)!.artifacts,['docs/result.md']);}
 finally{client.close();fs.rmSync(dir,{recursive:true,force:true});}
});
