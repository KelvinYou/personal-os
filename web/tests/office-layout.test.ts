import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { test } from "vitest";
import { neighborhoods, studioSkills, skillSeat } from "@/lib/office-layout";
import { seatedAt, deskAngle, idlePose } from "@/lib/office-life";
import { walkWorld, canOccupy, createPlayer } from "@/lib/office-navigation";

const skillsDir = path.resolve(import.meta.dirname, "../../.agents/skills");
test('every current employee has one neighborhood and retains its seat when filtered or reordered',()=>{
 const actual=fs.readdirSync(skillsDir).filter(id=>fs.existsSync(path.join(skillsDir,id,'SKILL.md')));
 assert.ok(studioSkills.every(id=>actual.includes(id)), 'all named neighborhoods refer to installed skills');
 assert.equal(new Set(studioSkills).size,18);
 assert.deepEqual(neighborhoods.find(zone=>zone.id==='coach')?.skills,['coach-planner'],'the approved gym belongs to Coach Planner');
 assert.deepEqual(neighborhoods.map(n=>n.skills.length),[6,8,2,1,1]);
 for(const skill of studioSkills)assert.equal(skillSeat(skill,0),skillSeat(skill,99));
 assert.equal(skillSeat(undefined,2),2,'temporary participants keep positional seating');
 assert.ok(skillSeat('future-specialist',0)>=18,'new skills use the extension bay');
 const expanded=[...studioSkills,'future-specialist','another-specialist'];
 assert.equal(skillSeat('future-specialist',0,expanded),skillSeat('future-specialist',99,[...expanded].reverse()),'future employee seats use the full catalog rather than visible order');
});
test('every employee can be approached from spawn through continuous clear circulation',()=>{
 const world=walkWorld(18),start=createPlayer(),step=.25,queue=[[start.x,start.z]],seen=new Set([`${start.x},${start.z}`]);
 for(let index=0;index<queue.length;index++){
  const [x,z]=queue[index];
  for(const [dx,dz] of [[step,0],[-step,0],[0,step],[0,-step]]){
   const nx=x+dx,nz=z+dz,key=`${nx},${nz}`;
   if(!seen.has(key)&&canOccupy(world,nx,nz)){seen.add(key);queue.push([nx,nz]);}
  }
 }
 for(let index=0;index<18;index++){
  const [x,,z]=seatedAt(index),approachX=x+.9;
  assert.ok(queue.some(([px,pz])=>Math.hypot(px-approachX,pz-z)<.3),`${studioSkills[index]} can be reached beside its chair`);
 }
 for(const zone of neighborhoods)assert.ok(queue.some(([x,z])=>Math.hypot(x-zone.x,z-zone.z-zone.depth/2-.6)<.3),`${zone.id} entrance connects to the garden`);
});

test('extension seats leave enough floor for their chairs and visitor approaches',()=>{
 for(const count of [19,24,25,64]){
  const world=walkWorld(count);
  for(let index=18;index<count;index++){
   const [x,,z]=seatedAt(index);
   assert.ok(canOccupy(world,x+.9,z),`extension seat ${index} stays approachable with roster ${count}`);
  }
 }
});

test('pavilion walls block walking while broad level entrances remain open',()=>{
 const world=walkWorld(18);
 assert.equal(canOccupy(world,-3,-8),false,'Maker Studio side wall is solid');
 for(const zone of neighborhoods){
  assert.equal(canOccupy(world,zone.x,zone.z-zone.depth/2),false,`${zone.id} back wall is solid`);
  assert.equal(canOccupy(world,zone.x,zone.z+zone.depth/2),true,`${zone.id} front entrance is level and clear`);
 }
 assert.equal(canOccupy(world,25,18),false,'cannot leave the visible irregular lawn');
});

test('decorative breaks leave pavilions through open entrances rather than walls',()=>{
 const world=walkWorld(18);
 for(let index=0;index<4;index++)for(let second=0;second<700;second+=.5){
  const pose=idlePose(index,second);
  if(pose.mode==='walking')assert.ok(canOccupy(world,pose.at[0],pose.at[2],.1,world.cameraWalls),`worker ${index} crosses a wall or tall prop at ${second}`);
 }
});
