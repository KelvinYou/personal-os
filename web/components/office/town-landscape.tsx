"use client";

// The town around the Lab and Finance (docs/design/office-world.md): grass, paths,
// a plaza with a round planter, trees, shrubs, flower beds, lamps and benches.
// Original low-poly primitives with flat shading; positions come from
// lib/office-departments.ts. Repeated parts are instanced (one draw call per part).
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { Color, ConeGeometry, CylinderGeometry, IcosahedronGeometry, Matrix4, Object3D, type InstancedMesh } from "three";
import { bushes, flowerBeds, GROUND, lamps, paths, PLANTER, plazaBenches, trees } from "@/lib/office-departments";
import { townPalette } from "@/lib/office-palette";
import { KenneyAsset } from "./kenney-office-assets";


type Placement = { x: number; y: number; z: number; sx: number; sy?: number; sz?: number; color: string; yaw?: number };

/** One instanced mesh for many copies of one shape, each with its own transform and colour. */
function Instances({ geometry, items, flat = true, cast = true }: { geometry: InstanceType<typeof IcosahedronGeometry | typeof ConeGeometry | typeof CylinderGeometry>; items: Placement[]; flat?: boolean; cast?: boolean }) {
  const ref = useRef<InstancedMesh>(null);
  useLayoutEffect(() => {
    const mesh = ref.current; if (!mesh) return;
    const dummy = new Object3D(), color = new Color();
    items.forEach((p, i) => {
      dummy.position.set(p.x, p.y, p.z); dummy.rotation.set(0, p.yaw ?? 0, 0); dummy.scale.set(p.sx, p.sy ?? p.sx, p.sz ?? p.sx); dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix); mesh.setColorAt(i, color.set(p.color));
    });
    mesh.instanceMatrix.needsUpdate = true; if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.computeBoundingSphere();
  }, [items]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return <instancedMesh ref={ref} args={[geometry, undefined, items.length]} castShadow={cast} receiveShadow><meshStandardMaterial flatShading={flat} roughness={.95} /></instancedMesh>;
}

function Greenery() {
  const geometry = useMemo(() => ({ trunk: new CylinderGeometry(.12, .16, 1, 7), round: new IcosahedronGeometry(1, 0), pine: new ConeGeometry(1, 1, 7), bush: new IcosahedronGeometry(1, 0), flower: new IcosahedronGeometry(1, 0) }), []);
  const items = useMemo(() => {
    const trunk: Placement[] = [], round: Placement[] = [], pine: Placement[] = [], bush: Placement[] = [], flower: Placement[] = [];
    for (const t of trees) {
      const h = 1.6 * t.scale;
      trunk.push({ x: t.x, y: h / 2, z: t.z, sx: t.scale, sy: h, color: townPalette.trunk });
      if (t.kind === "round") {
        round.push({ x: t.x, y: h + 1.1 * t.scale, z: t.z, sx: 1.5 * t.scale, sy: 1.35 * t.scale, color: townPalette.leaves[t.tint], yaw: t.x });
        round.push({ x: t.x + .35 * t.scale, y: h + 1.9 * t.scale, z: t.z - .2 * t.scale, sx: 1 * t.scale, color: townPalette.leaves[(t.tint + 1) % 3], yaw: t.z });
      } else {
        pine.push({ x: t.x, y: h + 1.1 * t.scale, z: t.z, sx: 1.35 * t.scale, sy: 2.2 * t.scale, color: townPalette.pine[t.tint] });
        pine.push({ x: t.x, y: h + 2.4 * t.scale, z: t.z, sx: .95 * t.scale, sy: 1.8 * t.scale, color: townPalette.pine[(t.tint + 1) % 3] });
      }
    }
    for (const b of bushes) bush.push({ x: b.x, y: .45 * b.scale, z: b.z, sx: .75 * b.scale, sy: .6 * b.scale, color: townPalette.leaves[b.tint], yaw: b.x + b.z });
    // Flowers: a deterministic grid inside each bed, colours cycling by bed.
    flowerBeds.forEach((bed, n) => {
      const columns = Math.max(2, Math.round(bed.width / .45)), rows = Math.max(2, Math.round(bed.depth / .45));
      for (let i = 0; i < columns; i++) for (let j = 0; j < rows; j++) {
        const x = bed.x - bed.width / 2 + (i + .5) * bed.width / columns, z = bed.z - bed.depth / 2 + (j + .5) * bed.depth / rows;
        bush.push({ x, y: .22, z, sx: .2, sy: .16, color: townPalette.leaves[(i + j) % 3] });
        flower.push({ x: x + ((i * 7 + j * 3) % 5 - 2) * .03, y: .42, z, sx: .11, color: townPalette.flowers[(n + i + j) % townPalette.flowers.length] });
      }
    });
    return { trunk, round, pine, bush, flower };
  }, []);
  return <group name="town-greenery">
    <Instances geometry={geometry.trunk} items={items.trunk} flat={false} />
    <Instances geometry={geometry.round} items={items.round} />
    <Instances geometry={geometry.pine} items={items.pine} />
    <Instances geometry={geometry.bush} items={items.bush} />
    <Instances geometry={geometry.flower} items={items.flower} cast={false} />
  </group>;
}

