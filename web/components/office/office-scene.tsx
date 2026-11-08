"use client";

// Original procedural models/textures for the visual prototype. No remote assets.
import { Button } from "@/components/ui/button";
import { PostsBoard } from "./posts-board";
import type { PostSummary } from "@/lib/office-posts-contract";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { ContactShadows, OrbitControls, RoundedBox } from "@react-three/drei";
import { BufferGeometry, CatmullRomCurve3, CanvasTexture, Float32BufferAttribute, MathUtils, PCFShadowMap, RepeatWrapping, Shape, SRGBColorSpace, Vector3, type PerspectiveCamera } from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import type { RoomWorker as OfficeSession } from "@/lib/office-room";
import { workerName, type OfficeState } from "@/lib/office-contract";
import { OfficePerson as Person } from "./office-character-model";
import { stateLabels } from "./office-status";
import { CameraBlend, InteractWatch, OverviewPlayer, PlayerCamera, PlayerHud, useOfficePlayer } from "./office-player";
import { STANDARD } from "@/lib/scene-standard.mjs";
import { neighborhoods, amenities, coffeePosts, groundOutline, hostSeat, seatLayout, skillSeat, tableSeats, villagePaths, type GroundPoint } from "@/lib/office-layout";

import { deskAt, officeDepth, deskAngle, seatedAt, type V3 } from "@/lib/office-life";
type LabelPoint = [number, number, number, number];
type SceneProps = { posts?: PostSummary[]; onOpenPosts?: () => void; skillCatalog?: string[]; workers: OfficeSession[]; selectedId: string | null; animate: boolean; cameraCommand: { command: string; sequence: number }; onSelect: (id: string) => void; onDeselect: () => void };
const cream = "#ede6d6";
const walnut = "#b98a57";
const metal = "#464d49";

function Block({ at, size, color = cream, round = 0, rotation, children }: { at: V3; size: V3; color?: string; round?: number; rotation?: V3; children?: React.ReactNode }) {
  return round ? <RoundedBox args={size} radius={round} smoothness={3} position={at} rotation={rotation} castShadow receiveShadow><meshStandardMaterial color={color} roughness={0.72} />{children}</RoundedBox> : <mesh position={at} rotation={rotation} castShadow receiveShadow><boxGeometry args={size} /><meshStandardMaterial color={color} roughness={0.8} />{children}</mesh>;
}

function Cylinder({ at, radius, height, color, top }: { at: V3; radius: number; height: number; color: string; top?: number }) {
  return <mesh position={at} castShadow receiveShadow><cylinderGeometry args={[top ?? radius, radius, height, 24]} /><meshStandardMaterial color={color} roughness={0.8} /></mesh>;
}

function Plant({ at, scale = 1, pot = "#e4d5bc" }: { at: V3; scale?: number; pot?: string }) {
  return <group position={at} scale={scale}>
    <Cylinder at={[0, 0.22, 0]} radius={0.21} top={0.27} height={0.44} color={pot} />
    <Cylinder at={[0, 0.435, 0]} radius={0.24} height={0.025} color="#584839" />
    <Cylinder at={[0, 0.8, 0]} radius={0.018} height={0.8} color="#687348" />
    {Array.from({ length: 9 }, (_, i) => { const a = i * 2.4; return <group key={i} position={[Math.cos(a) * 0.13, 0.65 + i * 0.075, Math.sin(a) * 0.13]} rotation={[Math.cos(a) * 0.55, a, -0.5]}><mesh position={[0.12, 0, 0]} scale={[0.26, 0.065, 0.11]} castShadow><sphereGeometry args={[1, 10, 6]} /><meshStandardMaterial color={["#71864b", "#829559", "#536d41"][i % 3]} roughness={0.9} /></mesh></group>; })}
  </group>;
}

function Mug({ at, color = "#e6e2d3" }: { at: V3; color?: string }) {
  return <group position={at}><Cylinder at={[0, 0.1, 0]} radius={0.085} height={0.2} color={color} /><Cylinder at={[0, 0.202, 0]} radius={0.067} height={0.007} color="#564438" /><mesh position={[0.092, 0.11, 0]} rotation={[0, Math.PI / 2, 0]}><torusGeometry args={[0.057, 0.018, 8, 18]} /><meshStandardMaterial color={color} /></mesh></group>;
}

function useWoodTexture() {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas"); canvas.width = 512; canvas.height = 128;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#dcc4a2"; ctx.fillRect(0, 0, 512, 128);
    let seed = 17; const random = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    for (let i = 0; i < 180; i++) { const y = random() * 128; ctx.strokeStyle = `rgba(111,72,34,${random() * 0.09})`; ctx.lineWidth = random() * 1.5; ctx.beginPath(); ctx.moveTo(0, y); ctx.bezierCurveTo(170, y + random() * 4, 350, y - random() * 4, 512, y + 2); ctx.stroke(); }
    const result = new CanvasTexture(canvas); result.colorSpace = SRGBColorSpace; result.anisotropy = 4; return result;
  }, []);
  useEffect(() => () => texture.dispose(), [texture]);
  return texture;
}

function OfficeSign({ at, title, subtitle, width = 2.4, rotation = [0, 0, 0] }: { at: V3; title: string; subtitle: string; width?: number; rotation?: V3 }) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas"); canvas.width = 768; canvas.height = 256;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#e7dfc9"; ctx.fillRect(0, 0, 768, 256);
    ctx.strokeStyle = "#446658"; ctx.lineWidth = 8; ctx.strokeRect(13, 13, 742, 230);
    ctx.textAlign = "center"; ctx.fillStyle = "#294c40"; ctx.font = "600 66px sans-serif"; ctx.fillText(title, 384, 116);
    ctx.fillStyle = "#876f4d"; ctx.font = "29px sans-serif"; ctx.fillText(subtitle, 384, 181);
    const value = new CanvasTexture(canvas); value.colorSpace = SRGBColorSpace; return value;
  }, [title, subtitle]);
  useEffect(() => () => texture.dispose(), [texture]);
  return <mesh position={at} rotation={rotation}><planeGeometry args={[width, width / 3]} /><meshStandardMaterial map={texture} roughness={.9} /></mesh>;
}

