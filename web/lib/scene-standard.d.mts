export const STANDARD: Readonly<{
  walkSpeed: number; runSpeed: number; accelerationRate: number; collisionRadius: number; keyTurnRate: number; dtClamp: number; joystickDeadZone: number;
  lookSensitivity: number; firstPitch: readonly [number, number]; thirdPitch: readonly [number, number];
  eyeHeight: number; firstFov: number; fovRange: readonly [number, number];
  recenterGain: number; recenterMaxRate: number; recenterDelay: number;
  boom: number; boomRange: readonly [number, number]; boomRecovery: number; followSmoothing: number; avatarTurnSmoothing: number;
  avatarFadeDistance: number; overviewFov: number;
  transitions: Readonly<{ overviewToWalk: number; firstThird: number; roomJump: number; sit: number; focus: number }>;
}>;
export interface SceneParams { worldScale: number; walkSpeed: number; runSpeed: number; collisionRadius: number; eyeHeight: number; boom: number; boomRange: number[]; avatarFadeDistance: number }
export function sceneParams(worldScale?: number): SceneParams;
export function clampDt(seconds: number): number;
export function approach(current: number, target: number, rate: number, dt: number): number;
export function wrapAngle(angle: number): number;
export function smoothAngle(current: number, target: number, time: number, dt: number): number;
export function clamp(value: number, range: readonly [number, number]): number;
export function moveDirection(yaw: number, forward: number, side: number): { x: number; z: number; magnitude: number };
export function joystick(x: number, y: number, deadZone?: number): { side: number; forward: number };
export function stepBoom(current: number, available: number, desired: number, dt: number): number;
export function stepLocomotion(state: { yaw: number; vx?: number; vz?: number; facing?: number }, input: { forward: number; side: number; run?: boolean }, dt: number, params: SceneParams): { vx: number; vz: number; facing: number };
export function recenterYaw(yaw: number, target: number, dt: number, input: { forward: number; side: number }, idle: number): number;
