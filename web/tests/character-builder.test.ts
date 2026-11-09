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
  const geometry = new Set<T.BufferGeometry>(); standing.group.traverse(object => { if (object instanceof T.Mesh) geometry.add(object.geometry); });
  const disposed = new Set<T.BufferGeometry>(); for (const g of geometry) g.addEventListener('dispose', () => disposed.add(g));
  standing.dispose(); assert.equal(disposed.size, geometry.size, 'every original mesh is disposed');
  assert.equal(standing.group.userData.asset, look.asset, 'identity selects the official asset');

  seated.dispose();
});
test("office and home both draw people through the shared builder", () => {
  const office = fs.readFileSync(path.resolve(web, "components/office/office-character-model.tsx"), "utf8"), home = fs.readFileSync(path.resolve(web, "components/home-design/apartment.html"), "utf8");
  assert.match(office, /buildCharacter/); assert.doesNotMatch(office, /capsuleGeometry|shirtFront/, "no second copy of the body in the office");
  assert.match(home, /character-builder\.mjs/); assert.match(home, /kelvin-look\.json/);
});

test("every bundled Mini character retains the official GLB triangle count and palette bounds", () => {
  const folder = path.join(web, "public/office-materials/kenney-mini");
  for (const file of fs.readdirSync(folder).filter(name => name.endsWith(".glb"))) {
    const bytes = fs.readFileSync(path.join(folder, file));
    const source = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
    const expected = source.meshes.flatMap((m: { primitives: { indices: number }[] }) => m.primitives)
      .reduce((sum: number, p: { indices: number }) => sum + source.accessors[p.indices].count / 3, 0);
    const figure = b.buildCharacter({ T, RoundedBoxGeometry }, { profile: {}, look: { asset: file.replace(".glb", "") } });
    let triangles = 0;
    figure.group.traverse(object => {
      if (!(object instanceof T.Mesh)) return;
      triangles += object.geometry.attributes.position.count / 3;
      for (const value of object.geometry.attributes.color.array) assert.ok(value >= 0 && value <= 1);
    });
    assert.equal(triangles, expected, file + " keeps all original triangles");
    figure.dispose();
  }
});