function Bookshelf({ at, depth }: { at: V3; depth: number }) {
  return <group position={at}>
    <Block at={[0, 1.1, 0]} size={[.65, 2.2, depth]} color="#aa875f" />
    {[.45, 1.1, 1.75].map(y => <group key={y}>
      <Block at={[.02, y, 0]} size={[.69, .06, depth + .04]} color="#d8b88c" />
      {Array.from({ length: Math.floor(depth / .19) }, (_, i) => <Block key={i} at={[.1, y + .22, -depth / 2 + .16 + i * .19]} size={[.48, .36 + (i % 3) * .04, .12]} color={["#728e80", "#c5ae89", "#a77962", "#91a7aa"][i % 4]} />)}
    </group>)}
  </group>;
}

function useGrassTexture() {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas"); canvas.width = canvas.height = 512;
    const context = canvas.getContext("2d")!; context.fillStyle = "#e1e5ce"; context.fillRect(0, 0, 512, 512);
    let seed = 31;
    const random = () => { seed = seed * 16807 % 2147483647; return seed / 2147483647; };
    for (let i = 0; i < 26; i++) {
      const x = random() * 512, y = random() * 512, r = 60 + random() * 110, g = context.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, i % 2 ? "rgba(98,110,60,.16)" : "rgba(255,250,215,.2)"); g.addColorStop(1, "rgba(255,255,255,0)");
      context.fillStyle = g; context.fillRect(0, 0, 512, 512);
    }
    for (let i = 0; i < 6500; i++) {
      const x = random() * 512, y = random() * 512;
      context.strokeStyle = i % 2 ? "rgba(66,85,35,.065)" : "rgba(255,255,225,.14)";
      context.lineWidth = .6; context.beginPath(); context.moveTo(x, y); context.lineTo(x + random() * 2 - 1, y - random() * 3 - 1); context.stroke();
    }
    const result = new CanvasTexture(canvas); result.colorSpace = SRGBColorSpace;
    result.wrapS = result.wrapT = RepeatWrapping; result.repeat.set(.07, .07); result.anisotropy = 4; return result;
  }, []);
  useEffect(() => () => texture.dispose(), [texture]);
  return texture;
}

function TownSign({ at, title, width = 4, ratio = 7.11 }: { at: V3; title: string; width?: number; ratio?: number }) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas"); canvas.width = 1024; canvas.height = Math.round(1024 / ratio);
    const context = canvas.getContext("2d")!;
    context.fillStyle = "#eee7d6"; context.fillRect(0, 0, 1024, canvas.height);
    context.fillStyle = "#405348"; context.textAlign = "center"; context.font = `600 ${Math.round(canvas.height * .53)}px sans-serif`;
    context.fillText(title, 512, canvas.height * .7, 950);
    const result = new CanvasTexture(canvas); result.colorSpace = SRGBColorSpace; return result;
  }, [title, ratio]);
  useEffect(() => () => texture.dispose(), [texture]);
  return <mesh position={at}><planeGeometry args={[width, width / ratio]} /><meshStandardMaterial map={texture} roughness={.9} /></mesh>;
}

