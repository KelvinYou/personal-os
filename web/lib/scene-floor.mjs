// Single owner of flat-floor collision for every scene (docs/design/3d-scene-standard.md section 2).
// World: { floor: [[x,z],...] polygon, obstacles: [{minX,maxX,minZ,maxZ}], radius?, bounds?: {minX,maxX,minZ,maxZ} }.
// Callers may override the body radius and obstacle list, e.g. for camera clearance.
export function canStand(x, z, world, radius = world.radius ?? 0.18, obstacles = world.obstacles) {
  const b = world.bounds;
  if (b && (x < b.minX + radius || x > b.maxX - radius || z < b.minZ + radius || z > b.maxZ - radius)) return false;
  // Sample the body perimeter as well as its center against the floor polygon.
  for (let i = -1; i < 16; i++) {
    const px = x + (i < 0 ? 0 : Math.cos(i * Math.PI / 8) * radius);
    const pz = z + (i < 0 ? 0 : Math.sin(i * Math.PI / 8) * radius);
    let inside = false;
    const polygon = world.floor;
    for (let j = 0, k = polygon.length - 1; j < polygon.length; k = j++) {
      const [ax, az] = polygon[j], [bx, bz] = polygon[k];
      if ((az > pz) !== (bz > pz) && px < (bx - ax) * (pz - az) / (bz - az) + ax) inside = !inside;
    }
    if (!inside) return false;
  }
  for (const box of obstacles) {
    const nearX = Math.max(box.minX, Math.min(x, box.maxX));
    const nearZ = Math.max(box.minZ, Math.min(z, box.maxZ));
    if ((nearX - x) ** 2 + (nearZ - z) ** 2 < radius ** 2) return false;
  }
  return true;
}

export function moveOnFloor(position, delta, world) {
  const result = { x: position.x, z: position.z };
  // Substeps prevent tunnelling through a thin wall even after a delayed frame.
  const steps = Math.max(1, Math.ceil(Math.hypot(delta.x, delta.z) / ((world.radius ?? 0.18) / 2)));
  for (let i = 0; i < steps; i++) {
    const x = result.x + delta.x / steps, z = result.z + delta.z / steps;
    if (canStand(x, z, world)) { result.x = x; result.z = z; }
    else {
      if (canStand(x, result.z, world)) result.x = x;
      if (canStand(result.x, z, world)) result.z = z;
    }
  }
  return result;
}
