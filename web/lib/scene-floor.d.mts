export interface FloorBox { minX: number; maxX: number; minZ: number; maxZ: number }
export interface FloorWorld { floor: [number, number][]; obstacles: FloorBox[]; radius?: number; bounds?: FloorBox }
export function canStand(x: number, z: number, world: FloorWorld, radius?: number, obstacles?: FloorBox[]): boolean;
export function moveOnFloor(position: { x: number; z: number }, delta: { x: number; z: number }, world: FloorWorld): { x: number; z: number };
