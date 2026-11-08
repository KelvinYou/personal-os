// Decorative office routines. These never change observed session state.
export type V3 = [number, number, number];
import { floorDepth, seatLayout } from "./office-layout";
export const officeDepth = floorDepth;
export function deskAt(index: number): V3 {
  const seat = seatLayout(index);
  return [seat.x, 0, seat.z];
}
export const deskAngle = (index: number) => seatLayout(index).angle;
export const seatedAt = (index: number): V3 => [deskAt(index)[0] - .05 * (deskAngle(index) ? -1 : 1), .62, deskAt(index)[2] + (deskAngle(index) ? -1.25 : 1.25)];
type Point = [number, number];
export type IdleMode = "studying" | "walking" | "drinking" | "eating";
export type IdlePose = { at: V3; angle: number; mode: IdleMode; standing: boolean; stride: number };
const length = (path: Point[]) => path.slice(1).reduce((sum, p, i) => sum + Math.hypot(p[0] - path[i][0], p[1] - path[i][1]), 0);
const smooth = (t: number) => t * t * (3 - 2 * t);
function travel(path: Point[], progress: number, startY = .82, endY = .82): IdlePose {
  let distance = Math.max(0, Math.min(1, progress)) * length(path);
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1], b = path[i], size = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (distance <= size || i === path.length - 1) {
      const t = Math.min(1, distance / size), eased = smooth(t);
      const y = progress < .06 ? startY + (.82 - startY) * smooth(progress / .06) : progress > .94 ? .82 + (endY - .82) * smooth((progress - .94) / .06) : .82;
      return { at: [a[0] + (b[0] - a[0]) * eased, y, a[1] + (b[1] - a[1]) * eased], angle: Math.atan2(b[0] - a[0], b[1] - a[1]), mode: "walking", standing: true, stride: Math.sin(Math.PI * t) };
    }
    distance -= size;
  }
  throw new Error("Invalid office path");
}
export function idlePose(index: number, seconds: number): IdlePose {
  const seat = seatedAt(index), facing = Math.PI + deskAngle(index) + .15;
  if (index >= 4) return { at: seat, angle: facing, mode: "studying", standing: false, stride: 0 };
  // Exit the maker pavilion through its open front, then follow the garden path.
  const aisleZ = deskAt(index)[2] + (deskAngle(index) ? -2.7 : 2.7);
  const exit: Point[] = deskAngle(index) ? [[seat[0], seat[2]], [seat[0], aisleZ], [-5, aisleZ], [-5, -5.5], [-11, -5.5], [-11, -3.3]] : [[seat[0], seat[2]], [seat[0], -5.5], [-11, -5.5], [-11, -3.3]];
  const garden: Point[] = [...exit, [-8.5, 0], [-7.2, 4]];
  const water: Point[] = [...garden, [-5, 8.2], [-.1, 9], [-1.5, 10.5], [-1.5, 11.1]];
  const lunch: Point[] = [...garden, [-5.2, 4.8], [-5.2, 3.4]];
  const waterSeconds = length(water) / .7, lunchSeconds = length(lunch) / .7;
  const stages = [220, waterSeconds, 20, waterSeconds, 160, lunchSeconds, 32, lunchSeconds];
  const duration = stages.reduce((a, b) => a + b, 0);
  let time = (Math.max(0, seconds) + index * 211) % duration;
  let stage = 0;
  while (time >= stages[stage]) time -= stages[stage++];
  if (stage === 1 || stage === 3) return travel(stage === 1 ? water : [...water].reverse(), time / stages[stage], stage === 1 ? .62 : .82, stage === 1 ? .82 : .62);
  if (stage === 5 || stage === 7) return travel(stage === 5 ? lunch : [...lunch].reverse(), time / stages[stage], stage === 5 ? .62 : .5, stage === 5 ? .5 : .62);
  if (stage === 2) return { at: [-1.5, .82, 11.1], angle: 0, mode: "drinking", standing: true, stride: 0 };
  if (stage === 6) return { at: [-5.2, .5, 3.4], angle: 0, mode: "eating", standing: false, stride: 0 };
  return { at: seat, angle: facing, mode: "studying", standing: false, stride: 0 };
}
