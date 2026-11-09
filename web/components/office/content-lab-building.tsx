"use client";
import { Html } from "@react-three/drei";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { MIN_DETAIL_CANVAS } from "@/lib/office-render";
import { contentStations, type ContentStation } from "@/lib/office-departments";
import { KenneyAsset } from "./kenney-office-assets";
import { TownSign } from "./scene-parts";

/** Furniture fronts face +Z; same floor pivot, asset scale and palette as Finance. */
export function ContentLabBuilding({ active, station, summaries, onStation }: { active: boolean; station: ContentStation; summaries: Record<ContentStation, string>; onStation: (s: ContentStation) => void }) {
  // The building summary board shows only when Content Lab is selected and the canvas is roomy: at whole-town distance it was unreadable
  // and covered the station and person labels. The department button carries the waiting count instead.
  const roomy = useThree(state => state.size.width) >= MIN_DETAIL_CANVAS;
  return <group name="content-building">{active && roomy && <Html position={[-30, 3.5, -8]} center distanceFactor={24} zIndexRange={[6, 2]}><div className="content-lab-board"><strong>CONTENT LAB</strong>{contentStations.map(s => <div key={s.id}>{s.title}: {summaries[s.id]}</div>)}</div></Html>}{contentStations.map(s => <group key={s.id} name={`content-desk-${s.id}`} position={[s.x, 0, s.z]}
    onClick={(event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onStation(s.id); }}>
    <KenneyAsset kind={s.id === "research" ? "bookcase" : s.id === "review" ? "table" : "desk"} scale={s.id === "research" ? 2.8 : 3.2} yaw={s.id === "research" ? Math.PI : 0} />
    {s.id === "research" ? <><KenneyAsset kind="books" at={[0, .5, .08]} scale={2.5} /><KenneyAsset kind="books" at={[0, 1.28, .08]} scale={2.5} /></>
      : s.id === "production" ? <KenneyAsset kind="laptop" at={[0, 1.23, 0]} scale={2.8} yaw={Math.PI} />
        : s.id === "review" ? <><KenneyAsset kind="books" at={[-.6, 1.18, 0]} scale={2.5} /><KenneyAsset kind="screen" at={[.3, 1.18, 0]} scale={2.5} yaw={Math.PI} /></>
          : <KenneyAsset kind="screen" at={[0, 1.23, 0]} scale={2.5} yaw={Math.PI} />}
    <TownSign at={[0, 2.7, -.35]} title={s.title.toUpperCase()} width={3.2} ratio={7} />
    {active && roomy && station === s.id && <Html position={[0, 3.8, 0]} center distanceFactor={18} zIndexRange={[8, 4]}><div className="content-lab-board"><strong>{s.title}</strong>{summaries[s.id]}</div></Html>}
  </group>)}</group>;
}
