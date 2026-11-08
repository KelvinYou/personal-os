import { test } from "vitest";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import * as T from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import * as b from "@/lib/character-builder.mjs";
import { characterProfile, characterWardrobe } from "@/lib/office-character";

const web = path.resolve(import.meta.dirname, "..");
const kelvin = () => { const look = characterWardrobe("kelvin.ai", undefined, true); return { look, profile: { ...characterProfile("kelvin.ai"), feminine: false, shirt: look.shirt } }; };
test("shared builder draws the kelvin.ai figure standing and seated", () => {
  const { look, profile } = kelvin();
  const standing = b.buildCharacter({ T, RoundedBoxGeometry }, { profile, look, roaming: true }), seated = b.buildCharacter({ T, RoundedBoxGeometry }, { profile, look, roaming: false });
  assert.ok(standing.parts.legLeft && standing.parts.legRight && standing.parts.arm && standing.parts.leftArm && standing.parts.head);
  assert.equal(seated.parts.legLeft, undefined);
  const box = new T.Box3().setFromObject(standing.group), size = box.getSize(new T.Vector3());
  assert.ok(size.y > 2 && size.y < 2.4, "figure height " + size.y); assert.ok(Math.abs(box.min.y + b.FIGURE_FOOT_OFFSET) < .1, "feet sit at the documented offset " + box.min.y);
  b.walkPose(standing.parts, .4, 1); assert.notEqual(standing.parts.legLeft!.rotation.x, 0); b.walkPose(standing.parts, .4, 0); assert.equal(standing.parts.legLeft!.rotation.x, 0);
  let disposed = 0; const original = T.BufferGeometry.prototype.dispose; T.BufferGeometry.prototype.dispose = function (this: T.BufferGeometry) { disposed++; return original.call(this); }; standing.dispose(); T.BufferGeometry.prototype.dispose = original; assert.ok(disposed > 20);
  seated.dispose();
});
test("office and home both draw people through the shared builder", () => {
  const office = fs.readFileSync(path.resolve(web, "components/office/office-character-model.tsx"), "utf8"), home = fs.readFileSync(path.resolve(web, "components/home-design/apartment.html"), "utf8");
  assert.match(office, /buildCharacter/); assert.doesNotMatch(office, /capsuleGeometry|shirtFront/, "no second copy of the body in the office");
  assert.match(home, /character-builder\.mjs/); assert.match(home, /kelvin-look\.json/);
});
