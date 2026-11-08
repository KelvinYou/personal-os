// Presentation geometry only. Spatial membership never assigns work or runtime state.
export type LayoutPoint = [number, number, number];
export type GroundPoint = [number, number];
export type Footprint = { x: number; z: number; width: number; depth: number; tall?: boolean };
export const neighborhoods = [
  { id: 'engineering', title: 'MAKER STUDIO', subtitle: 'DESIGN · BUILD · SHIP', x: -11, z: -9, width: 16, depth: 10, color: '#cbb48f', skills: ['design-doc', 'diagram-flow', 'skill-creator', 'contract-guardian', 'repo-orchestrator', 'git-commit'] },
  { id: 'library', title: 'LIBRARY & REFLECTION', subtitle: 'LEARN · RECORD · REFLECT', x: 9, z: -9, width: 18, depth: 10, color: '#d2bd9c', skills: ['learning-agent', 'profile-optimizer', 'daily-report', 'weekly-review', 'decision-log', 'decision-review', 'identity-audit', 'meta-coach'] },
  { id: 'wealth', title: 'WEALTH LAB', subtitle: 'EVIDENCE · RISK · PATIENCE', x: 17, z: 0, width: 6, depth: 6, color: '#c9b28b', skills: ['wealth-manager', 'quant-backtest-review'] },
  { id: 'coach', title: 'COACH STUDIO', subtitle: 'MOVE · RECOVER · PLAN', x: 12, z: 9, width: 12, depth: 8, color: '#d2b68e', skills: ['coach-planner'] },
  { id: 'travel', title: 'TRAVEL ATELIER', subtitle: 'MAPS · CURIOSITY · DISCOVERY', x: -13, z: 8, width: 7, depth: 6, color: '#d2b48e', skills: ['travel-plan'] },
];
const slots = [
  ...[-15.7, -12.7, -9.7].map(x => ({ x, z: -8.46, angle: 0, kind: 'work' })),
  ...[-15.7, -12.7, -9.7].map(x => ({ x, z: -9.54, angle: Math.PI, kind: 'work' })),
  ...[4, 7, 10, 13].map(x => ({ x, z: -8.46, angle: 0, kind: 'study' })),
  ...[4, 7, 10, 13].map((x, i) => ({ x, z: -9.54, angle: Math.PI, kind: i >= 2 ? 'reading' : 'study' })),
  ...[15.5, 18.5].map(x => ({ x, z: -.8, angle: 0, kind: 'work' })),
  { x: 8, z: 7.7, angle: 0, kind: 'study' },
  { x: -13, z: 7, angle: 0, kind: 'study' },
];
export const studioSkills = neighborhoods.flatMap(zone => zone.skills);
export function skillSeat(skillId: string | undefined, fallback = 0, catalog: readonly string[] = []) {
  const known = skillId ? studioSkills.indexOf(skillId) : -1;
  const extra = skillId ? catalog.filter(id => !studioSkills.includes(id)).sort().indexOf(skillId) : -1;
  return known >= 0 ? known : skillId ? studioSkills.length + (extra >= 0 ? extra : fallback) : fallback;
}
export function seatLayout(index: number) {
  return slots[index] ?? { x: -4 + (index % 6 % 3) * 4, z: 19 + Math.floor((index - 18) / 6) * 6 + (index % 6 < 3 ? .54 : -.54), angle: index % 6 < 3 ? 0 : Math.PI, kind: 'work' };
}
export const floorDepth = (count: number) => 40 + Math.ceil(Math.max(0, count - 18) / 6) * 6;
export function groundOutline(count: number): GroundPoint[] {
  const extra = floorDepth(count) - 40;
  return Array.from({ length: 96 }, (_, index) => {
    const t = index / 96 * Math.PI * 2;
    const ripple = 1 + .035 * Math.sin(t * 3) + .025 * Math.cos(t * 5);
    const c = Math.cos(t), s = Math.sin(t);
    return [Math.sign(c) * Math.abs(c) ** .7 * 26 * ripple, Math.sign(s) * Math.abs(s) ** .7 * (20 + extra / 2) * ripple + extra / 2];
  });
}
export const hostDesk: LayoutPoint = [-3, 0, 12];
export const hostSeat: LayoutPoint = [-3.05, .62, 13.25];
export const amenities: Record<string, Footprint> = {
  tree: { x: -2, z: 1.4, width: .65, depth: .65, tall: true },
  treeWest: { x: -22, z: -12, width: .7, depth: .7, tall: true },
  treeEast: { x: 21.5, z: -11, width: .7, depth: .7, tall: true },
  project: { x: 1.6, z: 3.1, width: 1.9, depth: 1.9 },
  bench: { x: -5.2, z: 3.4, width: 2.6, depth: .8 },
  pantry: { x: -3, z: 12, width: 5, depth: .9, tall: true },
  hostChair: { x: -3.05, z: 13.3, width: .85, depth: 1.05 },
  coffeeStoolLeft: { x: -4.6, z: 13.3, width: .5, depth: .5 },
  coffeeStoolRight: { x: -1.4, z: 13.3, width: .5, depth: .5 },
  library: { x: 1.7, z: -11, width: .65, depth: 4.4, tall: true },
  archive: { x: 16.3, z: -10.8, width: .65, depth: 4.4, tall: true },
  travelMap: { x: -13, z: 5.3, width: 4.5, depth: .13, tall: true },
  dailyBoard: { x: 9, z: -13.7, width: 5, depth: .12, tall: true },
  rack: { x: 14.2, z: 6.4, width: 2.6, depth: 1.4, tall: true },
  weights: { x: 17.1, z: 9.8, width: .65, depth: 2.4, tall: true },
  trainingBench: { x: 13.5, z: 10, width: .7, depth: 1.9 },
};
export const tableSeats = [
  { x: 1.6, z: 1.65, yaw: 0 }, { x: 3.05, z: 3.1, yaw: -Math.PI / 2 },
  { x: 1.6, z: 4.55, yaw: Math.PI }, { x: .15, z: 3.1, yaw: Math.PI / 2 },
];
export const coffeePosts = [{ x: -5.65, z: 11.1 }, { x: -.35, z: 11.1 }, { x: -5.65, z: 14 }, { x: -.35, z: 14 }];
export function buildingWalls(): Footprint[] {
  return neighborhoods.flatMap(zone => [
    { x: zone.x, z: zone.z - zone.depth / 2, width: zone.width, depth: .18, tall: true },
    ...[-1, 1].map(side => ({ x: zone.x + side * zone.width / 2, z: zone.z, width: .18, depth: zone.depth, tall: true })),
    ...[-1, 1].map(side => ({ x: zone.x + side * (zone.width / 2 - .12), z: zone.z + zone.depth / 2, width: .24, depth: .24, tall: true })),
  ]);
}
export function seatFurniture(index: number): Footprint[] {
  const seat = seatLayout(index), side = seat.angle ? -1 : 1;
  const chair = { x: seat.x - .05 * side, z: seat.z + 1.3 * side, width: .85, depth: 1.05 };
  return [seat.kind === 'reading' ? { x: seat.x - 1 * side, z: seat.z + .3 * side, width: .55, depth: .55 } : { x: seat.x, z: seat.z, width: 2.65, depth: 1.08 }, chair];
}
// The path is a presentation surface. Grass is intentionally walkable too.
export const villagePaths: { points: GroundPoint[]; width: number; closed?: boolean }[] = [
  { points: [[-11, -3.3], [-17, 0], [-17, 4], [-9, 11.9], [0, 13.9], [8, 14.1], [18.9, 6], [21.7, 1], [19.8, -3.2], [8, -3.1], [-1, -2.7]], width: 1.65, closed: true },
  { points: [[-11, -4.2], [-11, -3.3], [-8.5, 0], [-7.2, 4], [-5, 8.2], [-.1, 9], [4.7, 6], [6, 1], [7, -3.2], [9, -4.2]], width: 1.45 },
  { points: [[-13, 11], [-12, 11.8]], width: 2.1 },
  { points: [[12, 13], [11, 13.9]], width: 2.1 },
  { points: [[17, 3], [17, 4.7], [18.9, 6]], width: 1.8 },
  { points: [[-.1, 15.7], [-.1, 13.9], [-.1, 9], [1.6, 6], [1.6, 5.1]], width: 1.6 },
];
