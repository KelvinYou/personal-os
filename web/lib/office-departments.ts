// One flat town on /office: Lab, Finance and Content Lab are
// open, roofless buildings standing on a grass town with paths, a plaza, trees,
// shrubs and flower beds. No doors, no page changes. kelvin.ai can walk anywhere.
// World units, worldScale 1.37 (scene standard §4). +Z faces the overview camera.
import { ROOM } from "./office-radar";
import { createPlayer, officeParams, type WalkWorld } from "./office-navigation";
import type { FloorBox } from "./scene-floor.mjs";

export type Department = "lab" | "finance" | "content";
export type FinanceStation = "assets" | "notices" | "analysis" | "research";
export type ContentStation = "research" | "production" | "review" | "results";
export type DepartmentSelection = { department: "lab" | "finance"; station: FinanceStation } | { department: "content"; station: ContentStation };
export interface Area { id: string; title: string; x: number; z: number; width: number; depth: number }
export type Rect = { x: number; z: number; width: number; depth: number };

export const departments: Record<Department, Area> = {
  // First building: the attention radar, at its original origin so every radar slot stays valid.
  lab: { id: "lab", title: "Lab", x: 0, z: 0, width: ROOM.width, depth: ROOM.depth },
  // Second building: Finance, across a small plaza from the Lab.
  finance: { id: "finance", title: "Finance", x: 34, z: 0, width: 18, depth: ROOM.depth },
  content: { id: "content", title: "Content Lab", x: -30, z: 0, width: 18, depth: ROOM.depth },
};
export const departmentOrder: Department[] = ["content", "lab", "finance"];

const labRight = departments.lab.x + departments.lab.width / 2;
const financeLeft = departments.finance.x - departments.finance.width / 2;
/** The square between the buildings: paved, with a round planter, benches and lamps. */
export const PLAZA: Rect = { x: (labRight + financeLeft) / 2, z: 2, width: financeLeft - labRight - 2, depth: 12 };
/** Main avenue in front of both buildings. */
export const AVENUE: Rect = { x: 1, z: 14, width: 100, depth: 3.4 };
/** Grass ground of the whole town. */
export const GROUND: Rect = { x: 1, z: 3, width: 108, depth: 50 };
/** How far an overview orbit target lies outside the town ground; pan shifts camera and target back by this. */
export function panOvershoot(x: number, z: number, area: Rect = GROUND): [number, number] {
  const over = (value: number, centre: number, half: number) => value > centre + half ? value - centre - half : value < centre - half ? value - centre + half : 0;
  return [over(x, area.x, area.width / 2), over(z, area.z, area.depth / 2)];
}
/** Paved paths: the avenue, a front path from each building, the plaza and its link to the avenue. */
export const paths: Rect[] = [
  AVENUE,
  PLAZA,
  { x: PLAZA.x, z: (PLAZA.z + PLAZA.depth / 2 + AVENUE.z) / 2, width: 3, depth: AVENUE.z - PLAZA.z - PLAZA.depth / 2 },
  ...departmentOrder.map(id => { const a = departments[id]; const front = a.z + a.depth / 2; return { x: a.x, z: (front + AVENUE.z) / 2, width: 4, depth: AVENUE.z - front }; }),
];
export const PLANTER = { x: PLAZA.x, z: PLAZA.z, radius: 1.6 };

/** Overview framing for the whole town: all three buildings, plaza and avenue. */
export const town: Area = (() => {
  const areas = departmentOrder.map(id => departments[id]);
  const left = Math.min(...areas.map(a => a.x - a.width / 2)), right = Math.max(...areas.map(a => a.x + a.width / 2));
  const back = -ROOM.depth / 2, front = AVENUE.z + AVENUE.depth / 2;
  return { id: "town", title: "Town", x: (left + right) / 2, z: (back + front) / 2, width: right - left, depth: front - back };
})();

const fx = departments.finance.x;
/** Finance desks in town coordinates; a desk faces the camera, its chair in front. */
export const financeStations: { id: FinanceStation; title: string; short: string; x: number; z: number }[] = [
  { id: "assets", title: "Asset overview", short: "Assets", x: fx - 5, z: -3 },
  { id: "notices", title: "Finance notices", short: "Notices", x: fx, z: -3 },
  { id: "analysis", title: "Finance workbench", short: "Workbench", x: fx + 5, z: -3 },
  // The Finance manager's desk, front-centre: proposals the owner reviews (docs/design/finance-research.md).
  { id: "research", title: "Research desk", short: "Research", x: fx, z: 2.5 },
];
/** The Finance manager stands beside the research desk, facing the camera. Not an obstacle, like every person. */
export const financeManagerSpot = { x: fx + 2.1, z: 2.9 };
export const contentStations: { id: ContentStation; title: string; x: number; z: number }[] = [
  { id: "research", title: "Ideas", x: -35, z: -4 },
  { id: "production", title: "Pipeline", x: -25, z: -4 },
  { id: "review", title: "Review", x: -35, z: 3.5 },
  { id: "results", title: "Results", x: -25, z: 3.5 },
];

