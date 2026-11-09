"use client";

// The flat town (docs/design/office-world.md): the Lab building holds the attention
// radar (office-attention-radar.md §7) and the Finance building holds three desks.
// Position is status in the Lab: a person's zone is their attention zone, and
// movement happens only when the observed zone or tool changes; no idle routines.
// The town around them (grass, paths, plaza, trees) comes from town-landscape.tsx.
// Only kelvin.ai walks, under explicit input: overview (WASD), first or third person.
// No doors. Scene standard: Office · town.
import { Suspense, memo, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { ContactShadows, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { MathUtils, PCFShadowMap, Vector3, type Group, type Mesh, type MeshBasicMaterial, type PerspectiveCamera } from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { Button } from "@/components/ui/button";
import { buildCharacter, walkPose } from "@/lib/character-builder.mjs";
import { characterProfile, characterWardrobe } from "@/lib/office-character";
import { pads, radarSlots, ROOM, STATION_Z, stations, toolLabels, waitedFor, zoneLabels, type RadarWorker, type Slot } from "@/lib/office-radar";
import { clampDt, sceneParams, STANDARD } from "@/lib/scene-standard.mjs";
import { ContextWatch, TownSign } from "./scene-parts";
import { KenneyAsset, KenneyTownShell } from "./kenney-office-assets";
import { departments, departmentOrder, financeStations, financeManagerSpot, contentStations, panOvershoot, town, townObstacles, townSpawn, townWalkWorld, type Area, type Department, type FinanceStation, type ContentStation } from "@/lib/office-departments";
import { ContentLabBuilding } from "./content-lab-building";
import { officeParams, type PlayerPose } from "@/lib/office-navigation";
import { CameraBlend, InteractWatch, OverviewPlayer, PlayerCamera, PlayerHud, useOfficePlayer, type OfficePlayerControls } from "./office-player";
import { OfficePerson } from "./office-character-model";
import { townSky } from "@/lib/office-palette";
import { budgetDpr, MIN_DETAIL_CANVAS } from "@/lib/office-render";
import { TownLandscape } from "./town-landscape";

const SPAWN = townSpawn();
const SKY = townSky;
import type { V3 } from "@/lib/office-life";

const WORLD = sceneParams(1.37);
// Scene palette (3D standard §4, Office · radar): attention and review accents join the office neutrals.
const palette = { wall: "#7b80ad", cap: "#b9bfd7", needs: "#ef925b", needsPad: "#edbd8d", review: "#64bfa7", reviewPad: "#9ad5c1", workPad: "#a5b3ce", donePad: "#8c91ad" };
const STAND_Y = .82, SEAT_Y = .62;
type SceneProps = { workers: RadarWorker[]; selectedId: string | null; animate: boolean; now: number; replay: boolean; cameraCommand: { command: string; sequence: number }; onSelect: (id: string) => void; onDeselect: () => void;
  department: Department; station: FinanceStation; financeNotice: string; onDepartment: (id: Department) => void; onStation: (id: FinanceStation) => void;
  contentStation: ContentStation; contentSummary: Record<ContentStation, string>; onContentStation: (id: ContentStation) => void;
  /** Owner waits per building, shown as a badge on its projected name (web/lib/office-attention.ts). */
  badges?: Partial<Record<Department, number>> };
type Anchor = { id: string; title: string; at: V3; kind: "department" | "desk" | "content"; action: () => void };
type Label = { id: string; x: number; y: number; ax: number; ay: number };

function FloorText({ at, title, width, ratio = 7 }: { at: V3; title: string; width: number; ratio?: number }) {
  return <group position={at} rotation={[-Math.PI / 2, 0, 0]}><TownSign at={[0, 0, 0]} title={title} width={width} ratio={ratio} /></group>;
}

function ZonePad({ zone, color, edge }: { zone: keyof typeof pads; color: string; edge: string }) {
  const pad = pads[zone];
  return <group>
    <mesh position={[pad.x, .012, pad.z]} receiveShadow><boxGeometry args={[pad.width, .02, pad.depth]} /><meshStandardMaterial color={color} roughness={1} transparent opacity={.7} depthWrite={false} /></mesh>
    {[-1, 1].map(side => <mesh key={`h${side}`} position={[pad.x, .026, pad.z + side * pad.depth / 2]}><boxGeometry args={[pad.width, .012, .07]} /><meshStandardMaterial color={edge} roughness={.9} /></mesh>)}
    {[-1, 1].map(side => <mesh key={`v${side}`} position={[pad.x + side * pad.width / 2, .026, pad.z]}><boxGeometry args={[.07, .012, pad.depth]} /><meshStandardMaterial color={edge} roughness={.9} /></mesh>)}
  </group>;
}

function Station({ tool, x }: { tool: string; x: number }) {
  const z = STATION_Z;
  if (tool === "read") return <group position={[x, 0, z - .2]}>
    <KenneyAsset kind="bookcase" scale={2.8} yaw={Math.PI} />
    {[.5, 1.28, 2.02].map(y => <KenneyAsset key={y} kind="books" at={[0, y, .08]} scale={2.5} />)}
  </group>;
  if (tool === "agent") return <group position={[x, 0, z]}>
    <KenneyAsset kind="table" scale={3.2} />
    <KenneyAsset kind="coffee" at={[0, 1.18, 0]} scale={1.6} />
  </group>;
  return <group position={[x, 0, z]}>
    <KenneyAsset kind="desk" />
    {tool === "web" || tool === "think" ? <KenneyAsset kind="laptop" at={[0, 1.23, -.06]} scale={2.8} yaw={Math.PI} /> : <>
      <KenneyAsset kind="screen" at={[tool === "command" ? -.45 : 0, 1.23, -.12]} scale={2.5} yaw={Math.PI} />
      {tool === "command" && <KenneyAsset kind="screen" at={[.5, 1.23, -.12]} scale={2.1} yaw={Math.PI - .15} />}
      <KenneyAsset kind="keyboard" at={[0, 1.23, .25]} scale={2.5} />
    </>}
    <KenneyAsset kind="chair" at={[0, 0, .95]} scale={2.4} yaw={Math.PI} />
    {tool === "command" && <KenneyAsset kind="cables" at={[.6, .015, -.7]} scale={.5} />}
  </group>;
}

function RadarRoom() {
  return <group>
    <ZonePad zone="done" color={palette.donePad} edge={palette.cap} />
    <ZonePad zone="working" color={palette.workPad} edge={palette.wall} />
    <ZonePad zone="review" color={palette.reviewPad} edge={palette.review} />
    <ZonePad zone="needs_you" color={palette.needsPad} edge={palette.needs} />
    {stations.map(station => <Station key={station.tool} tool={station.tool} x={station.x} />)}
    {Array.from({ length: 8 }, (_, i) => <KenneyAsset key={i} kind="bench" at={[-10 + i * 2.85, 0, pads.done.z - .2]} scale={3.5} />)}
    <group position={[pads.review.x, 0, pads.review.z - pads.review.depth / 2 + .5]}>
      <KenneyAsset kind="desk" scale={3.2} />
      <KenneyAsset kind="books" at={[0, 1.23, 0]} scale={2.5} />
    </group>
    <FloorText at={[pads.done.x - pads.done.width / 2 + 2, .04, pads.done.z + pads.done.depth / 2 - .35]} title={zoneLabels.done.toUpperCase()} width={2.8} />
    <FloorText at={[pads.working.x - pads.working.width / 2 + 1.6, .04, pads.working.z + pads.working.depth / 2 - .35]} title={zoneLabels.working.toUpperCase()} width={2.2} />
    <FloorText at={[pads.review.x - pads.review.width / 2 + 2.2, .04, pads.review.z + pads.review.depth / 2 - .4]} title={zoneLabels.review.toUpperCase()} width={3.6} ratio={9} />
    <FloorText at={[pads.needs_you.x + pads.needs_you.width / 2 - 1.8, .04, pads.needs_you.z + pads.needs_you.depth / 2 - .45]} title="NEEDS YOU" width={3} />
    {stations.map(station => <FloorText key={station.tool} at={[station.x, .04, STATION_Z + 2.55]} title={toolLabels[station.tool].toUpperCase()} width={1.5} />)}
  </group>;
}
const MemoRoom = memo(RadarRoom);

/** Second building. Desks face the camera; clicking one opens that workstation beside the floor. */
function FinanceBuilding({ station, active, notice, onStation }: { station: FinanceStation; active: boolean; notice: string; onStation: (id: FinanceStation) => void }) {
  const area = departments.finance;
  const hover = (on: boolean) => { document.body.style.cursor = on ? "pointer" : ""; };
  useEffect(() => () => { document.body.style.cursor = ""; }, []);
  return <group name="finance-building">
    {financeStations.map(desk => <group key={desk.id} name={`finance-desk-${desk.id}`} position={[desk.x, 0, desk.z]}
      onClick={(event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onStation(desk.id); }}
      onPointerOver={event => { event.stopPropagation(); hover(true); }} onPointerOut={() => hover(false)}>
      {active && station === desk.id && <mesh position={[0, .014, .7]} receiveShadow><boxGeometry args={[3.6, .02, 3.4]} /><meshStandardMaterial color={palette.reviewPad} roughness={1} transparent opacity={.75} depthWrite={false} /></mesh>}
      <KenneyAsset kind="desk" />
      {desk.id === "notices" || desk.id === "research" ? <KenneyAsset kind="books" at={[0, 1.23, 0]} scale={2.5} /> : desk.id === "assets"
        ? <><KenneyAsset kind="screen" at={[0, 1.23, -.12]} scale={2.5} yaw={Math.PI} /><KenneyAsset kind="keyboard" at={[0, 1.23, .25]} scale={2.5} /></>
        : <KenneyAsset kind="laptop" at={[0, 1.23, -.06]} scale={2.8} yaw={Math.PI} />}
      <KenneyAsset kind="chair" at={[0, 0, .95]} scale={2.4} yaw={Math.PI} />
      <FloorText at={[0, .04, 2.55]} title={desk.title.toUpperCase()} width={2.6} ratio={9} />
    </group>)}
    <group position={[area.x - area.width / 2 + 1.6, 0, area.z - area.depth / 2 + 1.4]}>
      <KenneyAsset kind="bookcase" scale={2.8} yaw={Math.PI} />
      {[.5, 1.28].map(y => <KenneyAsset key={y} kind="books" at={[0, y, .08]} scale={2.5} />)}
    </group>
    <OfficePerson session={{ session_id: "skill:wealth-manager", state: "idle" }} skillId="wealth-manager" preview="standing" at={[financeManagerSpot.x, .82, financeManagerSpot.z]} selected={active && station === "research"} animate={false} onSelect={() => onStation("research")} />
    <KenneyAsset kind="coffee" at={[area.x + area.width / 2 - 2, 0, 3]} scale={2.2} />
    <KenneyAsset kind="table" at={[area.x + 4, 0, 5.5]} scale={3.2} />
    <KenneyAsset kind="bench" at={[area.x - 4, 0, 6.5]} scale={3.5} />
    <FloorText at={[area.x, .04, area.z + area.depth / 2 - 1.2]} title={notice.toUpperCase()} width={9} ratio={12} />
  </group>;
}

/** A ground outline around the selected department: the cue that replaces any camera move. */
function SelectedOutline({ department }: { department: Department }) {
  const a = departments[department], w = a.width + 1.2, d = a.depth + 1.2, t = .22, y = .03;
  return <group name={`selected-${department}`} position={[a.x, y, a.z]}>
    {[[0, -d / 2, w, t], [0, d / 2, w, t], [-w / 2, 0, t, d], [w / 2, 0, t, d]].map(([x, z, sx, sz], i) => <mesh key={i} position={[x, 0, z]}><boxGeometry args={[sx, .02, sz]} /><meshStandardMaterial color="#f4f1e6" emissive="#f4f1e6" emissiveIntensity={.25} roughness={.8} /></mesh>)}
  </group>;
}

/** Department names over each building's back wall. */
function BuildingSigns() {
  return <group>{departmentOrder.map(id => { const area = departments[id]; return <TownSign key={id} at={[area.x, 4.9, area.z - area.depth / 2 + .2]} title={id === "lab" ? "LAB / DEVELOPMENT & EXPERIMENTS" : id === "content" ? "CONTENT LAB / RESEARCH & MAKE" : "FINANCE / REVIEW & PLAN"} width={id === "lab" ? 10 : 8} ratio={9} />; })}</group>;
}

function RadarPerson({ worker, slot, selected, animate, onSelect }: { worker: RadarWorker; slot: Slot; selected: boolean; animate: boolean; onSelect: () => void }) {
  const look = characterWardrobe(worker.session_id, worker.skill?.id);
  const profile = { ...characterProfile(worker.session_id), shirt: look.shirt };
  const key = JSON.stringify([profile, look, slot.seated]);
  const built = useMemo(() => buildCharacter({ T: THREE, RoundedBoxGeometry }, { profile, look, roaming: !slot.seated, armPitch: slot.seated ? -.3 : .05 }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key]);
  useEffect(() => () => built.dispose(), [built]);
  useEffect(() => () => { document.body.style.cursor = ""; }, []);
  const body = useRef<Group>(null), ring = useRef<Mesh>(null);
  const position = useRef<Vector3 | null>(null), clock = useRef(0);
  const [hovered, setHovered] = useState(false);
  const needs = worker.attention === "needs_you";
  useFrame((_, delta) => {
    const dt = clampDt(delta);
    const target = new Vector3(slot.at[0], slot.seated ? SEAT_Y : STAND_Y, slot.at[2]);
    if (!position.current) position.current = target.clone();
    const current = position.current, gap = target.clone().sub(current);
    const distance = Math.hypot(gap.x, gap.z);
    let walking = false, facing = slot.facing;
    // Purposeful movement only: walk when the observed zone or station changed.
    if (distance > .02 && animate) {
      const step = Math.min(distance, WORLD.walkSpeed * dt);
      current.addScaledVector(gap.setY(0).normalize(), step); current.y = target.y;
      walking = true; facing = Math.atan2(gap.x, gap.z);
    } else current.copy(target);
    if (animate) clock.current += dt;
    if (!body.current) return;
    body.current.position.copy(current);
    const turn = Math.atan2(Math.sin(facing - body.current.rotation.y), Math.cos(facing - body.current.rotation.y));
    body.current.rotation.y += animate ? turn * (1 - Math.exp(-dt / STANDARD.avatarTurnSmoothing)) : turn;
    const parts = built.parts;
    if (slot.seated) { if (parts.arm) parts.arm.rotation.x = -.3; if (parts.leftArm) parts.leftArm.rotation.x = -.3; }
    else {
      walkPose(parts, clock.current, walking ? 1 : 0);
      if (!walking && worker.attention === "working") {
        const typing = animate ? Math.sin(clock.current * 6) * .05 : 0;
        if (parts.arm) parts.arm.rotation.x = -.85 + typing; if (parts.leftArm) parts.leftArm.rotation.x = -.85 - typing;
      }
      // A raised hand is the needs-you signal; it does not wave under reduced motion.
      if (!walking && needs && parts.arm) parts.arm.rotation.x = -2.75 + (animate ? Math.sin(clock.current * 3) * .12 : 0);
    }
    if (parts.head) parts.head.rotation.y = worker.attention === "working" || walking ? 0 : -.15;
    if (ring.current) {
      const material = ring.current.material as MeshBasicMaterial;
      material.opacity = needs ? (animate ? .55 + Math.sin(clock.current * 2.4) * .25 : .7) : selected || hovered ? .9 : 0;
    }
  });
  const ringColor = needs ? palette.needs : look.shirt;
  return <group name={`radar-${worker.session_id}`} ref={body} scale={slot.scale} rotation={[0, slot.facing, 0]}
    onClick={(event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onSelect(); }}
    onPointerOver={event => { event.stopPropagation(); setHovered(true); document.body.style.cursor = "pointer"; }}
    onPointerOut={() => { setHovered(false); document.body.style.cursor = ""; }}>
    <primitive object={built.group} />
    <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]} position={[0, (slot.seated ? -SEAT_Y : -STAND_Y) + .05, 0]}><ringGeometry args={[.55, needs ? .7 : .62, 40]} /><meshBasicMaterial color={ringColor} transparent opacity={0} depthWrite={false} /></mesh>
  </group>;
}

