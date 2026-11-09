"use client";

// Local CC0 Kenney assets. Original geometry/colours; provenance beside each pack.
// Furniture is floor-centred; the space shell retains its original modular pivots.
import { useEffect, useMemo, useRef } from "react";
import { useGLTF } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { Box3, Matrix4, Mesh, MeshStandardMaterial, Vector3, type InstancedMesh, type Material } from "three";
import { departments, departmentOrder, type Area } from "@/lib/office-departments";
import assets from "@/lib/office-assets.json";
import type { V3 } from "@/lib/office-life";

const base = "/office-materials/";
type Asset = keyof typeof assets;

export function KenneyAsset({ kind, at = [0, 0, 0], scale = 3.2, yaw = 0, pivot = "floor" }: { kind: Asset; at?: V3; scale?: number | V3; yaw?: number; pivot?: "source" | "floor" }) {
  const { scene } = useGLTF(base + assets[kind]);
  const built = useMemo(() => {
    const object = scene.clone(true), materials: Material[] = [];
    object.traverse(node => {
      if (!(node instanceof Mesh)) return;
      node.castShadow = node.receiveShadow = true;
      const matte = (source: Material) => { const m = source.clone(); if (m instanceof MeshStandardMaterial) { m.roughness = Math.max(.85, m.roughness); m.metalness = 0; } materials.push(m); return m; };
      node.material = Array.isArray(node.material) ? node.material.map(matte) : matte(node.material);
    });
    if (pivot === "floor") { const box = new Box3().setFromObject(object), centre = box.getCenter(new Vector3()); object.position.sub(new Vector3(centre.x, box.min.y, centre.z)); }
    return { object, materials };
  }, [scene, pivot]);
  useEffect(() => () => built.materials.forEach(m => m.dispose()), [built]);
  return <group position={at} scale={scale} rotation={[0, yaw, 0]}><primitive object={built.object} dispose={null} /></group>;
}

function SpaceFloor({ area }: { area: Area }) {
  const { scene } = useGLTF(base + assets.floor);
  const mesh = scene.getObjectByProperty("isMesh", true) as Mesh;
  const ref = useRef<InstancedMesh>(null);
  const { invalidate } = useThree();
  const columns = area.width / 2, rows = area.depth / 2;
  useEffect(() => {
    if (!ref.current) return;
    const matrix = new Matrix4(); let i = 0;
    for (let x = 0; x < columns; x++) for (let z = 0; z < rows; z++) {
      matrix.makeScale(.5, .5, .5).setPosition(area.x - area.width / 2 + 1 + x * 2, -.015, area.z - area.depth / 2 + 1 + z * 2);
      ref.current.setMatrixAt(i++, matrix);
    }
    ref.current.instanceMatrix.needsUpdate = true;
    ref.current.computeBoundingSphere();
    invalidate();
  }, [area, columns, rows, invalidate]);
  return <instancedMesh ref={ref} args={[mesh.geometry, mesh.material, columns * rows]} receiveShadow dispose={null} />;
}

/** Back wall row for one building: 4-unit modules, a half module to finish an odd edge. Never side walls. */
function BackWall({ area, gateAt }: { area: Area; gateAt?: number }) {
  const back = area.z - area.depth / 2, left = area.x - area.width / 2;
  const full = Math.floor(area.width / 4), half = area.width - full * 4 >= 2;
  return <group>
    {Array.from({ length: full }, (_, i) => left + 2 + i * 4).map(x => x === gateAt
      ? <KenneyAsset key={x} kind="gate" at={[x, 0, back - .2]} scale={1} pivot="source" />
      : <KenneyAsset key={x} kind="wall" at={[x, 0, back]} scale={1} yaw={Math.PI} pivot="source" />)}
    {half && <KenneyAsset kind="halfWall" at={[left + full * 4 + 1, 0, back]} scale={1} yaw={Math.PI} pivot="source" />}
  </group>;
}

/** Both buildings' floors and back walls; the landscape around them lives in town-landscape.tsx. */
export function KenneyTownShell() {
  // Suspend until the complete local asset set is ready; no partial blank floor.
  useGLTF(Object.values(assets).map(name => base + name));
  const { gl } = useThree();
  useEffect(() => {
    const shell = document.querySelector(".radar-canvas-shell"); shell?.setAttribute("data-assets-ready", "true");
    return () => shell?.removeAttribute("data-assets-ready");
  }, []);
  useFrame(() => {
    const shell = document.querySelector<HTMLElement>(".radar-canvas-shell");
    if (shell) shell.dataset.renderStats = JSON.stringify({ calls: gl.info.render.calls, triangles: gl.info.render.triangles, geometries: gl.info.memory.geometries, textures: gl.info.memory.textures });
  });
  const { lab, finance } = departments;
  return <group name="kenney-modular-town">
    {departmentOrder.map(id => <group key={id} name={`building-shell-${id}`}><SpaceFloor area={departments[id]} /><BackWall area={departments[id]} gateAt={id === "lab" ? 1 : undefined} /></group>)}
    <KenneyAsset kind="plant" at={[lab.x - lab.width / 2 + .7, 0, lab.z - lab.depth / 2 + 1.6]} scale={2.8} />
    <KenneyAsset kind="plant" at={[finance.x + finance.width / 2 - .7, 0, finance.z - finance.depth / 2 + 1.6]} scale={2.8} />
    <KenneyAsset kind="bin" at={[lab.x + lab.width / 2 - 1.3, 0, 8.8]} scale={2.5} />
  </group>;
}