function Lamp({ x, z }: { x: number; z: number }) {
  return <group position={[x, 0, z]}>
    <mesh position={[0, 1.6, 0]} castShadow><cylinderGeometry args={[.06, .09, 3.2, 10]} /><meshStandardMaterial color={townPalette.lamp} roughness={.8} /></mesh>
    <mesh position={[0, 3.3, 0]}><boxGeometry args={[.42, .3, .42]} /><meshStandardMaterial color={townPalette.glow} emissive={townPalette.glow} emissiveIntensity={.35} roughness={.6} /></mesh>
    <mesh position={[0, 3.5, 0]}><coneGeometry args={[.36, .22, 4]} /><meshStandardMaterial color={townPalette.lamp} flatShading roughness={.8} /></mesh>
  </group>;
}

export function TownLandscape() {
  return <group name="town-landscape">
    {/* Grass sits just below the building floors (y −0.015) so the floors read as slabs on the lawn. */}
    <mesh position={[GROUND.x, -.09, GROUND.z]} receiveShadow><boxGeometry args={[GROUND.width, .12, GROUND.depth]} /><meshStandardMaterial color={townPalette.grass} roughness={1} /></mesh>
    <mesh position={[GROUND.x, -.32, GROUND.z]}><boxGeometry args={[GROUND.width + .6, .35, GROUND.depth + .6]} /><meshStandardMaterial color={townPalette.soil} roughness={1} /></mesh>
    {paths.map((p, i) => <group key={i}>
      <mesh position={[p.x, -.025, p.z]} receiveShadow><boxGeometry args={[p.width, .03, p.depth]} /><meshStandardMaterial color={townPalette.paving} roughness={.95} /></mesh>
      <mesh position={[p.x, -.03, p.z]}><boxGeometry args={[p.width + .24, .025, p.depth + .24]} /><meshStandardMaterial color={townPalette.kerb} roughness={1} /></mesh>
    </group>)}
    {flowerBeds.map((b, i) => <mesh key={i} position={[b.x, .08, b.z]} receiveShadow castShadow><boxGeometry args={[b.width + .2, .2, b.depth + .2]} /><meshStandardMaterial color={townPalette.kerb} roughness={1} /></mesh>)}
    <mesh position={[PLANTER.x, .22, PLANTER.z]} castShadow receiveShadow><cylinderGeometry args={[PLANTER.radius, PLANTER.radius + .1, .44, 24]} /><meshStandardMaterial color={townPalette.kerb} roughness={.95} /></mesh>
    <mesh position={[PLANTER.x, .46, PLANTER.z]} receiveShadow><cylinderGeometry args={[PLANTER.radius - .15, PLANTER.radius - .15, .05, 24]} /><meshStandardMaterial color={townPalette.soil} roughness={1} /></mesh>
    {plazaBenches.map((b, i) => <KenneyAsset key={i} kind="bench" at={[b.x, 0, b.z]} scale={3.2} yaw={b.yaw} />)}
    {lamps.map((l, i) => <Lamp key={i} x={l.x} z={l.z} />)}
    <Greenery />
  </group>;
}