function SubagentLinks({ workers, slots }: { workers: RadarWorker[]; slots: Map<string, Slot> }) {
  return <group>{workers.filter(worker => worker.parent_session_id && slots.has(worker.session_id) && slots.has(worker.parent_session_id)).map(worker => {
    const a = slots.get(worker.parent_session_id!)!.at, b = slots.get(worker.session_id)!.at;
    const length = Math.hypot(b[0] - a[0], b[2] - a[2]);
    return <mesh key={worker.session_id} position={[(a[0] + b[0]) / 2, .035, (a[2] + b[2]) / 2]} rotation={[0, Math.atan2(b[0] - a[0], b[2] - a[2]), 0]}><boxGeometry args={[.05, .01, length]} /><meshBasicMaterial color={palette.needs} transparent opacity={.6} /></mesh>;
  })}</group>;
}

/** Caps drawing-buffer pixels as the Canvas grows (fullscreen); DOM text keeps native resolution. */
function PixelBudget() {
  const size = useThree(state => state.size), setDpr = useThree(state => state.setDpr);
  useEffect(() => { setDpr(budgetDpr(window.devicePixelRatio || 1, size.width, size.height)); }, [size.width, size.height, setDpr]);
  return null;
}

/** Overview camera centred on kelvin.ai: it keeps the user's orbit and zoom and follows the walker.
 *  Focusing a person pauses the follow until kelvin.ai moves again. */
