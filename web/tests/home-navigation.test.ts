import assert from "node:assert/strict";
import { test } from "vitest";
import { moveOnFloor, canStand, type FloorWorld } from "@/lib/scene-floor.mjs";

// Synthetic rooms only; no private scene source is read.
const world: FloorWorld = { radius: .2, floor: [[0,0],[6,0],[6,6],[0,6]], obstacles: [{minX:2.95,maxX:3.05,minZ:0,maxZ:2.5},{minX:2.95,maxX:3.05,minZ:3.5,maxZ:6}] };
test('walker crosses an open doorway but cannot tunnel through its wall', ()=>{

 assert.ok(moveOnFloor({x:1,z:3},{x:4,z:0},world).x>4.9);
 assert.ok(moveOnFloor({x:1,z:1},{x:4,z:0},world).x<2.76);
});
test('body clearance applies to exterior corners, furniture and narrow gaps',()=>{

 assert.equal(canStand(.1,3,world),false);assert.equal(canStand(3,2.55,world),false);
 assert.equal(canStand(3,3,world),true);
 assert.equal(canStand(3,3,{...world,obstacles:[{minX:2,maxX:4,minZ:2,maxZ:4}]}),false);
 const concave: FloorWorld={radius:.2,floor:[[0,0],[4,0],[4,2],[2,2],[2,4],[0,4]],obstacles:[]};
 assert.equal(canStand(3,3,concave),false);assert.equal(canStand(1,3,concave),true);
});
test('diagonal movement slides along a wall and remains on the floor',()=>{
const result=moveOnFloor({x:2.5,z:1},{x:2,z:1},world);
 assert.ok(result.x<2.76);assert.ok(result.z>1.9);assert.ok(canStand(result.x,result.z,world));
 const edge=moveOnFloor({x:1,z:1},{x:-10,z:-10},world);assert.ok(canStand(edge.x,edge.z,world));
});
