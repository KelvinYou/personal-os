import assert from "node:assert/strict";
import { test } from "vitest";
import { createPlayer, walkWorld, advancePlayer, canOccupy, thirdPersonPosition } from "@/lib/office-navigation";

test('camera changes share a pose and diagonal walking is normalized',()=>{
 const world=walkWorld(18),origin=createPlayer(),forward=createPlayer(),diagonal=createPlayer();forward.yaw=diagonal.yaw=0;
 advancePlayer(forward,{forward:1,side:0,turn:0},.1,world);
 advancePlayer(diagonal,{forward:1,side:1,turn:0},.1,world);
 assert.ok(Math.abs(Math.hypot(forward.x-origin.x,forward.z-origin.z)-Math.hypot(diagonal.x-origin.x,diagonal.z-origin.z))<1e-8);
 const before={...forward};thirdPersonPosition(forward,world);assert.deepEqual(forward,before);
});
test('walking stays on the floor, cannot cross desks or pavilion walls, and slides along obstacles',()=>{
 const world=walkWorld(18),player=createPlayer();assert.ok(canOccupy(world,player.x,player.z));
 for(let i=0;i<500;i++)advancePlayer(player,{forward:1,side:0,turn:0},.02,world);
 assert.ok(player.x>world.minX && player.x<world.maxX);assert.ok(canOccupy(world,player.x,player.z));
 assert.equal(canOccupy(world,-15.7,-8.46),false);assert.equal(canOccupy(world,-3,-8),false);
 assert.equal(canOccupy(world,-11,-4),true,'pavilion doorway stays accessible');
 const glass=createPlayer();glass.x=-2.5;glass.z=-8;glass.yaw=Math.PI/2;
 for(let i=0;i<60;i++)advancePlayer(glass,{forward:1,side:1,turn:0},.02,world);
 assert.ok(glass.x> -3);assert.ok(glass.z< -8.5 && glass.z> -11,'motion slides along the pavilion side wall');
});
test('large frame gaps cannot tunnel across desks or jump across the room',()=>{
 const p=createPlayer(),origin=createPlayer(),world=walkWorld(18);advancePlayer(p,{forward:1,side:0,turn:0},60,world);
 assert.ok(Math.hypot(p.x-origin.x,p.z-origin.z)<.3);
 for(let i=0;i<30;i++)advancePlayer(p,{forward:0,side:0,turn:0},.05,world);const at={...p};advancePlayer(p,{forward:0,side:0,turn:0},.1,world);assert.equal(p.moving,false,'releasing input decelerates to a stop');assert.equal(p.x,at.x);
});

test('third-person camera shortens before pavilion walls or tall props without moving the avatar',()=>{
 const world=walkWorld(18),player=createPlayer();player.x=-2.5;player.z=-8;player.yaw=-Math.PI/2;
 const before={...player},position=thirdPersonPosition(player,world);
 assert.ok(canOccupy(world,position[0],position[2],.12,world.cameraWalls));assert.deepEqual(player,before);
 const origin=createPlayer(),open=thirdPersonPosition(origin,world);assert.ok(Math.hypot(open[0]-origin.x,open[2]-origin.z)>3,'starting third-person camera has room to show the host');
});

test('walking accelerates and decelerates instead of snapping to speed',()=>{
 const world=walkWorld(18),p=createPlayer();advancePlayer(p,{forward:1,side:0,turn:0},.016,world);
 const first=Math.hypot(p.vx,p.vz);assert.ok(first>0&&first<.5*2.4,'first frame is a fraction of walk speed');
 for(let i=0;i<60;i++){advancePlayer(p,{forward:1,side:0,turn:0},.016,world);p.x=2;p.z=9;}
 const walk=Math.hypot(p.vx,p.vz);advancePlayer(p,{forward:1,side:0,turn:0,run:true},.016,world);
 for(let i=0;i<60;i++){advancePlayer(p,{forward:1,side:0,turn:0,run:true},.016,world);p.x=2;p.z=9;}
 assert.ok(Math.hypot(p.vx,p.vz)>walk*1.8,'run is about twice walk speed');
});
test('every view shares one control scheme: the avatar turns toward travel',()=>{
 const world=walkWorld(18),p=createPlayer();p.yaw=0;
 for(let i=0;i<40;i++)advancePlayer(p,{forward:0,side:1,turn:0},.016,world);
 assert.ok(Math.abs(p.facing)>1.2,'avatar turns toward its sideways travel');
 const idle=createPlayer();idle.yaw=1;idle.facing=-.4;for(let i=0;i<20;i++)advancePlayer(idle,{forward:0,side:0,turn:0},.016,world);
 assert.equal(idle.facing,-.4,'avatar holds its facing when standing still');
});
test('A/D arc the camera behind the avatar after the look delay, in first and third person alike',()=>{
 const world=walkWorld(18),p=createPlayer();p.lookIdle=2;
 for(let i=0;i<30;i++)advancePlayer(p,{forward:0,side:-1,turn:0},.016,world);
 assert.ok(p.yaw>.1,'camera swings left with A');
 const looking=createPlayer();for(let i=0;i<30;i++)advancePlayer(looking,{forward:0,side:-1,turn:0},.016,world);
 assert.equal(looking.yaw,0,'no swing inside the delay after look input');
 const keyed=createPlayer();keyed.lookIdle=2;advancePlayer(keyed,{forward:0,side:-1,turn:1},.016,world);assert.equal(keyed.lookIdle,0,'arrow turn counts as look input');
 const overview=createPlayer();overview.lookIdle=2;for(let i=0;i<30;i++)advancePlayer(overview,{forward:0,side:-1,turn:0},.016,world,.7);assert.equal(overview.yaw,0,'god view never touches the player yaw');
});
