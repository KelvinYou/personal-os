// Presentation-only flat-floor navigation. Never changes agent or task state.
import { officeDepth } from "./office-life";
import { clampDt, recenterYaw, sceneParams, stepLocomotion, STANDARD } from "./scene-standard.mjs";
import { canStand, moveOnFloor, type FloorBox, type FloorWorld } from "./scene-floor.mjs";
import { amenities, buildingWalls, coffeePosts, groundOutline, seatFurniture, tableSeats, type GroundPoint } from "./office-layout";
export type OfficeView = "overview" | "first" | "third";
export interface PlayerPose { x: number; z: number; yaw: number; pitch: number; moving: boolean; vx: number; vz: number; facing: number; lookIdle: number }
export interface WalkInput { forward: number; side: number; turn: number; run?: boolean }
// Stylized office: desk top 1.22 m against 0.76 m real, so human-relative numbers scale by 1.37.
export const OFFICE_SCALE = 1.37;
export const officeParams = sceneParams(OFFICE_SCALE);
type Rect = { x: number; z: number; halfX: number; halfZ: number };
export interface WalkWorld { minX: number; maxX: number; minZ: number; maxZ: number; ground: GroundPoint[]; obstacles: Rect[]; cameraWalls: Rect[]; floor: GroundPoint[]; bounds: FloorBox; boxes: FloorBox[]; cameraBoxes: FloorBox[]; radius: number; sim: FloorWorld }
export const createPlayer = (): PlayerPose => ({ x: 2, z: 9, yaw: 0, pitch: -.08, moving: false, vx: 0, vz: 0, facing: 0, lookIdle: 0 });
const box = (x: number, z: number, width: number, depth: number): Rect => ({ x, z, halfX: width / 2, halfZ: depth / 2 });
export function walkWorld(count: number): WalkWorld {
  const parts = [...buildingWalls(), ...Object.values(amenities), ...coffeePosts.map(post => ({ ...post, width: .2, depth: .2, tall: true })), ...tableSeats.map(seat => ({ ...seat, width: .55, depth: .6 }))];
  const toBox = (prop: { x: number; z: number; width: number; depth: number }) => box(prop.x, prop.z, prop.width, prop.depth);
  const cameraWalls = parts.filter(prop => "tall" in prop && prop.tall).map(toBox);
  const obstacles = [...parts.map(toBox), ...Array.from({ length: count }, (_, index) => seatFurniture(index)).flat().map(toBox)];
  const minX = -28, maxX = 28, minZ = -21, maxZ = -20 + officeDepth(count) + 1, ground = groundOutline(count);
  const toFloor = (rect: Rect): FloorBox => ({ minX: rect.x - rect.halfX, maxX: rect.x + rect.halfX, minZ: rect.z - rect.halfZ, maxZ: rect.z + rect.halfZ });
  const boxes = obstacles.map(toFloor), bounds = { minX, maxX, minZ, maxZ };
  return { minX, maxX, minZ, maxZ, ground, obstacles, cameraWalls, floor: ground, bounds, boxes, cameraBoxes: cameraWalls.map(toFloor), radius: officeParams.collisionRadius, sim: { floor: ground, obstacles: boxes, bounds, radius: officeParams.collisionRadius } };
}
/** Body clearance on the office floor; delegates to the shared floor module. `obstacles` selects walls vs camera-only walls. */
export function canOccupy(world: WalkWorld, x: number, z: number, radius = world.radius, obstacles: Rect[] = world.obstacles) {
  return canStand(x, z, world.sim, radius, obstacles === world.cameraWalls ? world.cameraBoxes : obstacles === world.obstacles ? world.boxes : obstacles.map(rect => ({ minX: rect.x - rect.halfX, maxX: rect.x + rect.halfX, minZ: rect.z - rect.halfZ, maxZ: rect.z + rect.halfZ })));
}
export function advancePlayer(player: PlayerPose, input: WalkInput, seconds: number, world: WalkWorld, frameYaw?: number) {
  const dt = clampDt(seconds);
  // From the overview (frameYaw given) input is relative to that camera and the player yaw is left alone.
  if (frameYaw === undefined) player.yaw -= input.turn * dt * STANDARD.keyTurnRate;
  const { vx, vz, facing } = stepLocomotion(frameYaw === undefined ? player : { yaw: frameYaw, vx: player.vx, vz: player.vz, facing: player.facing }, input, dt, officeParams);
  player.vx = vx; player.vz = vz; player.facing = facing;
  // Chase camera in every view: the view swings behind the avatar while A/D/W carry it, unless the player is looking around.
  player.lookIdle = input.turn ? 0 : player.lookIdle + dt;
  if (frameYaw === undefined) player.yaw = recenterYaw(player.yaw, player.facing, dt, input, player.lookIdle);
  const dx = vx * dt, dz = vz * dt;
  const beforeX = player.x, beforeZ = player.z;
  const moved = moveOnFloor({ x: player.x, z: player.z }, { x: dx, z: dz }, world.sim);
  player.x = moved.x; player.z = moved.z;
  player.moving = Math.hypot(player.x - beforeX, player.z - beforeZ) > .00001;
  // Pressing into a wall must not leave residual velocity that releases as a lurch.
  if (!player.moving) { player.vx *= .5; player.vz *= .5; }
}
/** Clear boom length along the camera ray, up to `desired`. Pure: does not move the avatar. */
export function boomClearance(player: PlayerPose, world: WalkWorld, desired = officeParams.boom) {
  let distance = 0;
  for (let next = .05; next <= desired; next += .05) {
    const x = player.x + Math.sin(player.yaw) * Math.cos(player.pitch) * next;
    const z = player.z + Math.cos(player.yaw) * Math.cos(player.pitch) * next;
    if (!canOccupy(world, x, z, .12, world.cameraWalls)) break;
    distance = next;
  }
  return distance;
}
export function thirdPersonPosition(player: PlayerPose, world: WalkWorld, boom = boomClearance(player, world)): [number, number, number] {
  const distance = boom;
  return [player.x + Math.sin(player.yaw) * Math.cos(player.pitch) * distance,
    Math.max(.6, officeParams.eyeHeight + .65 - Math.sin(player.pitch) * distance),
    player.z + Math.cos(player.yaw) * Math.cos(player.pitch) * distance];
}