// ---- Greenery: deterministic (seeded LCG, scene standard §1), never on a building or path ----
export interface Tree { x: number; z: number; scale: number; kind: "round" | "pine"; tint: number }
export interface Bush { x: number; z: number; scale: number; tint: number }
export interface FlowerBed { x: number; z: number; width: number; depth: number }
const inflate = (r: Rect, by: number): Rect => ({ ...r, width: r.width + by * 2, depth: r.depth + by * 2 });
const inside = (r: Rect, x: number, z: number) => Math.abs(x - r.x) <= r.width / 2 && Math.abs(z - r.z) <= r.depth / 2;
const buildingRects = (): Rect[] => departmentOrder.map(id => departments[id]);
/** Areas greenery must leave clear: buildings (with a margin for walking around them), paths and the planter. */
export const keepClear = (): Rect[] => [...buildingRects().map(r => inflate(r, 1.6)), ...paths.map(p => inflate(p, .6))];

function lcg(seed: number) { let s = seed; return () => (s = s * 16807 % 2147483647) / 2147483647; }

export const flowerBeds: FlowerBed[] = [
  // Either side of each building's front path, and two at the plaza's avenue edge.
  ...departmentOrder.flatMap(id => { const a = departments[id]; const z = a.z + a.depth / 2 + 1.7; return [-1, 1].map(side => ({ x: a.x + side * 4.4, z, width: 4, depth: 1.4 })); }),
  ...[-1, 1].map(side => ({ x: PLAZA.x + side * 3.4, z: PLAZA.z + PLAZA.depth / 2 + 1.6, width: 2.6, depth: 1.4 })),
];

/** Trees in bands around the town and a few in the plaza corners. */
export const trees: Tree[] = (() => {
  const random = lcg(20261108), clear = keepClear(), out: Tree[] = [];
  const bands: Rect[] = [
    { x: GROUND.x, z: -17, width: GROUND.width - 6, depth: 8 },                  // behind the buildings
    { x: GROUND.x, z: 22, width: GROUND.width - 6, depth: 8 },                   // across the avenue
    { x: GROUND.x - GROUND.width / 2 + 5, z: 2, width: 7, depth: 30 },           // west edge
    { x: GROUND.x + GROUND.width / 2 - 5, z: 2, width: 7, depth: 30 },           // east edge
  ];
  for (const band of bands) {
    const count = Math.round(band.width * band.depth / 26);
    for (let i = 0, tries = 0; i < count && tries < count * 20; tries++) {
      const x = band.x + (random() - .5) * band.width, z = band.z + (random() - .5) * band.depth;
      if (clear.some(r => inside(r, x, z)) || flowerBeds.some(b => inside(inflate(b, .8), x, z)) || out.some(t => Math.hypot(t.x - x, t.z - z) < 3.1)) continue;
      out.push({ x, z, scale: .85 + random() * .5, kind: random() < .35 ? "pine" : "round", tint: Math.floor(random() * 3) }); i++;
    }
  }
  // Four shade trees in the plaza's own corners (paved, so they bypass the keep-clear test).
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) out.push({ x: PLAZA.x + sx * (PLAZA.width / 2 - 1.2), z: PLAZA.z + sz * (PLAZA.depth / 2 - 1.2), scale: .75, kind: "round", tint: (sx + sz + 2) % 3 });
  out.push({ x: PLANTER.x, z: PLANTER.z, scale: 1.15, kind: "round", tint: 1 }); // the planter's centre tree
  return out;
})();

/** Low shrubs along the building fronts' side margins and beside the avenue. */
export const bushes: Bush[] = (() => {
  const random = lcg(1108), out: Bush[] = [];
  for (const id of departmentOrder) {
    const a = departments[id];
    for (const side of [-1, 1]) for (let k = 0; k < 4; k++) out.push({ x: a.x + side * (a.width / 2 + 1), z: a.z - a.depth / 2 + 2.5 + k * 5, scale: .8 + random() * .4, tint: Math.floor(random() * 3) });
  }
  return out.filter(b => !paths.some(p => inside(inflate(p, .4), b.x, b.z)));
})();

/** Street lamps along the avenue's town side, clear of the paths that meet it. */
export const lamps: { x: number; z: number }[] = Array.from({ length: 9 }, (_, i) => ({ x: AVENUE.x - AVENUE.width / 2 + 6 + i * 8, z: AVENUE.z - AVENUE.depth / 2 - .5 }))
  .filter(l => !paths.slice(1).some(p => inside(inflate(p, .6), l.x, l.z)));