function PathRibbon({ points, width, closed, y, color }: { points: GroundPoint[]; width: number; closed: boolean; y: number; color: string }) {
  const geometry = useMemo(() => {
    const curve = new CatmullRomCurve3(points.map(([x, z]) => new Vector3(x, y, z)), closed, "centripetal");
    const positions: number[] = [], indices: number[] = [], steps = 96;
    for (let i = 0; i <= steps; i++) {
      const p = curve.getPoint(i / steps), tangent = curve.getTangent(i / steps);
      const dx = -tangent.z * width / 2, dz = tangent.x * width / 2;
      positions.push(p.x + dx, p.y, p.z + dz, p.x - dx, p.y, p.z - dz);
      if (i < steps) { const v = i * 2; indices.push(v, v + 2, v + 1, v + 1, v + 2, v + 3); }
    }
    const result = new BufferGeometry(); result.setAttribute("position", new Float32BufferAttribute(positions, 3)); result.setIndex(indices); result.computeVertexNormals(); return result;
  }, [points, width, closed, y]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return <mesh geometry={geometry} receiveShadow><meshStandardMaterial color={color} roughness={1} side={2} /></mesh>;
}

// A pale kerb ribbon under the paving gives the path an edge instead of a floating strip.
function GardenPath({ points, width, closed = false }: { points: GroundPoint[]; width: number; closed?: boolean }) {
  return <group>
    <PathRibbon points={points} width={width + .22} closed={closed} y={.012} color="#cdbf9f" />
    <PathRibbon points={points} width={width} closed={closed} y={.034} color="#e9dcc3" />
  </group>;
}

function GardenTree({ x, z, scale = 1 }: { x: number; z: number; scale?: number }) {
  return <group position={[x, 0, z]} scale={scale}>
    <Cylinder at={[0, 1.65, 0]} radius={.2} top={.11} height={3.3} color="#93734e" />
    {[-1, 1].map(side => <Block key={side} at={[side * .42, 2.75, 0]} size={[.13, 1.5, .15]} color="#93734e" rotation={[0, 0, side * -.6]} />)}
    {[[0, 4.25, 0, 1.65], [-1.15, 3.65, .2, 1.35], [1.2, 3.75, .1, 1.45], [-.3, 3.7, 1, 1.35], [.4, 3.9, -1, 1.3]].map(([a, b, c, radius], i) => <mesh key={i} position={[a, b, c]} scale={[1, .8, 1]} castShadow><sphereGeometry args={[radius, 28, 20]} /><meshStandardMaterial color={["#7a8c4e", "#869a58", "#6b8244"][i % 3]} roughness={1} /></mesh>)}
  </group>;
}

function Pavilion({ zone, walking, wood }: { zone: typeof neighborhoods[number]; walking: boolean; wood: CanvasTexture }) {
  const { x, z, width, depth } = zone, back = z - depth / 2, front = z + depth / 2;
  return <group>
    <mesh position={[x, -.005, z]} receiveShadow><boxGeometry args={[width, .035, depth]} /><meshStandardMaterial map={wood} color="#f3e8d3" roughness={.9} /></mesh>
    <Block at={[x, 1.85, back]} size={[width, 3.7, .18]} color="#e8ddc7" />
    {[-1, 1].map(side => <group key={side}>
      <Block at={[x + side * width / 2, .5, z]} size={[.18, 1, depth]} color="#e8ddc7" />
      <Block at={[x + side * width / 2, 3.2, z]} size={[.18, .4, depth]} color="#e8ddc7" />
      <mesh position={[x + side * width / 2, 2, z]}><boxGeometry args={[.025, 2, depth - .35]} /><meshStandardMaterial color="#d0ded0" transparent opacity={.12} depthWrite={false} roughness={.7} /></mesh>
      {[-1, 0, 1].map(end => <Block key={end} at={[x + side * (width / 2 - .015), 2, z + end * (depth / 2 - .12)]} size={[.22, 2.2, .16]} color="#8d9a7b" />)}
      <Block at={[x + side * (width / 2 - .12), 1.85, front]} size={[.24, 3.7, .24]} color="#bb986b" round={.04} />
      <Block at={[x + side * (width / 2 - .12), 3.7, z]} size={[.24, .18, depth]} color="#bb986b" />
    </group>)}
    <Block at={[x, walking ? 3.46 : 3.6, front]} size={[width + .25, walking ? .62 : .5, .28]} color="#a9ae92" round={.03} />
    <Block at={[x, 3.84, walking ? z : back + depth * .17]} size={[width + .55, .09, walking ? depth + .55 : depth * .34]} color="#a3ab8c" round={.03} />
    <TownSign at={[x, walking ? 3.46 : 3.6, front + .15]} title={zone.title} ratio={10} width={zone.width > 10 ? zone.id === "library" ? 7.5 : 6 : zone.width - 1.4} />
    {zone.width > 10 && [-1, 1].map(side => <Block key={side} at={[x + side * width * .25, 3.2, back + 1]} size={[2.4, .055, .12]} color="#f1d9a2" />)}
    <Plant at={[x - width / 2 + .65, 0, front - .7]} scale={.9} pot="#bf9573" />
    <Plant at={[x + width / 2 - .65, 0, front - .7]} scale={.85} pot="#bb946e" />
  </group>;
}

function VillageChair({ at, yaw = 0, color = "#d9cfb5" }: { at: V3; yaw?: number; color?: string }) {
  return <group position={at} rotation={[0, yaw, 0]}>
    {[-.22, .22].flatMap(x => [-.2, .2].map(z => <Block key={`${x}:${z}`} at={[x, .28, z]} size={[.06, .55, .06]} color="#a58b65" />))}
    <Block at={[0, .58, 0]} size={[.55, .12, .6]} color={color} round={.04} />
    <Block at={[0, .98, -.26]} size={[.55, .72, .1]} color={color} round={.04} />
  </group>;
}

function ReadingSeat({ at }: { at: V3 }) {
  return <group position={at}>
    <VillageChair at={[-.05, .17, 1.2]} yaw={Math.PI} color="#aab79c" />
    {[-.4, .3].map(x => <Block key={x} at={[x, 1.02, 1.2]} size={[.12, .2, .7]} color="#aab79c" round={.04} />)}
    <Cylinder at={[-1, .56, .3]} radius={.275} height={.07} color="#c7a478" />
    <Cylinder at={[-1, .26, .3]} radius={.06} height={.52} color="#aa8a63" />
    <Mug at={[-1, .6, .3]} />
  </group>;
}

function Gym() {
  const rack = amenities.rack, weights = amenities.weights, bench = amenities.trainingBench;
  return <group>
    <Block at={[10, .035, 10.6]} size={[2.4, .035, 2.8]} color="#8c9e7b" round={.06} />
    <group position={[rack.x, 0, rack.z]}>
      {[-1.15, 1.15].map(x => <group key={x}>
        <Block at={[x, 1.35, 0]} size={[.11, 2.7, .11]} color="#515a50" />
        <Block at={[x, .06, 0]} size={[.3, .12, 1.4]} color="#515a50" />
        {[.6, 1, 1.4, 1.8, 2.2].map(y => <Block key={y} at={[x, y, .06]} size={[.035, .04, .015]} color="#a5ab98" />)}
      </group>)}
      <Block at={[0, 2.65, 0]} size={[2.4, .1, .1]} color="#515a50" />
      <group position={[0, 1.65, .25]} rotation={[0, 0, Math.PI / 2]}>
        <Cylinder at={[0, 0, 0]} radius={.035} height={3.2} color="#afb6a7" />
        {[-1, 1].flatMap(side => [0, 1].map(i => <Cylinder key={`${side}:${i}`} at={[0, side * (1.15 + i * .13), 0]} radius={i ? .27 : .33} height={.11} color="#555c50" />))}
      </group>
    </group>
    <group position={[weights.x, 0, weights.z]}>
      {[.42, .9].map(y => <group key={y}>
        <Block at={[0, y, 0]} size={[weights.width, .08, weights.depth]} color="#58614f" />
        {[-.8, -.3, .3, .8].map(z => <group key={z} position={[0, y + .16, z]}>
          <Block at={[0, 0, 0]} size={[.5, .06, .06]} color="#aeb5a5" />
          {[-.2, .2].map(x => <mesh key={x} position={[x, 0, 0]}><boxGeometry args={[.17, .24, .24]} /><meshStandardMaterial color="#555b4d" /></mesh>)}
        </group>)}
      </group>)}
      {[-.9, .9].map(z => <Block key={z} at={[0, .45, z]} size={[.1, .9, .1]} color="#58614f" />)}
    </group>
    <Block at={[bench.x, .63, bench.z]} size={[bench.width, .18, bench.depth]} color="#56614f" round={.045} />
    {[-.6, .6].map(z => <Block key={z} at={[bench.x, .3, bench.z + z]} size={[.6, .6, .1]} color="#69705d" />)}
    <Block at={[8, 2, 5.15]} size={[3.4, 1.6, .09]} color="#ba9f76" />
    <Block at={[8, 2, 5.21]} size={[3.2, 1.4, .025]} color="#eee6d2" />
    {Array.from({ length: 7 }, (_, i) => <Block key={i} at={[6.65 + i * .45, 2, 5.24]} size={[.36, 1, .02]} color={i % 3 ? "#d1d8b8" : "#bdc8a6"} />)}
    <TownSign at={[8, 2.59, 5.25]} title="WEEKLY PLAN" width={2.25} />
    <mesh position={[10.65, .23, 11.1]} castShadow><sphereGeometry args={[.22, 12, 8]} /><meshStandardMaterial color="#626d53" /></mesh>
    <mesh position={[10.65, .48, 11.1]}><torusGeometry args={[.13, .035, 6, 12]} /><meshStandardMaterial color="#626d53" /></mesh>
  </group>;
}

function TownAmenities({ walking }: { walking: boolean }) {
  const table = amenities.project, bench = amenities.bench, pantry = amenities.pantry;
  return <group>
    <GardenTree x={amenities.tree.x} z={amenities.tree.z} />
    <GardenTree x={amenities.treeWest.x} z={amenities.treeWest.z} scale={1.1} />
    <GardenTree x={amenities.treeEast.x} z={amenities.treeEast.z} scale={1.1} />
    <Cylinder at={[table.x, .8, table.z]} radius={table.width / 2} height={.12} color="#c5a277" />
    <Cylinder at={[table.x, .39, table.z]} radius={.12} height={.78} color="#a88961" />
    <Plant at={[table.x, .87, table.z]} scale={.35} pot="#bd9571" />
    {tableSeats.map((seat, i) => <VillageChair key={i} at={[seat.x, 0, seat.z]} yaw={seat.yaw} />)}
    <Block at={[bench.x, .5, bench.z]} size={[bench.width, .12, bench.depth]} color="#be9c70" round={.03} />
    {[.88, 1.12].map(y => <Block key={y} at={[bench.x, y, bench.z - .34]} size={[bench.width, .19, .08]} color="#be9c70" />)}
    {[-1, 1].map(side => <Block key={side} at={[bench.x + side * .95, .25, bench.z]} size={[.08, .5, .65]} color="#a38a62" />)}
    <Bookshelf at={[amenities.library.x, 0, amenities.library.z]} depth={amenities.library.depth} />
    <group position={[amenities.archive.x, 0, amenities.archive.z]} rotation={[0, Math.PI, 0]}><Bookshelf at={[0, 0, 0]} depth={amenities.archive.depth} /></group>
    <Block at={[-11, 2, -13.85]} size={[5.5, 1.8, .09]} color="#b79d76" />
    <Block at={[-11, 2, -13.78]} size={[5.3, 1.6, .04]} color="#eee7d5" />
    {[-1.5, 0, 1.5].map((x, i) => <Block key={x} at={[-11 + x, 2 + (i % 2) * .2, -13.74]} size={[1.15, .6, .025]} color={i === 1 ? "#a7bba9" : "#d5c39f"} />)}
    <group position={[amenities.travelMap.x, 1.9, amenities.travelMap.z]}>
      <Block at={[0, 0, 0]} size={[4.5, 2, .13]} color="#b49b77" />
      <Block at={[0, 0, .08]} size={[4.3, 1.8, .025]} color="#e5dfc6" />
      {[-1.3, -.5, .4, 1.3].map((x, i) => <mesh key={i} position={[x, (i % 2) * .45 - .2, .11]} scale={[.55, .4, .01]}><icosahedronGeometry args={[1, 0]} /><meshStandardMaterial color="#a1b489" flatShading /></mesh>)}
    </group>
    <Block at={[-15, .45, 6.5]} size={[.65, .9, .35]} color="#a77e57" round={.07} />
    <Block at={[-15, .93, 6.5]} size={[.28, .12, .12]} color="#6f785a" round={.025} />
    <Gym />
    <Block at={[pantry.x, .55, pantry.z]} size={[pantry.width, 1.1, pantry.depth]} color="#b59a71" round={.04} />
    <Block at={[pantry.x, 1.13, pantry.z]} size={[pantry.width + .08, .08, pantry.depth]} color="#ead7b8" />
    <Block at={[-4.5, 1.48, 12]} size={[.6, .63, .48]} color="#5a6252" round={.04} />
    <Mug at={[-4.5, 1.18, 11.75]} /><Mug at={[-1.4, 1.18, 11.75]} color="#c8a48a" />
    {coffeePosts.map((post, i) => <Block key={i} at={[post.x, 1.6, post.z]} size={[.2, 3.2, .2]} color="#b6986e" />)}
    <Block at={[-3, 3.3, walking ? 12.5 : 11.1]} size={[5.85, .16, walking ? 3.5 : .7]} color="#919b7b" round={.025} />
    <Block at={[-3, 3.12, 14]} size={[5.85, .2, .2]} color="#a5aa8c" />
    <TownSign at={[-3, 2.83, 14.13]} title="KOPI & TEH" width={3.2} />
    {[amenities.hostChair, amenities.coffeeStoolLeft, amenities.coffeeStoolRight].map((stool, i) => <group key={i}>
      <Cylinder at={[stool.x, .74, stool.z]} radius={.26} height={.1} color="#c3a57a" />
      {[-.16, .16].flatMap(x => [-.16, .16].map(z => <Block key={`${x}:${z}`} at={[stool.x + x, .36, stool.z + z]} size={[.045, .7, .045]} color="#a38a64" />))}
    </group>)}
    {neighborhoods.flatMap((zone, i) => [-1, 1].map(side => <group key={`${i}:${side}`} position={[zone.x + side * (zone.width / 2 + .65), 0, zone.z + zone.depth / 2 - .7]}>
      {[-1, 0, 1].map(j => <group key={`leaf-${j}`} rotation={[0, j * 1.2, 0]}>
        <mesh position={[.1, .72, .1]} rotation={[0, 0, j * .28]} scale={[.14, .85, .17]} castShadow><sphereGeometry args={[1, 8, 4]} /><meshStandardMaterial color={j % 2 ? "#71884e" : "#849959"} roughness={1} /></mesh>
        {j !== 0 && <><Cylinder at={[j * .15, .63, .1]} radius={.018} height={1.25} color="#859a57" /><Block at={[j * .15, 1.28, .1]} size={[.09, .3, .14]} rotation={[0, 0, -.4]} color="#d4ad5e" /></>}
      </group>)}
      {[0, 1, 2].map(j => <mesh key={j} position={[(j - 1) * .4, .35 + (j % 2) * .1, (j % 2) * .3]} scale={[.7, .55, .6]} castShadow><sphereGeometry args={[.7, 20, 14]} /><meshStandardMaterial color={["#9aa86c", "#a6b37b", "#8e9f63"][j]} roughness={1} /></mesh>)}
    </group>))}
  </group>;
}

function Room({ count, walking }: { count: number; walking: boolean }) {
  const wood = useWoodTexture(), grass = useGrassTexture();
  const ground = useMemo(() => {
    const shape = new Shape(), outline = groundOutline(count);
    outline.forEach(([x, z], i) => i ? shape.lineTo(x, -z) : shape.moveTo(x, -z)); shape.closePath(); return shape;
  }, [count]);
  return <group>
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -.018, 0]} receiveShadow><shapeGeometry args={[ground]} /><meshStandardMaterial map={grass} color="#a6ab80" roughness={1} side={2} /></mesh>
    {villagePaths.map((path, i) => <GardenPath key={i} {...path} />)}
    {neighborhoods.map(zone => <Pavilion key={zone.id} zone={zone} walking={walking} wood={wood} />)}
    {Array.from({ length: count }, (_, i) => <group key={i} position={deskAt(i)} rotation={[0, deskAngle(i), 0]}>
      {seatLayout(i).kind === "reading" ? <ReadingSeat at={[0, 0, 0]} /> : <Desk at={[0, 0, 0]} study={seatLayout(i).kind === "study"} />}
    </group>)}
    <TownAmenities walking={walking} />
  </group>;
}
const MemoRoom = memo(Room);

