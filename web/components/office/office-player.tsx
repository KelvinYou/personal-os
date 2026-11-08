"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent, type RefObject } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Quaternion, Vector3, type Group, type PerspectiveCamera as Camera } from "three";
import { advancePlayer, boomClearance, createPlayer, officeParams, thirdPersonPosition, walkWorld, type OfficeView, type PlayerPose } from "@/lib/office-navigation";
import { clamp, joystick, STANDARD, stepBoom } from "@/lib/scene-standard.mjs";

const movement = new Set(["KeyW", "KeyA", "KeyS", "KeyD", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "ShiftLeft", "ShiftRight"]);
const overviewKeys = new Set(["KeyW", "KeyA", "KeyS", "KeyD", "ShiftLeft", "ShiftRight"]);
const editing = (target: EventTarget | null) => target instanceof HTMLElement && !!target.closest("input,textarea,select,button,a,[contenteditable=true],[role=combobox]");
export function useOfficePlayer() {
  const [view, setView] = useState<OfficeView>("overview");
  const [entered, setEntered] = useState(false);
  const player = useRef(createPlayer());
  const keys = useRef(new Set<string>());
  const stick = useRef({ forward: 0, side: 0 });
  const boomTarget = useRef<number>(officeParams.boom);
  const interact = useRef(0);
  const wake = useRef<() => void>(() => {});
  const [fov, setFov] = useState<number>(STANDARD.firstFov);
  const root = useRef<HTMLDivElement>(null);
  const drag = useRef<{ id: number; x: number; y: number } | null>(null);
  function clear() { stick.current = { forward: 0, side: 0 }; keys.current.clear(); player.current.moving = false; drag.current = null; }
  function reset() { clear(); boomTarget.current = officeParams.boom; Object.assign(player.current, createPlayer()); root.current?.focus({ preventScroll: true }); }
  function changeView(next: OfficeView) { clear(); if (next !== "overview") setEntered(true); setView(next); }
  useEffect(() => {
    const clearInput = () => { stick.current = { forward: 0, side: 0 }; keys.current.clear(); player.current.moving = false; drag.current = null; };
    window.addEventListener("blur", clearInput); document.addEventListener("visibilitychange", clearInput);
    return () => { clearInput(); window.removeEventListener("blur", clearInput); document.removeEventListener("visibilitychange", clearInput); };
  }, []);
  useEffect(() => { if (entered) root.current?.focus({ preventScroll: true }); }, [view, entered]);
  function keyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.code === "Escape" && view !== "overview") { event.preventDefault(); event.stopPropagation(); changeView("overview"); return; }
    if (editing(event.target)) return;
    if (view === "overview") {
      // God view: W A S D (and Shift) walk kelvin.ai relative to the screen. Arrows stay free for page scrolling.
      if (overviewKeys.has(event.code)) { event.preventDefault(); keys.current.add(event.code); if (!entered) setEntered(true); wake.current(); }
      return;
    }
    if (event.code === "KeyR" && !event.repeat) { event.preventDefault(); reset(); return; }
    if (event.code === "KeyF" && !event.repeat) { event.preventDefault(); interact.current += 1; return; }
    if (event.code === "KeyV" && !event.repeat) { event.preventDefault(); changeView(view === "first" ? "third" : "first"); return; }
    if (movement.has(event.code)) { event.preventDefault(); keys.current.add(event.code); }
  }
  function pointerDown(event: PointerEvent<HTMLDivElement>) {
    if (view === "overview" || !(event.target instanceof HTMLCanvasElement) || event.button !== 0) return;
    event.preventDefault(); root.current?.focus({ preventScroll: true });
    drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  const bindings = {
    ref: root, tabIndex: 0, role: "region", "aria-label": "Control kelvin.ai", "data-office-view": view,
    onKeyDown: keyDown,
    onKeyUp: (event: KeyboardEvent<HTMLDivElement>) => { if (movement.has(event.code)) { keys.current.delete(event.code); if (!editing(event.target) && (view !== "overview" || overviewKeys.has(event.code))) event.preventDefault(); } },
    onBlur: (event: React.FocusEvent<HTMLDivElement>) => { if (!event.currentTarget.contains(event.relatedTarget)) clear(); },
    onPointerDown: pointerDown,
    onWheel: (event: React.WheelEvent<HTMLDivElement>) => { if (view === "third") boomTarget.current = clamp(boomTarget.current * Math.exp(event.deltaY * .001), officeParams.boomRange as [number, number]); },
    onPointerMove: (event: PointerEvent<HTMLDivElement>) => {
      if (!drag.current || drag.current.id !== event.pointerId) return;
      player.current.lookIdle = 0;
      player.current.yaw -= (event.clientX - drag.current.x) * STANDARD.lookSensitivity;
      player.current.pitch = clamp(player.current.pitch - (event.clientY - drag.current.y) * STANDARD.lookSensitivity, view === "third" ? STANDARD.thirdPitch : STANDARD.firstPitch);
      drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY };
    },
    onPointerUp: (event: PointerEvent<HTMLDivElement>) => { if (drag.current?.id === event.pointerId) drag.current = null; },
    onPointerCancel: () => clear(),
    onLostPointerCapture: () => { drag.current = null; },
  };
  return { view, entered, player, keys, drag, wake, stick, boomTarget, interact, fov, setFov, bindings, changeView,
    reset };
}
export type OfficePlayerControls = ReturnType<typeof useOfficePlayer>;
export function PlayerCamera({ player, keys, controls, view, count, visible }: { player: RefObject<PlayerPose>; keys: RefObject<Set<string>>; controls: OfficePlayerControls; view: "first" | "third"; count: number; visible: boolean }) {
  const world = useMemo(() => walkWorld(count), [count]);
  const scene = useThree(state => state.scene);
  const host = useRef<Group | null>(null);
  useEffect(() => () => { if (host.current) host.current.visible = true; }, []);
  const boom = useRef<number>(officeParams.boom);
  const smooth = useRef<[number, number, number] | null>(null);
  const desired = controls.boomTarget;
  useEffect(() => { smooth.current = null; }, [view]);
  useFrame(({ camera: three }, delta) => {
    if (!visible) return;
    const cam = three as Camera;
    if (cam.fov !== controls.fov || cam.near !== .06) { cam.fov = controls.fov; cam.near = .06; cam.far = 100; cam.updateProjectionMatrix(); }
    const dt = Math.min(delta, STANDARD.dtClamp);
    const held = (code: string, alternative?: string) => keys.current.has(code) || !!alternative && keys.current.has(alternative) ? 1 : 0;
    const stick = controls.stick.current;
    if (controls.drag.current) player.current.lookIdle = 0;
    advancePlayer(player.current, { forward: clamp(held("KeyW", "ArrowUp") - held("KeyS", "ArrowDown") + stick.forward, [-1, 1]), side: clamp(held("KeyD") - held("KeyA") + stick.side, [-1, 1]), turn: held("ArrowRight") - held("ArrowLeft"), run: held("ShiftLeft", "ShiftRight") === 1 }, delta, world);
    const pose = player.current;
    if (!host.current) host.current = scene.getObjectByName("worker-kelvin.ai") as Group | null;
    if (view === "first") {
      if (host.current) host.current.visible = false;
      cam.position.set(pose.x, officeParams.eyeHeight, pose.z);
      cam.rotation.set(pose.pitch, pose.yaw, 0, "YXZ");
    } else {
      // Boom shortens at once when blocked and eases back out; the camera follows with a short critically damped lag.
      boom.current = stepBoom(boom.current, boomClearance(pose, world, desired.current), desired.current, dt);
      const target = thirdPersonPosition(pose, world, boom.current);
      const follow = 1 - Math.exp(-dt / STANDARD.followSmoothing);
      const at = smooth.current ??= target;
      // A boom shortened by a wall is applied directly so the camera never trails through geometry.
      const blocked = boom.current < desired.current - .01;
      for (let i = 0; i < 3; i++) at[i] = blocked ? target[i] : at[i] + (target[i] - at[i]) * follow;
      if (host.current) host.current.visible = Math.hypot(at[0] - pose.x, at[2] - pose.z) > officeParams.avatarFadeDistance;
      cam.position.set(...at);
      cam.lookAt(pose.x, officeParams.eyeHeight * .86, pose.z);
    }
  }, -2);
  return null;
}
/** God view: the same avatar walks from the overview, with input relative to the screen and the camera left alone. */
export function OverviewPlayer({ controls, count }: { controls: OfficePlayerControls; count: number }) {
  const world = useMemo(() => walkWorld(count), [count]);
  const invalidate = useThree(state => state.invalidate);
  useEffect(() => { controls.wake.current = invalidate; return () => { controls.wake.current = () => {}; }; }, [controls, invalidate]);
  useFrame(({ camera, controls: orbit }, delta) => {
    const held = (code: string) => controls.keys.current.has(code) ? 1 : 0, pose = controls.player.current;
    const input = { forward: held("KeyW") - held("KeyS"), side: held("KeyD") - held("KeyA"), turn: 0, run: held("ShiftLeft") + held("ShiftRight") > 0 };
    if (!controls.entered && !input.forward && !input.side) return;
    const target = (orbit as unknown as { target?: Vector3 } | null)?.target;
    const dx = target ? target.x - camera.position.x : -camera.position.x, dz = target ? target.z - camera.position.z : -camera.position.z;
    advancePlayer(pose, input, delta, world, Math.atan2(-dx, -dz));
    if (pose.moving || input.forward || input.side || Math.hypot(pose.vx, pose.vz) > .01) invalidate();
  });
  return null;
}
const ease = (t: number) => t < .5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2;
const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
type Pose = { pos: Vector3; quat: Quaternion; fov: number };
const capture = (camera: Camera, into: Pose) => { into.pos.copy(camera.position); into.quat.copy(camera.quaternion); into.fov = camera.fov; };
/** One camera serves every view. Rigs write the true pose; this blends the shown pose between views (standard §3). */
export function CameraBlend({ view, command }: { view: OfficeView; command: { command: string; sequence: number } }) {
  const invalidate = useThree(state => state.invalidate);
  const target = useRef<Pose>({ pos: new Vector3(), quat: new Quaternion(), fov: 0 });
  const shown = useRef<Pose>({ pos: new Vector3(), quat: new Quaternion(), fov: 0 });
  const from = useRef<Pose>({ pos: new Vector3(), quat: new Quaternion(), fov: 0 });
  const run = useRef({ t: 1, d: .6, ready: false });
  const last = useRef({ view, sequence: command.sequence });
  // Runs before the rigs: hand them the unblended pose so orbit controls never absorb the blend.
  useFrame(({ camera }) => {
    const cam = camera as Camera;
    if (run.current.t < 1 && cam.position.equals(shown.current.pos)) { cam.position.copy(target.current.pos); cam.quaternion.copy(target.current.quat); cam.fov = target.current.fov; }
  }, -3);
  useFrame(({ camera }, delta) => {
    const cam = camera as Camera;
    capture(cam, target.current);
    if (last.current.view !== view || (last.current.sequence !== command.sequence && (command.command === "focus" || command.command === "reset"))) {
      const viewChange = last.current.view !== view, involvesOverview = viewChange && (last.current.view === "overview" || view === "overview");
      last.current = { view, sequence: command.sequence };
      if (run.current.ready && !reduced()) { run.current.t = 0; run.current.d = viewChange ? (involvesOverview ? STANDARD.transitions.overviewToWalk : STANDARD.transitions.firstThird) : STANDARD.transitions.focus; from.current.pos.copy(shown.current.pos); from.current.quat.copy(shown.current.quat); from.current.fov = shown.current.fov; }
    }
    last.current.sequence = command.sequence;
    if (run.current.t < 1) {
      run.current.t = Math.min(1, run.current.t + Math.min(delta, .1) / run.current.d);
      const k = ease(run.current.t);
      cam.position.lerpVectors(from.current.pos, target.current.pos, k);
      cam.quaternion.slerpQuaternions(from.current.quat, target.current.quat, k);
      const fov = from.current.fov + (target.current.fov - from.current.fov) * k;
      if (fov !== cam.fov) { cam.fov = fov; cam.updateProjectionMatrix(); }
      invalidate();
    }
    capture(cam, shown.current); run.current.ready = true;
  }, -.5);
  return null;
}
/** F selects the nearest colleague within reach: the office's interaction target. */
export function InteractWatch({ controls, ids, onSelect, targets = [] }: { controls: OfficePlayerControls; ids: string[]; onSelect: (id: string) => void; targets?: { name: string; onInteract: () => void }[] }) {
  const scene = useThree(state => state.scene);
  const seen = useRef(controls.interact.current);
  useFrame(() => {
    if (seen.current === controls.interact.current) return;
    seen.current = controls.interact.current;
    const pose = controls.player.current; let best: string | null = null, bestDistance = 3.5 * officeParams.worldScale;
    for (const id of ids) { const actor = scene.getObjectByName(`worker-${id}`); if (!actor) continue; const d = Math.hypot(actor.position.x - pose.x, actor.position.z - pose.z); if (d < bestDistance) { best = id; bestDistance = d; } }
    let action = best ? () => onSelect(best!) : null;
    for (const target of targets) { const object = scene.getObjectByName(target.name); if (!object) continue; const position = object.getWorldPosition(new Vector3()); const distance = Math.hypot(position.x - pose.x, position.z - pose.z); if (distance < bestDistance) { bestDistance = distance; action = target.onInteract; } }
    action?.();
  });
  return null;
}
export function PlayerHud({ controls }: { controls: OfficePlayerControls }) {
  const active = controls.view !== "overview";
  function touch(code: string, label: string, content: string) {
    return <button type="button" aria-label={label} onPointerDown={event => { event.preventDefault(); controls.keys.current.add(code); if (event.currentTarget.hasPointerCapture(event.pointerId) === false) { try { event.currentTarget.setPointerCapture(event.pointerId); } catch { /* Synthetic or cancelled touch. */ } } }} onPointerUp={() => controls.keys.current.delete(code)} onPointerCancel={() => controls.keys.current.delete(code)} onLostPointerCapture={() => controls.keys.current.delete(code)} onKeyDown={event => { if (event.code === "Space" || event.code === "Enter") { event.preventDefault(); controls.keys.current.add(code); } }} onKeyUp={() => controls.keys.current.delete(code)} onBlur={() => controls.keys.current.delete(code)}>{content}</button>;
  }
  const [knob, setKnob] = useState({ x: 0, y: 0 });
  const radius = 44;
  function moveStick(event: PointerEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    let dx = event.clientX - (rect.left + rect.width / 2), dy = event.clientY - (rect.top + rect.height / 2);
    const length = Math.hypot(dx, dy); if (length > radius) { dx = dx / length * radius; dy = dy / length * radius; }
    setKnob({ x: dx, y: dy });
    controls.stick.current = joystick(dx / radius, -dy / radius);
  }
  function release() { setKnob({ x: 0, y: 0 }); controls.stick.current = { forward: 0, side: 0 }; }
  return <>
    {!active && <p className="office-overview-hint">W A S D walk kelvin.ai · Shift to run</p>}
    <div className="office-player-views" aria-label="Camera perspective">
      {([ ["overview", "Overview"], ["first", "First person"], ["third", "Third person"] ] as const).map(([value, label]) => <button type="button" key={value} aria-label={label} aria-pressed={controls.view === value} onClick={() => controls.changeView(value)}>{label}</button>)}
    </div>
    {active && <>
      <div className="office-player-help"><strong>Controlling kelvin.ai</strong><span className="office-player-desktop-hint">W A S D to move · A / D swing the camera behind you · ← → to turn · Shift to run · Drag to look · Scroll for distance · F to select a nearby colleague · V to switch · R to reset · Esc for overview</span><span className="office-player-touch-hint">Drag to look · Use the joystick to move</span><label className="office-player-fov">Field of view <input type="range" min={STANDARD.fovRange[0]} max={STANDARD.fovRange[1]} step={1} value={controls.fov} onChange={event => controls.setFov(Number(event.target.value))} aria-label="Field of view" /> <span>{controls.fov}°</span></label><button type="button" onClick={controls.reset} aria-label="Reset player position">Back to aisle</button></div>
      <div className="office-player-pad" aria-label="Movement joystick" role="group">
        <div className="office-joystick" data-office-joystick onPointerDown={event => { event.preventDefault(); event.currentTarget.setPointerCapture(event.pointerId); moveStick(event); }} onPointerMove={event => { if (event.currentTarget.hasPointerCapture(event.pointerId)) moveStick(event); }} onPointerUp={release} onPointerCancel={release} onLostPointerCapture={release}><span className="office-joystick-knob" style={{ transform: `translate(${knob.x}px, ${knob.y}px)` }} /></div>
        {touch("ShiftLeft", "Run", "Run")}
      </div>
    </>}
  </>;
}