function RadarCamera({ command, focusId, follow, root }: { command: SceneProps["cameraCommand"]; focusId: string | null; follow: React.RefObject<PlayerPose>; root: React.RefObject<HTMLDivElement | null> }) {
  const controls = useRef<OrbitControlsImpl>(null);
  const focusRef = useRef(focusId); focusRef.current = focusId;
  const { camera, size, invalidate, scene } = useThree();
  const perspective = camera as PerspectiveCamera;
  const tan = Math.tan(MathUtils.degToRad(STANDARD.overviewFov / 2));
  const aspect = size.width / Math.max(1, size.height);
  // The camera always frames the whole town (wide margin: near corners spread under perspective).
  // Drag, scroll and pan move freely from there; no view locks onto one building.
  const fitFor = (area: Area, margin: number) => Math.max((area.depth + 6) / 2 / tan, (area.width + margin) / 2 / (tan * aspect)) * .95;
  // Preserve the plaza spawn/follow target while leaving room for the new west building.
  const fit = fitFor({ ...town, width: 2 * Math.max(Math.abs(SPAWN.x - town.x + town.width / 2), Math.abs(town.x + town.width / 2 - SPAWN.x)) }, 12) * (size.width < 760 ? 1.2 : 1);
  const nearest = fitFor(departments.finance, 4) * .3, farthest = fit * 1.6;
  const home = useMemo(() => new Vector3(6, 24, 30).normalize(), []);
  const closeUp = useMemo(() => new Vector3(8, 7.5, 12).normalize(), []);
  const centerOn = (): V3 => [follow.current.x, .4, follow.current.z];
  const center = centerOn();
  const paused = useRef(false);
  // Once the user orbits, zooms or focuses, a resize (fullscreen entry/exit) keeps their camera; only reset reframes.
  const touched = useRef(false);
  const place = (target: V3, distance: number, direction: Vector3) => {
    controls.current?.target.set(...target);
    camera.position.set(...target).addScaledVector(direction, distance);
  };
  useEffect(() => {
    // A portrait viewport needs a distant overview to fit three buildings. Keep the
    // actual town inside the far plane and fog instead of fading the whole world away.
    perspective.fov = STANDARD.overviewFov; perspective.near = 1; perspective.far = Math.max(400, farthest + 120); perspective.updateProjectionMatrix();
    if (scene.fog instanceof THREE.Fog) { scene.fog.near = Math.max(90, fit * .8); scene.fog.far = Math.max(260, farthest * 1.4); }
    if (!touched.current) place(centerOn(), fit, home);
    controls.current?.update(); invalidate();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [camera, fit, invalidate]);
  useEffect(() => () => { if (scene.fog instanceof THREE.Fog) { scene.fog.near = 90; scene.fog.far = 260; } }, [scene]);
  useEffect(() => {
    if (!controls.current) return;
    const target = controls.current.target;
    if (command.command === "reset") { paused.current = false; touched.current = false; place(centerOn(), fit, home); }
    else if (command.command !== "focus" || focusRef.current) touched.current = true;
    if (command.command === "focus" && focusRef.current) {
      const actor = scene.getObjectByName(`radar-${focusRef.current}`);
      if (actor) { paused.current = true; place([actor.position.x, 1.2, actor.position.z], fit / 2.4, closeUp); }
    }
    if (command.command === "in" || command.command === "out") {
      const distance = MathUtils.clamp(camera.position.distanceTo(target) * (command.command === "in" ? 1 / 1.18 : 1.18), nearest, farthest);
      camera.position.sub(target).setLength(distance).add(target);
    }
    controls.current.update(); invalidate();
  // Selection alone must not reset a manually positioned camera.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [command]);
  useFrame((_, delta) => {
    const orbit = controls.current, pose = follow.current;
    if (!orbit || !pose) return;
    if (pose.moving) paused.current = false;
    if (paused.current) return;
    // Ease the target onto kelvin.ai and carry the camera by the same step, so orbit and zoom are kept.
    const k = 1 - Math.exp(-Math.min(delta, .1) * 10);
    const dx = (pose.x - orbit.target.x) * k, dz = (pose.z - orbit.target.z) * k;
    if (Math.abs(dx) + Math.abs(dz) < 1e-4) return;
    orbit.target.x += dx; orbit.target.z += dz; camera.position.x += dx; camera.position.z += dz;
    orbit.update(); invalidate();
  });
  // Pan keeps the target on the town ground: shift camera and target together so orbit and zoom are kept.
  const keepInTown = () => {
    const orbit = controls.current;
    if (!orbit) return;
    const [dx, dz] = panOvershoot(orbit.target.x, orbit.target.z);
    if (dx || dz) { orbit.target.x -= dx; orbit.target.z -= dz; camera.position.x -= dx; camera.position.z -= dz; }
    if (root.current) root.current.dataset.orbit = JSON.stringify({ x: +orbit.target.x.toFixed(3), z: +orbit.target.z.toFixed(3) }); // exposed for tests
  };
  return <OrbitControls ref={controls} makeDefault target={center} minDistance={nearest} maxDistance={farthest} minPolarAngle={.25} maxPolarAngle={Math.PI / 2.4} minAzimuthAngle={-1.4} maxAzimuthAngle={1.4} enableDamping={false} enablePan panSpeed={.9} onChange={keepInTown} onStart={() => { touched.current = true; }} />;
}

// Project label anchors into the host DOM (no nested React root), like the classic office.
// Labels arrive in queue priority (needs you first); later labels move up until they no longer overlap.
// `placed` may be seeded with rectangles already on screen (building and desk buttons), which never move.
type Placed = { x: number; y: number; w: number };
function declutter(labels: Label[], widths: Map<string, number>, placed: Placed[] = []) {
  for (const label of labels) {
    const w = widths.get(label.id) ?? 120;
    for (let tries = 0; tries < 8 && placed.some(other => Math.abs(other.x - label.x) < (other.w + w) / 2 + 4 && Math.abs(other.y - label.y) < 34); tries++) label.y -= 34;
    placed.push({ x: label.x, y: label.y, w });
  }
}
function LabelProjector({ ids, widths, extra, avoid, onPosition }: { ids: string[]; widths: Map<string, number>; extra: V3; avoid: React.RefObject<Placed[]>; onPosition: (labels: Label[]) => void }) {
  const point = useMemo(() => new Vector3(), []);
  const last = useRef<Label[]>([]);
  useFrame(({ camera, size, scene }) => {
    const next: Label[] = [];
    for (const id of ids) {
      const actor = scene.getObjectByName(`radar-${id}`);
      if (!actor) continue;
      point.set(actor.position.x, actor.position.y + 1.95 * actor.scale.y, actor.position.z).project(camera);
      const x = (point.x * .5 + .5) * size.width, y = (-point.y * .5 + .5) * size.height;
      next.push({ id, x, y, ax: x, ay: y });
    }
    point.set(...extra).project(camera);
    const mx = (point.x * .5 + .5) * size.width, my = (-point.y * .5 + .5) * size.height;
    next.push({ id: "__done_more", x: mx, y: my, ax: mx, ay: my });
    declutter(next, widths, [...avoid.current]);
    if (size.width <= 760) for (const label of next) { label.x = MathUtils.clamp(label.x, 56, size.width - 56); label.y = MathUtils.clamp(label.y, 40, size.height - 40); }
    if (next.length === last.current.length && next.every((p, i) => p.id === last.current[i].id && Math.abs(p.x - last.current[i].x) + Math.abs(p.y - last.current[i].y) <= .5)) return;
    last.current = next; onPosition(next);
  });
  return null;
}

/** Rough on-screen width of a projected building/desk button (small Button, 12-13 px text, optional badge). */
const anchorWidth = (anchor: Pick<Anchor, "title" | "kind">, badge = 0) => anchor.title.length * (anchor.kind === "department" ? 7.6 : 7) + 26 + (badge ? 24 : 0);

/** Department and desk buttons, projected like person labels (no nested React root).
 *  Buttons push each other up instead of overlapping, and publish their rectangles so person labels avoid them. */
function AnchorProjector({ anchors, badges, placed, onPosition }: { anchors: Anchor[]; badges: Partial<Record<Department, number>>; placed: React.RefObject<Placed[]>; onPosition: (labels: Label[]) => void }) {
  const point = useMemo(() => new Vector3(), []);
  const last = useRef("");
  const widths = useMemo(() => new Map(anchors.map(anchor => [anchor.id, anchorWidth(anchor, anchor.kind === "department" ? badges[anchor.id.slice(5) as Department] : 0)])), [anchors, badges]);
  useFrame(({ camera, size }) => {
    const next: Label[] = [];
    for (const anchor of anchors) {
      // A small canvas (Content Lab's wide workspace, narrow windows) keeps building names only;
      // the workstation nav beside it offers the same buttons as readable text.
      if (anchor.kind !== "department" && size.width < MIN_DETAIL_CANVAS) continue;
      point.set(...anchor.at).project(camera);
      if (point.z < -1 || point.z > 1 || Math.abs(point.x) > 1.05 || Math.abs(point.y) > 1.05) continue;
      const x = (point.x * .5 + .5) * size.width, y = (-point.y * .5 + .5) * size.height;
      next.push({ id: anchor.id, x, y, ax: x, ay: y });
    }
    const rects: Placed[] = [];
    declutter(next, widths, rects);
    placed.current = rects;
    const key = next.map(l => `${l.id}:${Math.round(l.x)}:${Math.round(l.y)}`).join("|");
    if (key !== last.current) { last.current = key; onPosition(next); }
  });
  return null;
}

/** People are sessions: a stable person name, never the skill (skills are badges). */
export const personName = (worker: Pick<RadarWorker, "session_id" | "parent_session_id">) => worker.parent_session_id ? "Subagent" : characterProfile(worker.session_id).name;
function labelDetail(worker: RadarWorker, now: number) {
  const since = waitedFor(worker.attention_since, now);
  return worker.attention === "working" ? worker.tool ? toolLabels[worker.tool] : "Working" : worker.attention === "done" ? "Done" : `${worker.attention === "needs_you" ? "Waiting" : "Ready"} ${since}`;
}
const labelText = (worker: RadarWorker, now: number) => `${personName(worker)} ${labelDetail(worker, now)}`;

type Near = { id: string; title: string; x: number; z: number; action: () => void };
/** Nearest desk or person within reach while walking; also exposes the live pose for tests. */
function NearWatch({ controls, targets, onNear, root }: { controls: OfficePlayerControls; targets: () => Near[]; onNear: (near: Near | null) => void; root: React.RefObject<HTMLDivElement | null> }) {
  const last = useRef<string | null>(null);
  useFrame(() => {
    const pose = controls.player.current;
    let nearest: Near | null = null, distance = 3.5 * officeParams.worldScale;
    for (const t of targets()) { const d = Math.hypot(t.x - pose.x, t.z - pose.z); if (d < distance) { nearest = t; distance = d; } }
    if (last.current !== (nearest?.id ?? null)) { last.current = nearest?.id ?? null; onNear(nearest); }
    if (root.current) root.current.dataset.player = JSON.stringify({ x: +pose.x.toFixed(3), z: +pose.z.toFixed(3), moving: pose.moving });
  });
  return null;
}

export default function RadarScene(props: SceneProps) {
  const controls = useOfficePlayer(SPAWN);
  const walking = controls.view !== "overview";
  const world = useMemo(() => townWalkWorld(townObstacles(stations.map(s => s.x), STATION_Z, pads.done.z - .2, { x: pads.review.x, z: pads.review.z - pads.review.depth / 2 + .5 })), []);
  const [near, setNear] = useState<Near | null>(null);
  const { slots, hiddenDone } = useMemo(() => radarSlots(props.workers), [props.workers]);
  const visibleWorkers = props.workers.filter(worker => slots.has(worker.session_id));
  const [labels, setLabels] = useState<Label[]>([]);
  const [anchorLabels, setAnchorLabels] = useState<Label[]>([]);
  const [lost, setLost] = useState(false);
  const [visible, setVisible] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(max-width: 760px)");
    const change = () => setNarrow(query.matches);
    change(); query.addEventListener("change", change);
    return () => query.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    update(); document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  // The done shelf stays quiet: its labels appear only for the selected person.
  // Narrow screens label only who needs you; the queue below lists everyone else.
  const ids = useMemo(() => visibleWorkers.filter(worker => worker.session_id === props.selectedId || (props.department !== "content" && (narrow ? worker.attention === "needs_you" : worker.attention !== "done"))).map(worker => worker.session_id), [visibleWorkers, props.selectedId, props.department, narrow]);
  const byId = new Map(visibleWorkers.map(worker => [worker.session_id, worker]));
  const widths = useMemo(() => new Map(visibleWorkers.map(worker => [worker.session_id, labelText(worker, props.now).length * 6.4 + (worker.badge ? worker.badge.length * 5.6 + 24 : 0) + 44])), [visibleWorkers, props.now]);
  const { onDepartment, onStation, onSelect, onContentStation } = props;
  const anchors = useMemo<Anchor[]>(() => [
    ...departmentOrder.map(id => ({ id: `dept-${id}`, title: departments[id].title, at: [departments[id].x, 6.6, departments[id].z - departments[id].depth / 2 + .2] as V3, kind: "department" as const, action: () => onDepartment(id) })),
    ...financeStations.map(desk => ({ id: `desk-${desk.id}`, title: desk.short, at: [desk.x, 2.7, desk.z] as V3, kind: "desk" as const, action: () => onStation(desk.id) })),
    ...contentStations.map(desk => ({ id: `content-${desk.id}`, title: desk.title, at: [desk.x, 2.7, desk.z] as V3, kind: "content" as const, action: () => onContentStation(desk.id) })),
  ], [onDepartment, onStation, onContentStation]);
  // Overview level of detail: building names always; workstation buttons only for the selected building
  // (its physical desk signs still name the others). Narrow screens keep building names only.
  const shownAnchors = useMemo(() => anchors.filter(a => a.kind === "department" || (!narrow && (a.kind === "desk" ? props.department === "finance" : props.department === "content"))), [anchors, narrow, props.department]);
  const badges = useMemo(() => props.badges ?? {}, [props.badges]);
  const anchorRects = useRef<Placed[]>([]);
  // Desks and Lab people are the F targets; positions are read live from the scene.
  const deskTargets = useMemo(() => [...financeStations.map(desk => ({ id: `desk-${desk.id}`, title: `Open ${desk.title}`, x: desk.x, z: desk.z + 1.6, action: () => onStation(desk.id) })), ...contentStations.map(desk => ({ id: `content-${desk.id}`, title: `Open Content ${desk.title}`, x: desk.x, z: desk.z + 1.6, action: () => onContentStation(desk.id) }))], [onStation, onContentStation]);
  const slotTargets = useMemo(() => visibleWorkers.filter(w => !w.parent_session_id).map(w => { const at = slots.get(w.session_id)!.at; return { id: w.session_id, title: `Check on ${personName(w)}`, x: at[0], z: at[2], action: () => onSelect(w.session_id) }; }), [visibleWorkers, slots, onSelect]);
  const nearTargets = () => [...deskTargets, ...slotTargets];
  const nearby = near ? nearTargets().find(t => t.id === near.id) : undefined;
  if (lost) return <div className="office-scene-placeholder"><p>The 3D connection was interrupted.</p><Button variant="outline" onClick={() => setLost(false)}>Reopen the town</Button><p>The attention queue, timeline and Finance workstations still work.</p></div>;
  return <div {...controls.bindings} className="office-canvas-shell radar-canvas-shell" data-replay={props.replay || undefined} data-department={props.department}>
    <Canvas camera={{ position: [6, 24, 30], fov: STANDARD.overviewFov, near: 1, far: 400 }} shadows={{ type: PCFShadowMap }} dpr={[1, 1.75]} frameloop={(props.animate || walking) && visible ? "always" : "demand"} gl={{ antialias: true, alpha: true }} onPointerMissed={props.onDeselect} fallback={<div className="office-scene-placeholder">Interactive 3D town. The attention queue and Finance workstations provide a text alternative.</div>}>
      <PixelBudget /><color attach="background" args={[SKY]} /><fog attach="fog" args={[SKY, 90, 260]} />
      <hemisphereLight args={["#eaf0ec", "#b9a98c", .85]} />
      <ambientLight intensity={.25} color="#fff3df" />
      <directionalLight position={[-9, 22, 12]} intensity={3} color="#fff0d4" castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-62} shadow-camera-right={62} shadow-camera-top={30} shadow-camera-bottom={-30} shadow-camera-near={.5} shadow-camera-far={120} shadow-bias={-.0004} shadow-normalBias={.035} />
      <directionalLight position={[8, 6, 10]} intensity={.45} color="#e8eeff" />
      <Suspense fallback={null}><TownLandscape /><KenneyTownShell /><MemoRoom /><BuildingSigns /><SelectedOutline department={props.department} /><FinanceBuilding station={props.station} active={props.department === "finance"} notice={props.financeNotice} onStation={props.onStation} /><ContentLabBuilding station={props.contentStation} active={props.department === "content"} summaries={props.contentSummary} onStation={onContentStation} /></Suspense>
      {visibleWorkers.map(worker => <RadarPerson key={worker.session_id} worker={worker} slot={slots.get(worker.session_id)!} selected={worker.session_id === props.selectedId} animate={props.animate && visible} onSelect={() => props.onSelect(worker.session_id)} />)}
      <SubagentLinks workers={visibleWorkers} slots={slots} />
      <ContactShadows position={[town.x, .005, 0]} opacity={.28} scale={town.width + 8} blur={2.6} far={4} resolution={1024} frames={1} color="#887b64" />
      <OfficePerson session={{ session_id: "kelvin.ai", state: "idle" }} host player={controls.player.current} selected={false} animate={props.animate || walking} onSelect={() => {}} at={[SPAWN.x, .82, SPAWN.z]} />
      {walking ? <PlayerCamera player={controls.player} keys={controls.keys} controls={controls} view={controls.view as "first" | "third"} count={0} visible={visible} world={world} />
        : <><RadarCamera command={props.cameraCommand} focusId={props.selectedId} follow={controls.player} root={controls.bindings.ref} /><OverviewPlayer controls={controls} count={0} world={world} /></>}
      <CameraBlend view={controls.view} command={props.cameraCommand} />
      <InteractWatch controls={controls} ids={[]} onSelect={() => {}} targets={[...financeStations.map(desk => ({ name: `finance-desk-${desk.id}`, onInteract: () => onStation(desk.id) })), ...contentStations.map(desk => ({ name: `content-desk-${desk.id}`, onInteract: () => onContentStation(desk.id) })), ...visibleWorkers.filter(w => !w.parent_session_id).map(w => ({ name: `radar-${w.session_id}`, onInteract: () => onSelect(w.session_id) }))]} />
      <NearWatch controls={controls} targets={nearTargets} onNear={setNear} root={controls.bindings.ref} />
      <ContextWatch onLost={() => setLost(true)} />
      {!walking && <AnchorProjector anchors={shownAnchors} badges={badges} placed={anchorRects} onPosition={setAnchorLabels} />}
      {showLabels && <LabelProjector ids={ids} widths={widths} extra={[pads.done.x + pads.done.width / 2 - 1.2, 1.4, pads.done.z]} avoid={anchorRects} onPosition={setLabels} />}
    </Canvas>
    <PlayerHud controls={controls} interactionHint="open a nearby desk or check on a person" resetLabel="Back to plaza" run={false} />
    {walking && nearby && <Button className="town-interact" onClick={nearby.action}>F · {nearby.title}</Button>}
    {!walking && anchorLabels.map(label => {
      const anchor = shownAnchors.find(a => a.id === label.id);
      if (!anchor) return null;
      const current = anchor.kind === "department" ? anchor.id === `dept-${props.department}` : anchor.kind === "content" ? props.department === "content" && anchor.id === `content-${props.contentStation}` : props.department === "finance" && anchor.id === `desk-${props.station}`;
      // The badge is CSS content (data-badge), so the button's text and accessible name stay the building name;
      // the department buttons above the town carry the same count as readable text.
      const badge = anchor.kind === "department" ? badges[anchor.id.slice(5) as Department] : undefined;
      return <Button key={label.id} size="sm" variant={current ? "default" : "outline"} aria-pressed={current} className={`town-anchor town-anchor-${anchor.kind}`} data-badge={badge || undefined} style={{ left: label.x, top: label.y }} onClick={anchor.action}>{anchor.title}</Button>;
    })}
    <Button variant="outline" size="sm" className="office-label-toggle" aria-pressed={showLabels} onClick={() => setShowLabels(value => !value)}>Name labels <span aria-hidden="true">{showLabels ? "On" : "Off"}</span></Button>
    {showLabels && <svg className="office-label-leaders" aria-hidden="true">{labels.filter(label => label.id !== "__done_more" && Math.abs(label.ay - label.y) > 2).map(label => <line key={label.id} x1={label.x} y1={label.y} x2={label.ax} y2={label.ay} />)}</svg>}
    {showLabels && labels.map(label => {
      if (label.id === "__done_more") return hiddenDone ? <span key={label.id} className="radar-more-label" style={{ left: label.x, top: label.y }}>+{hiddenDone} more done</span> : null;
      const worker = byId.get(label.id);
      if (!worker) return null;
      const since = waitedFor(worker.attention_since, props.now);
      const detail = labelDetail(worker, props.now);
      return <button key={label.id} type="button" className={`office-floating-label radar-label attention-${worker.attention} ${worker.parent_session_id ? "radar-label-sub" : ""} ${worker.session_id === props.selectedId ? "office-label-selected" : ""}`} style={{ left: label.x, top: label.y }} aria-label={`${personName(worker)}: ${zoneLabels[worker.attention]}${since ? ` for ${since}` : ""}${worker.badge ? `, skill ${worker.badge}` : ""}`} onClick={() => props.onSelect(worker.session_id)}>
        <span /><strong>{personName(worker)}</strong><i /><span className="office-label-state">{detail}</span>{worker.badge && !worker.parent_session_id && <em className="radar-badge">{worker.badge}</em>}
      </button>;
    })}
  </div>;
}
