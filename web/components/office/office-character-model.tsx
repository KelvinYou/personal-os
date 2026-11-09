"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import type { Group } from "three";
import type { RoomWorker as OfficeSession } from "@/lib/office-room";
import { officeParams, type PlayerPose } from "@/lib/office-navigation";
import { characterProfile, characterWardrobe } from "@/lib/office-character";
import { buildCharacter } from "@/lib/character-builder.mjs";
import { deskAngle, idlePose, type IdleMode, type V3 } from "@/lib/office-life";

export function OfficePerson({ session, selected, animate, onSelect, at, index = 0, host = false, player, hidden = false, skillId, preview }: { session: Pick<OfficeSession, "session_id" | "state">; selected: boolean; animate: boolean; onSelect: () => void; at: V3; index?: number; host?: boolean; player?: PlayerPose; hidden?: boolean; skillId?: string; preview?: "standing" | "seated" }) {
  const body = useRef<Group>(null);
  const walkTime = useRef(0);
  const idle = !preview && session.state === "idle" && !host;
  const [routine, setRoutine] = useState<{ mode: IdleMode; standing: boolean }>(() => { const pose = idlePose(index, 0); return { mode: pose.mode, standing: idle && pose.standing }; });
  const routineRef = useRef(routine);
  const roaming = !!player || preview === "standing" || idle && routine.standing;
  const look = characterWardrobe(session.session_id, skillId, host);
  const profile = { ...characterProfile(session.session_id), ...(host ? { feminine: false } : {}), shirt: look.shirt };
  const [hovered, setHovered] = useState(false);
  // Geometry comes from the shared builder (also used by the home viewer); this component only animates it.
  const mug = idle && routine.mode === "drinking", bowl = idle && routine.mode === "eating", laptop = idle && routine.mode === "studying";
  const buildKey = JSON.stringify([profile, look, roaming, mug, bowl, laptop, !!preview]);
  const built = useMemo(() => buildCharacter({ T: THREE, RoundedBoxGeometry }, { profile, look, roaming, mug, bowl, laptop, armPitch: preview ? .05 : -.65 }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [buildKey]);
  const builtRef = useRef(built); builtRef.current = built;
  useEffect(() => () => built.dispose(), [built]);
  useEffect(() => () => { document.body.style.cursor = ""; }, []);
  useFrame(({ clock }, delta) => {
    // A walking player's stride rate follows its actual speed (standard §2), so faster walks do not slide.
    if (animate || player?.moving) walkTime.current += delta * (player?.moving ? Math.max(.6, Math.hypot(player.vx, player.vz) / officeParams.walkSpeed) : 1);
    const pose = preview ? { at, angle: 0, mode: "studying" as IdleMode, standing: preview === "standing", stride: 0 } : player ? { at: [player.x, .82, player.z] as V3, angle: player.facing + Math.PI, mode: (player.moving ? "walking" : "studying") as IdleMode, standing: true, stride: player.moving ? 1 : 0 } : idle ? idlePose(index, walkTime.current) : { at, angle: Math.PI + deskAngle(index) + .15, mode: "studying" as IdleMode, standing: false, stride: 0 };
    if (routineRef.current.mode !== pose.mode || routineRef.current.standing !== pose.standing) { routineRef.current = { mode: pose.mode, standing: pose.standing }; setRoutine(routineRef.current); }
    if (body.current) {
      body.current.position.set(...pose.at);
      const turn = Math.atan2(Math.sin(pose.angle - body.current.rotation.y), Math.cos(pose.angle - body.current.rotation.y));
      body.current.rotation.y += turn * (animate ? 1 - Math.exp(-delta * 7) : 1);
      if (pose.mode === "walking" && animate) body.current.position.y += Math.abs(Math.sin(walkTime.current * 4.2)) * .012 * pose.stride;
    }
    const walking = (!!player || idle) && pose.mode === "walking";
    const swing = walking && (animate || !!player) ? Math.sin(walkTime.current * 4.2) * .24 * pose.stride : 0;
    const { legLeft, legRight, leftArm, arm, head } = builtRef.current.parts;
    if (legLeft) legLeft.rotation.x = swing;
    if (legRight) legRight.rotation.x = -swing;
    if (leftArm) leftArm.rotation.x = walking ? -swing * .65 : player || preview ? .05 : -.65;
    if (arm) arm.rotation.x = walking ? swing * .65 : player || preview ? .05 : idle && pose.mode === "drinking" ? -1.75 + (animate ? Math.sin(walkTime.current * .7) * .1 : 0) : idle && pose.mode === "eating" ? -1.1 : session.state === "waiting" ? -1.8 : -.65 + (animate && session.state === "working" ? Math.sin(walkTime.current * 4) * .04 : 0);

    if (head) head.rotation.y = animate ? Math.sin(clock.elapsedTime * .6) * .12 - .25 : preview ? -.05 : -.25;
  });
  return <group visible={!hidden} name={`worker-${session.session_id}`} ref={body} position={at} rotation={[0, preview ? 0 : Math.PI + deskAngle(index) + .15, 0]} onClick={(event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onSelect(); }} onPointerOver={event => { if (host || preview) return; event.stopPropagation(); setHovered(true); document.body.style.cursor = "pointer"; }} onPointerOut={() => { setHovered(false); document.body.style.cursor = ""; }}>
    <primitive object={built.group} />
    {(selected || hovered) && <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -.77, 0]}><ringGeometry args={[.59, .64, 40]} /><meshBasicMaterial color={look.shirt} transparent opacity={.9} depthWrite={false} /></mesh>}
  </group>;
}
