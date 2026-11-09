"use client";

// Shared procedural parts for the office scenes (radar and classic town).
// Original geometry; no remote assets. Colours come from the scene palette (3D standard §4).
import { useEffect, useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import { CanvasTexture, SRGBColorSpace } from "three";
import type { V3 } from "@/lib/office-life";

export const cream = "#ede6d6";
export const walnut = "#b98a57";
export const metal = "#464d49";

export function Block({ at, size, color = cream, round = 0, rotation, children }: { at: V3; size: V3; color?: string; round?: number; rotation?: V3; children?: React.ReactNode }) {
  return round ? <RoundedBox args={size} radius={round} smoothness={3} position={at} rotation={rotation} castShadow receiveShadow><meshStandardMaterial color={color} roughness={0.72} />{children}</RoundedBox> : <mesh position={at} rotation={rotation} castShadow receiveShadow><boxGeometry args={size} /><meshStandardMaterial color={color} roughness={0.8} />{children}</mesh>;
}

export function Cylinder({ at, radius, height, color, top }: { at: V3; radius: number; height: number; color: string; top?: number }) {
  return <mesh position={at} castShadow receiveShadow><cylinderGeometry args={[top ?? radius, radius, height, 24]} /><meshStandardMaterial color={color} roughness={0.8} /></mesh>;
}

export function Plant({ at, scale = 1, pot = "#e4d5bc" }: { at: V3; scale?: number; pot?: string }) {
  return <group position={at} scale={scale}>
    <Cylinder at={[0, 0.22, 0]} radius={0.21} top={0.27} height={0.44} color={pot} />
    <Cylinder at={[0, 0.435, 0]} radius={0.24} height={0.025} color="#584839" />
    <Cylinder at={[0, 0.8, 0]} radius={0.018} height={0.8} color="#687348" />
    {Array.from({ length: 9 }, (_, i) => { const a = i * 2.4; return <group key={i} position={[Math.cos(a) * 0.13, 0.65 + i * 0.075, Math.sin(a) * 0.13]} rotation={[Math.cos(a) * 0.55, a, -0.5]}><mesh position={[0.12, 0, 0]} scale={[0.26, 0.065, 0.11]} castShadow><sphereGeometry args={[1, 10, 6]} /><meshStandardMaterial color={["#71864b", "#829559", "#536d41"][i % 3]} roughness={0.9} /></mesh></group>; })}
  </group>;
}

export function Mug({ at, color = "#e6e2d3" }: { at: V3; color?: string }) {
  return <group position={at}><Cylinder at={[0, 0.1, 0]} radius={0.085} height={0.2} color={color} /><Cylinder at={[0, 0.202, 0]} radius={0.067} height={0.007} color="#564438" /><mesh position={[0.092, 0.11, 0]} rotation={[0, Math.PI / 2, 0]}><torusGeometry args={[0.057, 0.018, 8, 18]} /><meshStandardMaterial color={color} /></mesh></group>;
}

export function useWoodTexture() {
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

export function Bookshelf({ at, depth }: { at: V3; depth: number }) {
  return <group position={at}>
    <Block at={[0, 1.1, 0]} size={[.65, 2.2, depth]} color="#aa875f" />
    {[.45, 1.1, 1.75].map(y => <group key={y}>
      <Block at={[.02, y, 0]} size={[.69, .06, depth + .04]} color="#d8b88c" />
      {Array.from({ length: Math.floor(depth / .19) }, (_, i) => <Block key={i} at={[.1, y + .22, -depth / 2 + .16 + i * .19]} size={[.48, .36 + (i % 3) * .04, .12]} color={["#728e80", "#c5ae89", "#a77962", "#91a7aa"][i % 4]} />)}
    </group>)}
  </group>;
}

export function TownSign({ at, title, width = 4, ratio = 7.11 }: { at: V3; title: string; width?: number; ratio?: number }) {
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

export function Monitor({ at, angle = 0 }: { at: V3; angle?: number }) {
  return <group position={at} rotation={[0, angle, 0]}>
    <Block at={[0, 0, 0]} size={[0.49, 0.035, 0.25]} color="#666c65" round={0.012} />
    <Block at={[0, 0.17, -0.03]} size={[0.065, 0.35, 0.07]} color="#626960" />
    <Block at={[0, 0.53, -0.025]} size={[1.03, 0.66, 0.06]} color="#363f3e" round={0.035} />
    <Block at={[0, 0.54, 0.009]} size={[0.95, 0.56, 0.008]} color="#213b3e" />
    <Block at={[-0.39, 0.54, 0.017]} size={[0.13, 0.56, 0.003]} color="#294a4c" />
    {Array.from({ length: 7 }, (_, i) => <Block key={i} at={[-0.22 + (i % 3) * 0.035, 0.73 - i * 0.064, 0.019]} size={[0.15 + (i % 3) * 0.07, 0.015, 0.004]} color={["#84b5aa", "#ceb98b", "#73a0ad"][i % 3]} />)}
  </group>;
}

export function ContextWatch({ onLost }: { onLost: () => void }) {
  const gl = useThree(value => value.gl);
  useEffect(() => {
    const lost = (event: Event) => { event.preventDefault(); onLost(); };
    gl.domElement.addEventListener("webglcontextlost", lost);
    return () => gl.domElement.removeEventListener("webglcontextlost", lost);
  }, [gl, onLost]);
  return null;
}