function Monitor({ at, angle = 0 }: { at: V3; angle?: number }) {
  return <group position={at} rotation={[0, angle, 0]}>
    <Block at={[0, 0, 0]} size={[0.49, 0.035, 0.25]} color="#666c65" round={0.012} />
    <Block at={[0, 0.17, -0.03]} size={[0.065, 0.35, 0.07]} color="#626960" />
    <Block at={[0, 0.53, -0.025]} size={[1.03, 0.66, 0.06]} color="#363f3e" round={0.035} />
    <Block at={[0, 0.54, 0.009]} size={[0.95, 0.56, 0.008]} color="#213b3e" />
    <Block at={[-0.39, 0.54, 0.017]} size={[0.13, 0.56, 0.003]} color="#294a4c" />
    {Array.from({ length: 7 }, (_, i) => <Block key={i} at={[-0.22 + (i % 3) * 0.035, 0.73 - i * 0.064, 0.019]} size={[0.15 + (i % 3) * 0.07, 0.015, 0.004]} color={["#84b5aa", "#ceb98b", "#73a0ad"][i % 3]} />)}
  </group>;
}

function MacBookPro() {
  return <group position={[-.68, 1.3, .23]} rotation={[0, .08, 0]}>
    <Block at={[0, .025, 0]} size={[.62, .035, .43]} color="#a7abb0" round={.018} />
    <Block at={[0, .046, -.05]} size={[.52, .01, .19]} color="#30343a" round={.012} />
    {[0, 1, 2, 3].map(r => Array.from({ length: 9 }, (_, c) => <Block key={`${r}-${c}`} at={[-.22 + c * .055, .054, -.12 + r * .044]} size={[.044, .006, .032]} color="#646b72" />))}
    <Block at={[0, .046, .115]} size={[.23, .007, .13]} color="#bfc3c8" round={.008} />
    <group position={[0, .04, -.2]} rotation={[-.2, 0, 0]}>
      <Block at={[0, .21, 0]} size={[.62, .42, .024]} color="#9da3aa" round={.018} />
      <Block at={[0, .21, .014]} size={[.57, .36, .008]} color="#152d3b" round={.012} />
      <Block at={[0, .385, .02]} size={[.07, .018, .008]} color="#11191d" />
      {[0, 1, 2, 3].map(i => <Block key={i} at={[-.05, .31 - i * .057, .021]} size={[.3 - (i % 2) * .08, .012, .004]} color={i % 2 ? "#baaa83" : "#83b6ac"} />)}
    </group>
  </group>;
}

