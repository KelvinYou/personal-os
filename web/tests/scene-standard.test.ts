import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { test } from "vitest";
import { STANDARD, sceneParams, approach, smoothAngle, joystick, stepBoom, recenterYaw } from "@/lib/scene-standard.mjs";

const doc = fs.readFileSync(path.resolve(import.meta.dirname, "../../docs/design/3d-scene-standard.md"), "utf8");
test('documented numbers match the shared module',()=>{
 const S=STANDARD;
 const row=(name: string)=>{const m=doc.match(new RegExp('\\| '+name+' \\| ([0-9.]+)'));assert.ok(m,'doc row '+name);return Number(m[1]);};
 assert.equal(row('Walk speed'),S.walkSpeed);assert.equal(row('Run speed'),S.runSpeed);assert.equal(row('Collision radius'),S.collisionRadius);
 assert.match(doc,new RegExp('[Rr]ate '+S.accelerationRate+'\\b'));assert.match(doc,new RegExp('0\\.004 rad/px'));assert.equal(S.lookSensitivity,.004);
 assert.match(doc,new RegExp('Eye height '+S.eyeHeight+' m'));assert.match(doc,new RegExp('Vertical FOV '+S.firstFov+'°'));
 assert.match(doc,new RegExp('Boom \\(spring arm\\) length '+S.boom+'\\.0 m'));assert.match(doc,new RegExp('about '+S.followSmoothing+' s'));assert.match(doc,new RegExp(S.avatarTurnSmoothing+' s smoothing'));
 assert.match(doc,new RegExp('gain '+S.recenterGain+','));assert.match(doc,new RegExp('capped at '+S.recenterMaxRate+' rad/s'));assert.match(doc,new RegExp(S.recenterDelay.toFixed(1)+' s without look input'));assert.doesNotMatch(doc,/\| Q \/ E \|/);
 assert.match(doc,new RegExp('dead zone '+S.joystickDeadZone));assert.match(doc,new RegExp('0\\.7 m'));assert.equal(S.avatarFadeDistance,.7);
 for(const [k,v] of Object.entries({overviewToWalk:.6,firstThird:.3,sit:.4,focus:.5}))assert.equal(S.transitions[k as keyof typeof S.transitions],v);
});
test('scene scale multiplies lengths only',()=>{
 const S=STANDARD,p=sceneParams(1.37);
 assert.ok(Math.abs(p.walkSpeed-S.walkSpeed*1.37)<1e-12);assert.ok(Math.abs(p.eyeHeight-S.eyeHeight*1.37)<1e-12);assert.equal(sceneParams(1).collisionRadius,S.collisionRadius);
});
test('approach is frame-rate independent and angles take the short way round',()=>{
 let a=0;for(let i=0;i<10;i++)a=approach(a,1,10,.02);let b=0;for(let i=0;i<20;i++)b=approach(b,1,10,.01);assert.ok(Math.abs(a-b)<1e-9);
 assert.ok(smoothAngle(3,-3,.12,.016)>3,'wraps through pi, not through zero');
});
test('joystick has a dead zone and a continuous ramp',()=>{assert.deepEqual(joystick(.1,.05),{side:0,forward:0});
 const small=joystick(0,.3).forward,big=joystick(0,.9).forward;assert.ok(small>0&&small<big&&big<=1);assert.ok(Math.abs(joystick(0,1).forward-1)<1e-9);
});
test('boom shortens at once when blocked and eases out when clear',()=>{assert.equal(stepBoom(3,1,3,.016),1);
 const out=stepBoom(1,3,3,.016);assert.ok(out>1&&out<1.5);
});
test('chase camera swings behind sideways and forward travel, never toward the camera or while looking',()=>{
 const idle=2;
 assert.ok(recenterYaw(0,1.5,.016,{forward:0,side:1},idle)>0,'A or D arcs the view');
 assert.ok(recenterYaw(0,1.5,.016,{forward:1,side:0},idle)>0,'W follows a turned avatar');
 assert.equal(recenterYaw(0,1.5,.016,{forward:-1,side:0},idle),0,'S does not swing');
 assert.equal(recenterYaw(0,1.5,.016,{forward:0,side:0},idle),0,'standing still does not swing');
 assert.equal(recenterYaw(0,1.5,.016,{forward:1,side:1},.3),0,'recent look input blocks it');
 assert.ok(Math.abs(recenterYaw(0,3,1,{forward:0,side:1},idle))<=1.8+1e-9,'rate is capped');
 assert.ok(recenterYaw(3,-3,.016,{forward:1,side:0},idle)>3,'takes the short way round');
});