export const plazaBenches = [-1, 1].map(side => ({ x: PLAZA.x + side * 3, z: PLAZA.z, yaw: side * Math.PI / 2 }));

// ---- Walking (shared controller, scene standard §2) ----
const box = (r: Rect): FloorBox => ({ minX: r.x - r.width / 2, maxX: r.x + r.width / 2, minZ: r.z - r.depth / 2, maxZ: r.z + r.depth / 2 });
const rect = (x: number, z: number, width: number, depth: number): Rect => ({ x, z, width, depth });

/** Solid things kelvin.ai walks around. People are not obstacles: they move with observed state. */
export function townObstacles(stationXs: number[], stationZ: number, doneBenchZ: number, reviewDesk: { x: number; z: number }): Rect[] {
  const walls = departmentOrder.map(id => { const a = departments[id]; return rect(a.x, a.z - a.depth / 2, a.width, .5); });
  return [
    ...walls,
    ...stationXs.flatMap(x => [rect(x, stationZ - .1, 3, 1.7), rect(x, stationZ + .95, .8, .76)]),
    ...Array.from({ length: 8 }, (_, i) => rect(-10 + i * 2.85, doneBenchZ, 2.2, .8)),
    rect(reviewDesk.x, reviewDesk.z, 3.2, 1.7),
    ...financeStations.flatMap(s => [rect(s.x, s.z, 3.2, 1.7), rect(s.x, s.z + .95, .8, .76)]),
    ...contentStations.map(s => rect(s.x, s.z, 3.2, 1.7)),
    rect(fx - departments.finance.width / 2 + 1.6, -ROOM.depth / 2 + 1.4, 2, 1), rect(fx + departments.finance.width / 2 - 2, 3, 1, 1),
    rect(fx + 4, 5.5, 2.4, 2.4), rect(fx - 4, 6.5, 2.2, .8),
    rect(PLANTER.x, PLANTER.z, PLANTER.radius * 2, PLANTER.radius * 2),
    ...plazaBenches.map(b => rect(b.x, b.z, .8, 2.2)),
    ...trees.map(t => rect(t.x, t.z, .7 * t.scale, .7 * t.scale)),
    ...lamps.map(l => rect(l.x, l.z, .35, .35)),
    ...flowerBeds.map(b => rect(b.x, b.z, b.width, b.depth)),
  ];
}

export function townWalkWorld(obstacles: Rect[]): WalkWorld {
  const bounds = box(inflate(GROUND, -1.5));
  const boxes = obstacles.map(box);
  const ground: [number, number][] = [[bounds.minX, bounds.minZ], [bounds.maxX, bounds.minZ], [bounds.maxX, bounds.maxZ], [bounds.minX, bounds.maxZ]];
  const rects = boxes.map(b => ({ x: (b.minX + b.maxX) / 2, z: (b.minZ + b.maxZ) / 2, halfX: (b.maxX - b.minX) / 2, halfZ: (b.maxZ - b.minZ) / 2 }));
  // Owner choice (2026-11-08): one brisk walk at the standard run speed, and no separate run.
  return { ...bounds, ground, floor: ground, bounds, boxes, cameraBoxes: boxes, obstacles: rects, cameraWalls: rects, radius: officeParams.collisionRadius, sim: { floor: ground, bounds, obstacles: boxes, radius: officeParams.collisionRadius }, walkSpeed: TOWN_WALK_SPEED };
}
export const TOWN_WALK_SPEED = officeParams.runSpeed;

/** kelvin.ai starts in the plaza, in front of the planter, facing the back of the town. */
export const townSpawn = () => ({ ...createPlayer(), x: PLAZA.x, z: PLAZA.z + 3.6, yaw: 0, facing: 0 });

export const isDepartment = (value: unknown): value is Department => value === "lab" || value === "finance" || value === "content";
export const isFinanceStation = (value: unknown): value is FinanceStation => financeStations.some(s => s.id === value);
export const isContentStation = (value: unknown): value is ContentStation => contentStations.some(s => s.id === value);

/** Department-specific deep links; unknown content stations select Research, Finance selects Workbench. */
export function departmentFromQuery(params: URLSearchParams): DepartmentSelection {
  const dept = params.get("dept"), station = params.get("station");
  if (dept === "content") return { department: "content", station: isContentStation(station) ? station : "research" };
  return { department: dept === "finance" ? "finance" : "lab", station: isFinanceStation(station) ? station : "analysis" };
}

/** Old `/office/world` links land on the matching department of the town. */
export function legacyWorldRedirect(params: Record<string, string | string[] | undefined>): string {
  const query = new URLSearchParams();
  if (params.place === "finance") query.set("dept", "finance");
  if (params.mode === "demo") query.set("mode", "demo");
  const text = query.toString();
  return `/office${text ? `?${text}` : ""}`;
}