function Desk({ at, study = false }: { at: V3; study?: boolean }) {
  return <group position={at}>
    <Block at={[0, 1.22, 0]} size={[2.65, 0.13, 1.08]} color="#caa679" round={0.045} />
    {[-1.12, 1.12].map(x => <group key={x}><Block at={[x, 0.61, 0]} size={[0.095, 1.16, 0.83]} color="#7c8172" /><Block at={[x, 0.08, 0]} size={[0.16, 0.08, 0.94]} color="#646c60" round={0.02} /></group>)}
    <MacBookPro />
    {!study && <>
    <Monitor at={[-0.4, 1.3, -0.21]} angle={0.12} />
    <Monitor at={[0.62, 1.3, -0.18]} angle={-0.15} />
    <Block at={[0.28, 1.304, 0.25]} size={[0.7, 0.024, 0.3]} color="#dddccc" round={0.015} />
    {Array.from({ length: 4 }, (_, r) => Array.from({ length: 12 }, (_, c) => <Block key={`${r}-${c}`} at={[-0.01 + c * 0.052, 1.322, 0.15 + r * 0.064]} size={[0.04, 0.009, 0.044]} color={r === 3 && c < 6 ? "#bdc5b6" : "#f0eee0"} />))}
    <Block at={[0.68, 1.3, 0.3]} size={[0.28, 0.012, 0.3]} color="#8b9d8c" round={0.02} />
    <Block at={[0.68, 1.33, 0.3]} size={[0.085, 0.05, 0.14]} color="#eaeadd" round={0.025} />
    </>}
    {study && <Block at={[.55, 1.31, .2]} size={[.55, .04, .4]} color="#e8e0c7" round={.015} />}
    <Mug at={[-1.02, 1.3, 0.24]} color="#9bb2a4" />
    <Plant at={[-1.03, 1.3, -0.28]} scale={0.32} pot="#e9dfca" />
    <group position={[-0.05, 0, 1.2]}>
      <Cylinder at={[0, 0.42, 0]} radius={0.045} height={0.62} color={metal} />
      {[0, 1, 2, 3, 4].map(i => <group key={i} rotation={[0, i * Math.PI * 0.4, 0]}><Block at={[0.2, 0.13, 0]} size={[0.43, 0.055, 0.065]} color={metal} /><mesh position={[0.4, 0.085, 0]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.065, 0.065, 0.06, 12]} /><meshStandardMaterial color="#38413c" /></mesh></group>)}
      <Block at={[0, 0.78, 0]} size={[0.82, 0.17, 0.76]} color="#8c9b8c" round={0.09} />
      <Block at={[0, 1.17, 0.37]} size={[0.81, 0.76, 0.15]} color="#7b8a7a" round={0.09} rotation={[0.12, 0, 0]} />
    </group>
  </group>;
}

