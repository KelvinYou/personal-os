// Single owner of 3D movement and camera feel. Mirrors docs/design/3d-scene-standard.md §2-3;
// tests/scene-standard.cjs fails if the numbers here and in the document drift apart.
// Framework-free so the React office and the standalone home viewer import the same file.
// Yaw convention: forward is (-sin yaw, -cos yaw). Callers with another convention convert.

/** Real-world values in metres; scenes multiply by their own worldScale. */
export const STANDARD = Object.freeze({
  walkSpeed: 1.8, runSpeed: 3.6, accelerationRate: 10, collisionRadius: 0.2,
  keyTurnRate: 2.0, dtClamp: 0.1, joystickDeadZone: 0.15,
  lookSensitivity: 0.004, firstPitch: Object.freeze([-1.309, 1.309]), thirdPitch: Object.freeze([-0.5236, 1.2217]),
  eyeHeight: 1.6, firstFov: 60, fovRange: Object.freeze([50, 80]),
  recenterGain: 2.5, recenterMaxRate: 1.8, recenterDelay: 1.0,
  boom: 3.0, boomRange: Object.freeze([1.5, 4.5]), boomRecovery: 0.3, followSmoothing: 0.08, avatarTurnSmoothing: 0.12,
  avatarFadeDistance: 0.7, overviewFov: 32,
  transitions: Object.freeze({ overviewToWalk: 0.6, firstThird: 0.3, roomJump: 0.3, sit: 0.4, focus: 0.5 }),
});

/** Scale every human-relative length by the scene's worldScale. Angles, rates and times are unscaled. */
export function sceneParams(worldScale = 1) {
  const s = STANDARD;
  return {
    worldScale, walkSpeed: s.walkSpeed * worldScale, runSpeed: s.runSpeed * worldScale,
    collisionRadius: s.collisionRadius * worldScale, eyeHeight: s.eyeHeight * worldScale,
    boom: s.boom * worldScale, boomRange: s.boomRange.map(v => v * worldScale),
    avatarFadeDistance: s.avatarFadeDistance * worldScale,
  };
}

export const clampDt = seconds => Math.max(0, Math.min(STANDARD.dtClamp, seconds));
/** Frame-rate independent exponential approach; rate 10 reaches about 86% in 0.2 s. */
export const approach = (current, target, rate, dt) => current + (target - current) * (1 - Math.exp(-rate * dt));
export const wrapAngle = a => Math.atan2(Math.sin(a), Math.cos(a));
/** Turn along the shortest arc with a time constant (seconds); 0 snaps. */
export const smoothAngle = (current, target, time, dt) => time <= 0 ? target : current + wrapAngle(target - current) * (1 - Math.exp(-dt / time));
export const clamp = (v, [lo, hi]) => Math.max(lo, Math.min(hi, v));

/** Camera-relative input to a unit-or-shorter direction; diagonals are normalised, analog deflection is kept. */
export function moveDirection(yaw, forward, side) {
  const length = Math.hypot(forward, side), scale = length > 1 ? 1 / length : 1;
  const f = forward * scale, r = side * scale;
  return { x: -Math.sin(yaw) * f + Math.cos(yaw) * r, z: -Math.cos(yaw) * f - Math.sin(yaw) * r, magnitude: Math.min(1, length) };
}

/** Joystick deflection with a dead zone, rescaled so speed grows from zero at the edge of the zone. */
export function joystick(x, y, deadZone = STANDARD.joystickDeadZone) {
  const m = Math.hypot(x, y);
  if (m <= deadZone) return { side: 0, forward: 0 };
  const k = Math.min(1, (m - deadZone) / (1 - deadZone)) / m;
  return { side: x * k, forward: y * k };
}

/**
 * GTA-style chase camera: while the player walks forward or sideways (not toward the camera) and has not
 * touched the look controls for `recenterDelay` seconds, the camera yaw swings toward the avatar's facing.
 * `idle` is seconds since the last look input. Rate is capped so a held A or D draws a gentle arc.
 */
export function recenterYaw(yaw, target, dt, input, idle) {
  const walking = input.forward >= 0 && (input.forward > 0 || Math.abs(input.side) > 0);
  if (!walking || idle < STANDARD.recenterDelay) return yaw;
  return yaw + clamp(wrapAngle(target - yaw) * STANDARD.recenterGain, [-STANDARD.recenterMaxRate, STANDARD.recenterMaxRate]) * dt;
}

/** Boom length: shortens at once when blocked, eases back out when clear. */
export function stepBoom(current, available, desired, dt) {
  const limit = Math.min(desired, available);
  return limit < current ? limit : approach(current, limit, 3 / STANDARD.boomRecovery, dt);
}

/** Advance planar velocity toward the input target. Returns the new velocity and avatar facing. */
export function stepLocomotion(state, input, dt, params) {
  const { x, z, magnitude } = moveDirection(state.yaw, input.forward, input.side);
  const speed = (input.run ? params.runSpeed : params.walkSpeed) * magnitude;
  const vx = approach(state.vx ?? 0, x * speed, STANDARD.accelerationRate, dt);
  const vz = approach(state.vz ?? 0, z * speed, STANDARD.accelerationRate, dt);
  const turning = Math.hypot(vx, vz) > 0.1 * params.walkSpeed;
  // Every view shares one control scheme: the avatar turns toward its travel direction and holds still otherwise.
  const heading = Math.atan2(-vx, -vz);
  const facing = turning ? smoothAngle(state.facing ?? state.yaw, heading, STANDARD.avatarTurnSmoothing, dt) : state.facing ?? state.yaw;
  return { vx, vz, facing };
}