function CameraRig({ command, focus, focusId, count }: { count: number; command: SceneProps["cameraCommand"]; focus: V3 | null; focusId: string | null }) {
  const controls = useRef<OrbitControlsImpl>(null);
  const focusRef = useRef(focus);
  const focusIdRef = useRef(focusId);
  focusIdRef.current = focusId;
  focusRef.current = focus;
  const { camera, size, invalidate, scene } = useThree();
  const extra = officeDepth(count) - 40;
  const center = extra / 2;
  // Perspective overview: distance that frames the same ground the old orthographic zoom did.
  const tan = Math.tan(MathUtils.degToRad(STANDARD.overviewFov / 2));
  const fit = Math.max((34 + extra * .7) / 2 / tan, (50 + extra * .7) / 2 / (tan * (size.width / Math.max(1, size.height))));
  const home = useMemo(() => new Vector3(8, 23.3, 40).normalize(), []);
  const closeUp = useMemo(() => new Vector3(10, 7.2, 12).normalize(), []);
  const perspective = camera as PerspectiveCamera;
  const place = (target: V3, distance: number, direction: Vector3) => {
    controls.current?.target.set(...target);
    camera.position.set(target[0], target[1], target[2]).addScaledVector(direction, distance);
  };
  useFrame(() => {
    if (perspective.fov !== STANDARD.overviewFov || perspective.near !== 1) { perspective.fov = STANDARD.overviewFov; perspective.near = 1; perspective.far = 400; perspective.updateProjectionMatrix(); }
  }, -2);
  useEffect(() => {
    perspective.fov = STANDARD.overviewFov; perspective.near = 1; perspective.far = 400; perspective.updateProjectionMatrix();
    place([0, .7, center], fit, home);
    controls.current?.update(); invalidate();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [camera, fit, center, invalidate]);
  useEffect(() => {
    if (!controls.current) return;
    const actor = focusIdRef.current ? scene.getObjectByName(`worker-${focusIdRef.current}`) : null;
    const focus: V3 | null = actor ? [actor.position.x + .05, 0, actor.position.z - 1.25] : focusRef.current;
    const target = controls.current.target;
    if (command.command === "reset") place([0, .7, center], fit, home);
    if (command.command === "focus" && focus) place([focus[0] - 0.05, 1.3, focus[2] + 1.25], fit / 2.1, closeUp);
    if (command.command === "in" || command.command === "out") {
      const factor = command.command === "in" ? 1 / 1.18 : 1.18;
      const distance = MathUtils.clamp(camera.position.distanceTo(target) * factor, fit * .4, fit * 1.43);
      camera.position.sub(target).setLength(distance).add(target);
    }
    controls.current.update(); invalidate();
  // Selection alone must not reset a manually positioned camera.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [command, camera, fit, center, invalidate, scene]);
  return <OrbitControls ref={controls} makeDefault target={[0, .7, center]} minDistance={fit * .4} maxDistance={fit * 1.43} minPolarAngle={0.25} maxPolarAngle={Math.PI / 2.35} minAzimuthAngle={-0.15} maxAzimuthAngle={1.5} enableDamping={false} enablePan panSpeed={0.7} />;
}

function ContextWatch({ onLost }: { onLost: () => void }) {
  const gl = useThree(value => value.gl);
  useEffect(() => {
    const lost = (event: Event) => { event.preventDefault(); onLost(); };
    gl.domElement.addEventListener("webglcontextlost", lost);
    return () => gl.domElement.removeEventListener("webglcontextlost", lost);
  }, [gl, onLost]);
  return null;
}

// Project into the existing DOM tree rather than mounting a nested React root.
function LabelPosition({ workers, seats, onPosition }: { workers: OfficeSession[]; seats: number[]; onPosition: (position: LabelPoint[]) => void }) {
  const last = useRef<LabelPoint[]>([]);
  const point = useMemo(() => new Vector3(), []);
  useFrame(({ camera, size, scene }) => {
    const next: LabelPoint[] = workers.map((worker, i) => {
      const actor = scene.getObjectByName(`worker-${worker.session_id}`);
      const at = seatedAt(seats[i]);
      point.set(actor ? actor.position.x : at[0], 2.65, actor ? actor.position.z : at[2]).project(camera);
      const x = (point.x * .5 + .5) * size.width, y = (-point.y * .5 + .5) * size.height;
      return [x, y, x, y];
    });
    const owner = scene.getObjectByName("worker-kelvin.ai");
    point.set(owner?.position.x ?? hostSeat[0], owner ? owner.position.y + 2.03 : 2.65, owner?.position.z ?? hostSeat[2]).project(camera);
    const ownerX = (point.x * .5 + .5) * size.width, ownerY = (-point.y * .5 + .5) * size.height;
    next.push([ownerX, ownerY, ownerX, ownerY]);
    if (next.length === last.current.length && next.every((p, i) => Math.abs(p[2] - last.current[i][2]) + Math.abs(p[3] - last.current[i][3]) <= .5)) return;
    if (size.width <= 760) for (const label of next) {
      label[0] = MathUtils.clamp(label[0], 66, size.width - 66);
      label[1] = MathUtils.clamp(label[1], 44, size.height - 55);
    }
    if (workers.length > 8 && size.width > 760) {
      const gap = 118;
      const placed: LabelPoint[] = [];
      for (const label of [...next].sort((a, b) => a[1] - b[1])) {
        const candidates: [number, number, number][] = [];
        for (let dx = -12; dx <= 12; dx++) for (let dy = -12; dy <= 12; dy++) {
          const x = MathUtils.clamp(label[2] + dx * gap / 2, gap / 2 + 6, size.width - gap / 2 - 6);
          const y = MathUtils.clamp(label[3] + dy * 40, 44, size.height - 55);
          candidates.push([x, y, (x - label[2]) ** 2 + (y - label[3]) ** 2]);
        }
        const free = candidates.sort((a, b) => a[2] - b[2]).find(([x, y]) => !placed.some(other => Math.abs(other[0] - x) < gap && Math.abs(other[1] - y) < 40));
        if (free) { label[0] = free[0]; label[1] = free[1]; }
        placed.push(label);
      }
    }
    if (next.length !== last.current.length || next.some((p, i) => Math.abs(p[0] - last.current[i][0]) + Math.abs(p[1] - last.current[i][1]) > 0.5)) { last.current = next; onPosition(next); }
  });
  return null;
}

// Project into the host DOM, matching worker labels without a nested React root.
function BoardPosition({ onPosition }: { onPosition: (value: [number, number] | null) => void }) {
  const point = useMemo(() => new Vector3(), []);
  const last = useRef<[number, number] | null>(null);
  useFrame(({ camera, size }) => {
    point.set(amenities.dailyBoard.x, 3.2, amenities.dailyBoard.z).project(camera);
    const next: [number, number] | null = point.z > -1 && point.z < 1 && Math.abs(point.x) < 1 && Math.abs(point.y) < 1
      ? [(point.x * .5 + .5) * size.width, (-point.y * .5 + .5) * size.height] : null;
    if (!next && last.current || next && (!last.current || Math.abs(next[0] - last.current[0]) + Math.abs(next[1] - last.current[1]) > .5)) { last.current = next; onPosition(next); }
  });
  return null;
}

export default function OfficeScene(props: SceneProps) {
  const navigation = useOfficePlayer();
  const [boardLabel, setBoardLabel] = useState<[number, number] | null>(null);
  const walking = navigation.view !== "overview";
  const [lost, setLost] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const [visible, setVisible] = useState(true);
  const [labels, setLabels] = useState<LabelPoint[]>([]);
  const seats = props.workers.map((worker, index) => skillSeat(worker.skill?.id, index, props.skillCatalog));
  const seatCount = Math.max(18, ...(props.skillCatalog ?? []).map(id => skillSeat(id, 0, props.skillCatalog) + 1), ...seats.map(index => index + 1));
  const focusedIndex = props.workers.findIndex(worker => worker.session_id === props.selectedId);
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    update(); document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  if (lost) return <div className="office-scene-placeholder"><p>The 3D connection was interrupted.</p><Button variant="outline" onClick={() => setLost(false)}>Reopen the room</Button><p>The session list and details are still available.</p></div>;
  return <div {...navigation.bindings} className={`office-canvas-shell ${walking ? "office-player-active" : ""}`}><Canvas camera={{ position: [8, 24, 40], fov: STANDARD.overviewFov, near: 1, far: 400 }} shadows={{ type: PCFShadowMap }} dpr={[1, 1.75]} frameloop={(props.animate || walking) && visible ? "always" : "demand"} gl={{ antialias: true, alpha: true }} onPointerMissed={props.onDeselect} fallback={<div className="office-scene-placeholder">Interactive 3D office. The session list provides a text alternative.</div>}>
    <color attach="background" args={["#f0ede4"]} /><fog attach="fog" args={["#f0ede4", 85, 230]} />
    <ambientLight intensity={.3} color="#fff3df" />
    <hemisphereLight args={["#eaf0ec", "#b9a98c", .8]} />
    <directionalLight position={[-10, 24, 10]} intensity={3.1} color="#fff0d4" castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-34} shadow-camera-right={34} shadow-camera-top={34} shadow-camera-bottom={-34} shadow-camera-near={0.5} shadow-camera-far={70} shadow-bias={-0.0004} shadow-normalBias={0.035} shadow-radius={4} />
    <directionalLight position={[6, 5, 8]} intensity={0.45} color="#e8eeff" />
    <group position={[0, 0, 0]}><MemoRoom count={seatCount} walking={walking} /><PostsBoard posts={props.posts ?? []} onOpen={props.onOpenPosts} />{props.workers.map((worker, i) => <Person key={worker.session_id} skillId={worker.skill?.id} session={worker} selected={worker.session_id === props.selectedId} animate={props.animate && visible && worker.state !== "unknown" && worker.state !== "error"} onSelect={() => props.onSelect(worker.session_id)} index={seats[i]} at={seatedAt(seats[i])} />)}<Person session={{ session_id: "kelvin.ai", state: "idle" }} host selected={false} animate={props.animate && visible} onSelect={() => {}} player={navigation.entered ? navigation.player.current : undefined} hidden={navigation.view === "first"} at={hostSeat} /></group>
    <ContactShadows position={[0, -.06, 0]} opacity={0.32} scale={66} blur={2.8} far={5} resolution={512} frames={1} color="#887b64" />
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -.07, 0]} receiveShadow><planeGeometry args={[200, 200]} /><meshStandardMaterial color="#f8f3e7" roughness={1} /></mesh>
    {navigation.view !== "overview" ? <PlayerCamera player={navigation.player} keys={navigation.keys} controls={navigation} view={navigation.view} count={seatCount} visible={visible} /> : <CameraRig count={seatCount} focusId={props.selectedId} command={props.cameraCommand} focus={focusedIndex >= 0 ? (props.workers[focusedIndex].state === "idle" ? [1, 0, 1] : deskAt(seats[focusedIndex])) : null} />}
    {navigation.view === "overview" && <OverviewPlayer controls={navigation} count={seatCount} />}
    <CameraBlend view={navigation.view} command={props.cameraCommand} />
    {walking && <InteractWatch targets={props.onOpenPosts ? [{ name: "office-posts-board", onInteract: props.onOpenPosts }] : []} controls={navigation} ids={props.workers.map(worker => worker.session_id)} onSelect={props.onSelect} />}
    {props.onOpenPosts && <BoardPosition onPosition={setBoardLabel} />}
    <ContextWatch onLost={() => setLost(true)} />
    {showLabels && !walking && <LabelPosition workers={props.workers} seats={seats} onPosition={setLabels} />}
  </Canvas>{props.onOpenPosts && boardLabel && <Button className="office-posts-board-label" style={{ left: boardLabel[0], top: boardLabel[1] }} onClick={event => { event.stopPropagation(); props.onOpenPosts?.(); }}>Browse posts</Button>}<PlayerHud controls={navigation} />{!walking && <button type="button" className="office-label-toggle" aria-pressed={showLabels} onClick={() => setShowLabels(value => !value)}>Name labels <span aria-hidden="true">{showLabels ? "On" : "Off"}</span></button>}{showLabels && !walking && <><svg className="office-label-leaders" aria-hidden="true">{labels.map((p, i) => <line key={i} x1={p[0]} y1={p[1]} x2={p[2]} y2={p[3]} />)}</svg>{props.workers.map((worker, i) => labels[i] && <button key={worker.session_id} aria-label={`${workerName(worker)}: ${worker.skill?.id ?? worker.agent?.role ?? "Observed session"}: ${worker.standby ? "Standby" : stateLabels[worker.state]}`} className={`office-floating-label state-${worker.state} ${props.workers.length > 1 ? "office-label-multi" : ""} ${props.workers.length > 8 ? "office-label-dense" : ""} ${worker.session_id === props.selectedId ? "office-label-selected" : ""}`} style={{ left: labels[i][0], top: labels[i][1] }} onClick={() => props.onSelect(worker.session_id)}><span /><strong>{workerName(worker)}</strong><i /><span className="office-label-state">{worker.standby ? "Standby" : !worker.skill && worker.agent ? worker.agent.role === "coordinator" ? "Coordinator" : worker.agent.assignment : stateLabels[worker.state]}</span></button>)}{labels[props.workers.length] && <div className="office-floating-label office-host-label" style={{ left: labels[props.workers.length][0], top: labels[props.workers.length][1] }}><strong>kelvin.ai</strong><span>Office owner</span></div>}</>}</div>;
}
