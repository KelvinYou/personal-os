// Single owner of the procedural character geometry shared by /office and /home-design.
// Framework-free: callers inject Three.js (`T`) and RoundedBoxGeometry so the React office
// (npm three) and the standalone home viewer (locally served three) build the same figure.
// Identity and wardrobe data come from web/lib/office-character.ts; this file only draws them.
// Figure space: body origin at the hips, +Z is the front, feet about 0.78 below the origin when standing.
// Style target: polished feature-animation look (tapered jaw, iris eyes, clumped hair, fingers, knit, chunky shoes).
// Small parts (hair locks, fingers) are merged into one mesh each so 19 people stay cheap to draw.

export const FIGURE_FOOT_OFFSET = 0.8; // body origin height above the floor when standing, in figure units

const SAGE = "#9db08c";
const norm = v => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
const hashString = text => { let h = 2166136261; for (const c of text) h = Math.imul(h ^ c.charCodeAt(0), 16777619) >>> 0; return h || 1; };

/**
 * @param {{T: any, RoundedBoxGeometry: any}} lib
 * @param {{profile: any, look: any, roaming?: boolean, mug?: boolean, bowl?: boolean, laptop?: boolean, armPitch?: number}} options
 */
export function buildCharacter({ T, RoundedBoxGeometry }, { profile, look, roaming = true, mug = false, bowl = false, laptop = false, armPitch = -0.65 }) {
  const materials = new Map(), geometries = [], textures = [];
  const { skin, hair, glasses } = profile;
  const shorts = look.bottom === "shorts", longSleeves = look.outfit !== "athletic";
  const knit = ["knit", "cardigan", "hoodie", "overshirt"].includes(look.outfit);

  const material = (color, roughness = 1, extra = {}) => {
    const key = `${color}|${roughness}|${extra.transparent ? "t" : ""}${extra.side ?? ""}${extra.emissive ?? ""}`;
    if (!materials.has(key)) materials.set(key, new T.MeshStandardMaterial({ color, roughness, ...extra }));
    return materials.get(key);
  };
  // Soft skin: a faint warm emissive stands in for subsurface scattering so shadowed cheeks do not go grey.
  const skinMat = material(skin, 0.58, { emissive: "#8f4332", emissiveIntensity: 0.09 });
  const hairMat = material(hair, 0.42);
  const surface = (color, roughness) => color === skin ? skinMat : color === hair ? hairMat : material(color, roughness);

  // Ribbed knit: one canvas gives colour and bump; tinted by the garment colour.
  let ribMap = null, ribBump = null;
  const fabric = color => {
    if (!knit || typeof document === "undefined") return material(color, 0.88);
    if (!ribMap) {
      const canvas = document.createElement("canvas"); canvas.width = canvas.height = 128;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#f1f1f1"; ctx.fillRect(0, 0, 128, 128);
      for (let i = 0; i < 16; i++) { ctx.fillStyle = "rgba(0,0,0,.2)"; ctx.fillRect(i * 8 + 5, 0, 3, 128); ctx.fillStyle = "rgba(255,255,255,.4)"; ctx.fillRect(i * 8 + 1, 0, 2, 128); }
      for (let y = 0; y < 128; y += 8) for (let i = 0; i < 16; i++) { ctx.fillStyle = "rgba(0,0,0,.08)"; ctx.fillRect(i * 8 + 2, y + 4, 4, 2); }
      ribMap = new T.CanvasTexture(canvas); ribMap.colorSpace = T.SRGBColorSpace;
      ribBump = new T.CanvasTexture(canvas);
      [ribMap, ribBump].forEach(t => { t.wrapS = t.wrapT = T.RepeatWrapping; t.repeat.set(2.5, 2.5); t.anisotropy = 4; textures.push(t); });
    }
    const key = `fabric|${color}`;
    if (!materials.has(key)) materials.set(key, new T.MeshStandardMaterial({ color, roughness: 0.95, map: ribMap, bumpMap: ribBump, bumpScale: 1.5 }));
    return materials.get(key);
  };

  const add = (parent, geometry, mat, at, { rotation, scale, cast = true, receive = true } = {}) => {
    geometries.push(geometry);
    const mesh = new T.Mesh(geometry, mat);
    if (at) mesh.position.set(...at);
    if (rotation) mesh.rotation.set(...rotation);
    if (scale) mesh.scale.set(...scale);
    mesh.castShadow = cast; mesh.receiveShadow = receive;
    parent.add(mesh); return mesh;
  };
  const group = (parent, at, rotation) => { const g = new T.Group(); if (at) g.position.set(...at); if (rotation) g.rotation.set(...rotation); parent.add(g); return g; };
  const block = (parent, at, size, color, round = 0.02, rotation) => add(parent, new RoundedBoxGeometry(size[0], size[1], size[2], 2, round), surface(color, 0.82), at, { rotation });
  const pebble = (parent, at, size, color, rotation) => add(parent, new T.SphereGeometry(1, 20, 14), surface(color, 0.84), at, { rotation, scale: size });
  const limbWith = (parent, at, radius, height, mat, rotation) => add(parent, new T.CapsuleGeometry(radius, height - radius * 2, 4, 12), mat, at, { rotation });
  const limb = (parent, at, radius, height, color, rotation) => limbWith(parent, at, radius, height, surface(color, 0.86), rotation);
  const ring = (parent, at, radius, tube, color, rotation = [Math.PI / 2, 0, 0], scale = [1, 1, 1]) => add(parent, new T.TorusGeometry(radius, tube ?? 0.018, 8, 28), material(color, 0.7), at, { rotation, scale, cast: false, receive: false });
  const mugAt = (parent, at) => {
    const g = group(parent, at);
    add(g, new T.CylinderGeometry(0.085, 0.08, 0.2, 12), material("#dce6d9"), [0, 0.1, 0], { cast: false, receive: false });
    ring(g, [0.09, 0.11, 0], 0.05, 0.018, "#dce6d9", [0, Math.PI / 2, 0]);
  };
  // Merge many small pieces into one mesh: { geometry, matrix } with positions already in the parent's space.
  const piece = (geometry, at, euler = [0, 0, 0], scale = [1, 1, 1]) => ({ geometry, matrix: new T.Matrix4().compose(new T.Vector3(...at), new T.Quaternion().setFromEuler(new T.Euler(...euler)), new T.Vector3(...scale)) });
  const merged = (parent, items, mat, options) => {
    const position = [], normal = [], index = []; let base = 0;
    for (const { geometry, matrix } of items) {
      const g = geometry.clone(); g.applyMatrix4(matrix);
      const p = g.attributes.position, n = g.attributes.normal;
      for (let i = 0; i < p.count; i++) { position.push(p.getX(i), p.getY(i), p.getZ(i)); normal.push(n.getX(i), n.getY(i), n.getZ(i)); }
      if (g.index) for (let i = 0; i < g.index.count; i++) index.push(g.index.getX(i) + base); else for (let i = 0; i < p.count; i++) index.push(base + i);
      base += p.count; g.dispose(); geometry.dispose();
    }
    const out = new T.BufferGeometry();
    out.setAttribute("position", new T.Float32BufferAttribute(position, 3)); out.setAttribute("normal", new T.Float32BufferAttribute(normal, 3)); out.setIndex(index);
    return add(parent, out, mat, null, options);
  };

  const root = new T.Group(), parts = {};

  // Lower body: hips plus either walking legs (separate, swingable) or seated thighs. Trouser hems are rolled.
  block(root, [0, 0.23, 0], [0.46, 0.24, 0.34], look.pants, 0.085);
  if (roaming) {
    [-0.15, 0.15].forEach((x, i) => {
      const leg = group(root, [x, 0.2, 0]);
      parts[i === 0 ? "legLeft" : "legRight"] = leg;
      limb(leg, [0, -0.25, 0], 0.104, 0.57, shorts ? skin : look.pants);
      if (shorts) block(leg, [0, -0.11, 0], [0.215, 0.31, 0.24], look.pants, 0.045);
      limb(leg, [0, -0.68, 0], 0.086, 0.43, shorts ? skin : look.pants);
      if (shorts) block(leg, [0, -0.82, 0], [0.175, 0.11, 0.19], look.inner, 0.025).position.z = 0.015;
      else ring(leg, [0, -0.8, 0], 0.096, 0.03, look.pants);
      shoe(leg, [0, -0.92, 0.075]);
    });
  } else {
    [-0.15, 0.15].forEach(x => {
      block(root, [x, 0.15, 0.22], [0.19, 0.21, 0.48], shorts ? skin : look.pants, 0.075);
      if (shorts) block(root, [x, 0.17, 0.1], [0.21, 0.23, 0.32], look.pants, 0.045);
      limb(root, [x, -0.1, 0.39], 0.086, 0.46, shorts ? skin : look.pants);
      if (shorts) block(root, [x, -0.27, 0.42], [0.175, 0.1, 0.19], look.inner, 0.025);
      else ring(root, [x, -0.24, 0.395], 0.096, 0.03, look.pants);
      shoe(root, [x, -0.37, 0.47]);
    });
  }
  // Chunky sneaker: thick cream sole, upper, sage toe cap and heel tab, laces. Loafers stay slim.
  function shoe(parent, at) {
    const loafers = look.shoes === "loafers", g = group(parent, at);
    block(g, [0, -0.047, 0.012], [0.228, 0.062, loafers ? 0.335 : 0.385], loafers ? "#4c4d43" : "#f3f0e5", 0.03);
    block(g, [0, 0.017, 0], [0.205, 0.1, loafers ? 0.31 : 0.345], look.shoe, 0.05);
    if (!loafers) {
      block(g, [0, 0.02, 0.1], [0.21, 0.082, 0.125], SAGE, 0.04);
      block(g, [0, 0.04, -0.15], [0.13, 0.075, 0.04], SAGE, 0.02);
      [0.01, 0.05, 0.09].forEach(z => block(g, [0, 0.07, z - 0.02], [0.11, 0.012, 0.016], "#fbf8ee", 0.004));
    }
  }

  // Torso, outfit layers and shoulders.
  add(root, new T.CapsuleGeometry(0.23, 0.22, 6, 14), fabric(look.shirt), [0, 0.62, 0], { scale: [profile.feminine ? 1.04 : 1.1, 1.04, 0.86] });
  outfit();
  [-1, 1].forEach(side => add(root, new T.SphereGeometry(1, 20, 14), fabric(look.shirt), [side * 0.26, 0.83, -0.01], { scale: [0.112, 0.098, 0.108] }));
  function outfit() {
    const open = ["overshirt", "blazer", "cardigan", "utility"].includes(look.outfit);
    if (open) {
      const s = new T.Shape();
      s.moveTo(-0.11, 0.87); s.lineTo(-0.075, 0.94); s.quadraticCurveTo(0, 0.88, 0.075, 0.94); s.lineTo(0.11, 0.87); s.lineTo(0.09, 0.43); s.lineTo(-0.09, 0.43); s.closePath();
      add(root, new T.ShapeGeometry(s), material(look.inner, 0.9), [0, 0, 0.204], { cast: false, receive: false });
      // Placket buttons down the open edge.
      [0.78, 0.67, 0.56, 0.45].forEach(y => pebble(root, [-0.108, y, 0.208], [0.014, 0.014, 0.008], "#2a2f33"));
    }
    if (look.outfit === "overshirt" || look.outfit === "utility" || look.outfit === "blazer") {
      // Folded collar: two leaves plus a back band.
      [-1, 1].forEach(side => block(root, [side * 0.075, 0.935, 0.125], [0.12, 0.04, 0.095], look.shirt, 0.018, [0.55, 0, side * -0.5]));
      ring(root, [0, 0.935, -0.01], 0.108, 0.026, look.shirt, undefined, [1, 1.12, 1]);
    }
    if (look.outfit === "blazer") [-1, 1].forEach(side => block(root, [side * 0.105, 0.78, 0.199], [0.12, 0.27, 0.03], look.shirt, 0.015, [0, 0, side * -0.26]));
    if (look.outfit === "overshirt" || look.outfit === "utility") [-1, 1].forEach(side => { block(root, [side * 0.155, 0.72, 0.172], [0.13, 0.14, 0.025], look.shirt, 0.015); block(root, [side * 0.155, 0.775, 0.19], [0.13, 0.025, 0.02], look.accent, 0.006); });
    if (look.outfit === "cardigan") { [-1, 1].forEach(side => block(root, [side * 0.125, 0.63, 0.197], [0.035, 0.5, 0.025], look.accent, 0.006)); block(root, [0, 0.345, 0.01], [0.46, 0.055, 0.33], look.shirt, 0.02); }
    if (look.outfit === "knit") { ring(root, [0, 0.945, 0.015], 0.105, 0.03, look.accent, undefined, [1, 1.1, 1]); block(root, [0, 0.35, 0.01], [0.46, 0.05, 0.32], look.accent, 0.02); }
    if (look.outfit === "hoodie") { pebble(root, [0, 0.93, -0.12], [0.25, 0.16, 0.15], look.shirt); block(root, [0, 0.47, 0.18], [0.3, 0.15, 0.035], look.shirt, 0.035); [-1, 1].forEach(side => block(root, [side * 0.065, 0.75, 0.192], [0.012, 0.19, 0.015], look.inner, 0.004)); }
    if (look.outfit === "athletic") { [-1, 1].forEach(side => block(root, [side * 0.224, 0.62, 0.13], [0.035, 0.4, 0.065], look.inner, 0.01)); ring(root, [0, 0.944, 0.015], 0.108, 0.02, look.inner); block(root, [-0.12, 0.75, 0.18], [0.07, 0.06, 0.02], look.accent, 0.012); }
    if (look.accessory === "backpack") {
      block(root, [0, 0.62, -0.215], [0.4, 0.53, 0.14], "#876c4e", 0.065); block(root, [0, 0.56, -0.295], [0.3, 0.25, 0.04], look.accent, 0.035);
      [-1, 1].forEach(side => block(root, [side * 0.18, 0.7, 0.173], [0.04, 0.43, 0.028], "#876c4e", 0.01, [0, 0, side * 0.09])); block(root, [0, 0.91, -0.215], [0.13, 0.07, 0.05], "#876c4e", 0.015);
    }
  }

  // Arms: the right arm (side 1) is `arm`, the left is `leftArm`, matching the office animation.
  // Long sleeves are rolled to mid forearm with a thick cuff; hands have a palm, four fingers and a thumb.
  [-1, 1].forEach(side => {
    const a = group(root, [side * 0.33, 0.86, 0], [armPitch, 0, side * 0.1]);
    parts[side === 1 ? "arm" : "leftArm"] = a;
    limbWith(a, [0, -0.13, 0], 0.09, 0.36, fabric(look.shirt));
    if (longSleeves) {
      limb(a, [0, -0.33, 0.055], 0.066, 0.3, skin, [-0.25, 0, 0]);
      limbWith(a, [0, -0.272, 0.04], 0.079, 0.18, fabric(look.shirt), [-0.25, 0, 0]);
      add(a, new T.CylinderGeometry(0.089, 0.089, 0.06, 20), fabric(look.shirt), [0, -0.359, 0.0623], { rotation: [-0.25, 0, 0] });
      ring(a, [0, -0.388, 0.0695], 0.088, 0.014, look.shirt, [Math.PI / 2 - 0.25, 0, 0]);
    } else {
      limb(a, [0, -0.33, 0.055], 0.075, 0.3, skin, [-0.25, 0, 0]);
    }
    const hand = group(a, [0, -0.475, 0.1], [-0.25, 0, 0]);
    const bits = [piece(new T.SphereGeometry(1, 14, 10), [0, -0.045, 0], [0, 0, 0], [0.052, 0.062, 0.03])];
    [-0.034, -0.011, 0.011, 0.034].forEach((x, i) => { const len = [0.07, 0.084, 0.08, 0.064][i]; bits.push(piece(new T.CapsuleGeometry(0.0155, len - 0.031, 3, 8), [x, -0.107 - len / 2 + 0.014, 0.012], [-0.3, 0, 0])); });
    bits.push(piece(new T.CapsuleGeometry(0.017, 0.03, 3, 8), [-side * 0.052, -0.06, 0.014], [-0.2, 0, -side * 0.6]));
    merged(hand, bits, skinMat);
    if (side === -1 && look.accessory === "watch") {
      ring(a, [0, -0.427, 0.08], 0.071, 0.012, "#6b4a35", [Math.PI / 2 - 0.25, 0, 0]);
      add(a, new T.CylinderGeometry(0.04, 0.04, 0.02, 18), material(look.accent, 0.4), [-0.078, -0.427, 0.082], { rotation: [-0.25, 0, Math.PI / 2] });
      add(a, new T.CylinderGeometry(0.031, 0.031, 0.006, 18), material("#f6f1e4", 0.6), [-0.089, -0.427, 0.082], { rotation: [-0.25, 0, Math.PI / 2], cast: false });
    }
    if (side === 1 && mug) mugAt(a, [0, -0.49, 0.21]);
    if (side === -1 && bowl) add(a, new T.SphereGeometry(0.16, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), material("#d7b68e", 1, { side: T.DoubleSide }), [0, -0.39, 0.23], { cast: false, receive: false });
  });
  if (laptop) { const l = group(root, [0, 0.48, 0.43], [-0.25, 0, 0]); block(l, [0, 0, 0], [0.47, 0.035, 0.31], look.accent, 0.012); [-1, 1].forEach(side => block(l, [side * 0.112, 0.025, 0], [0.215, 0.012, 0.28], "#f3ecd9", 0.003, [0, 0, side * 0.1])); }

  // Neck and head.
  add(root, new T.CylinderGeometry(0.082, 0.094, 0.22, 16), skinMat, [0, 1.0, 0], { receive: false });
  const head = parts.head = group(root, [0, 1.19, 0]);
  head.scale.set(0.9, 0.9, 0.9);
  buildHead(head);
  function buildHead(h) {
    // Skull: a sphere whose lower half narrows into a soft jaw and chin.
    const skull = new T.SphereGeometry(1, 36, 28), p = skull.attributes.position;
    for (let i = 0; i < p.count; i++) { const y = p.getY(i); if (y < 0) { const k = Math.pow(-y, 1.4); p.setX(i, p.getX(i) * (1 - 0.2 * k)); p.setZ(i, p.getZ(i) * (1 - 0.1 * k)); } }
    skull.computeVertexNormals();
    add(h, skull, skinMat, [0, 0, 0], { scale: [0.255, 0.285, 0.225] });

    // Hair: a tilted cap (high forehead, covers the nape) plus tapered locks merged into one mesh.
    const cap = group(h, [0, 0.025, -0.025], [-0.28, 0, 0]);
    add(cap, new T.SphereGeometry(1, 32, 20, 0, Math.PI * 2, 0, Math.PI * 0.42), hairMat, [0, 0, 0], { scale: [0.272, 0.308, 0.244], receive: false });
    pebble(h, [0, 0.0, -0.165], [0.245, 0.2, 0.1], hair);
    let seed = hashString(`${hair}${look.haircut}${look.shirt}`);
    const random = () => { seed = seed * 16807 % 2147483647; return seed / 2147483647; };
    const items = [], up = new T.Vector3(0, 1, 0);
    const surfacePoint = (az, el) => [0.262 * Math.cos(el) * Math.sin(az), 0.296 * Math.sin(el), 0.234 * Math.cos(el) * Math.cos(az)];
    const lock = (az, el, mix, length, radius) => {
      const at = surfacePoint(az, el);
      const n = norm([at[0] / 0.0686, at[1] / 0.0876, at[2] / 0.0548]), tan = [Math.cos(az), 0, -Math.sin(az)];
      const dir = norm([n[0] * mix[0] + tan[0] * mix[1], n[1] * mix[0] + mix[2], n[2] * mix[0] + tan[2] * mix[1]]);
      const q = new T.Quaternion().setFromUnitVectors(up, new T.Vector3(...dir));
      items.push({ geometry: new T.ConeGeometry(radius, length, 8, 1), matrix: new T.Matrix4().compose(new T.Vector3(at[0] + dir[0] * length * 0.4, at[1] + dir[1] * length * 0.4, at[2] + dir[2] * length * 0.4), q, new T.Vector3(1, 1, 0.85)) });
    };
    const kind = look.haircut, long = kind === "waves" ? 0.3 : kind === "bob" ? 0.21 : 0.1;
    const crown = { crop: 15, parted: 14, bob: 10, waves: 10, ponytail: 12, bun: 8 }[kind] ?? 12;
    for (let i = 0; i < crown; i++) lock(i / crown * Math.PI * 2 + random() * 0.3, 0.55 + random() * 0.7, [0.45, 0.95, 0.1], 0.075 + random() * 0.04, 0.055 + random() * 0.012);
    for (let k = -2; k <= 2; k++) lock(k * 0.27, 0.36 + Math.abs(k) * 0.03, [0.4, k * 0.3, -0.55], 0.12 + random() * 0.03, 0.05);
    if (kind === "parted") lock(0.55, 0.5, [0.3, 0.9, -0.3], 0.17, 0.065);
    [-1, 1].forEach(side => { for (let i = 0; i < 4; i++) lock(side * (1.15 + i * 0.28 + random() * 0.1), 0.3 - i * 0.04, [0.5, 0, -0.9], long * (0.8 + random() * 0.3), 0.05); });
    for (let i = 0; i < 7; i++) lock(Math.PI * (0.78 + i * 0.07) * (i % 2 ? 1 : -1), 0.25 + random() * 0.15, [0.5, 0, -0.9], long * 1.3 * (0.8 + random() * 0.3), 0.055);
    merged(cap, items, hairMat, { receive: false });

    if (kind === "bob" || kind === "waves") [-1, 1].forEach(side => pebble(h, [side * 0.21, kind === "waves" ? -0.13 : -0.07, -0.06], [0.085, kind === "waves" ? 0.3 : 0.23, 0.14], hair, [0, 0, side * -0.1]));
    if (kind === "ponytail") { pebble(h, [0, 0.08, -0.265], [0.12, 0.12, 0.11], hair); pebble(h, [0, -0.13, -0.29], [0.09, 0.23, 0.11], hair, [0.25, 0, 0]); ring(h, [0, 0.04, -0.27], 0.085, 0.018, look.accent); }
    if (kind === "bun") { pebble(h, [0, 0.17, -0.25], [0.135, 0.135, 0.12], hair); ring(h, [0, 0.16, -0.25], 0.11, 0.018, look.accent, [0, 0, 0]); }
    if (look.family === "athletic") ring(h, [0, 0.105, -0.015], 0.25, 0.025, look.inner, undefined, [1, 0.9, 1]);

    [-1, 1].forEach(side => {
      const ex = side * 0.097;
      // Ears with a pink inner.
      pebble(h, [side * 0.245, -0.03, -0.005], [0.03, 0.058, 0.04], skin);
      pebble(h, [side * 0.262, -0.03, 0.004], [0.014, 0.036, 0.026], "#e9a994");
      // Eye: cream sclera, brown iris, pupil, two highlights, soft upper lid and a friendly brow.
      pebble(h, [ex, 0, 0.19], [0.047, 0.054, 0.024], "#f7f2ea");
      pebble(h, [ex + side * 0.002, -0.002, 0.203], [0.034, 0.042, 0.014], "#573a28");
      pebble(h, [ex + side * 0.002, -0.002, 0.211], [0.019, 0.024, 0.008], "#17110e");
      pebble(h, [ex - 0.011, 0.017, 0.219], [0.0105, 0.0125, 0.005], "#ffffff");
      pebble(h, [ex + 0.012, -0.018, 0.218], [0.005, 0.006, 0.003], "#fff6e6");
      pebble(h, [ex, 0.047, 0.203], [0.052, 0.012, 0.014], "#2a1d18", [0, 0, side * 0.12]);
      pebble(h, [ex, 0.094, 0.196], [0.058, 0.0135, 0.016], hair, [0, 0, side * -0.1]);
      pebble(h, [side * 0.15, -0.062, 0.173], [0.055, 0.032, 0.012], "#ec9d8f");
      if (glasses) ring(h, [ex + side * 0.001, 0.009, 0.235], 0.071, 0.009, "#58574c", [0, 0, 0], [1, 0.82, 1]);
    });
    if (glasses) block(h, [0, 0.018, 0.237], [0.052, 0.012, 0.013], "#58574c", 0.004);
    pebble(h, [0, -0.047, 0.222], [0.027, 0.034, 0.028], skin);
    add(h, new T.TorusGeometry(0.042, 0.007, 6, 18, Math.PI - 0.4), material("#a66f61"), [0, -0.104, 0.204], { rotation: [0, 0, Math.PI + 0.2], cast: false, receive: false });
    if (look.accessory === "headphones") {
      add(h, new T.TorusGeometry(0.295, 0.023, 8, 28, Math.PI), material("#4b555c"), [0, 0.01, -0.02], { cast: false, receive: false });
      [-1, 1].forEach(side => { pebble(h, [side * 0.285, -0.015, -0.015], [0.055, 0.105, 0.08], "#4b555c"); pebble(h, [side * 0.325, -0.015, -0.015], [0.016, 0.073, 0.055], look.accent); });
    }
  }

  const dispose = () => { geometries.forEach(g => g.dispose()); textures.forEach(t => t.dispose()); materials.forEach(m => m.dispose()); };
  return { group: root, parts, dispose };
}

/** Walking pose shared by every scene: leg and arm swing from a running clock and a 0..1 stride. */
export function walkPose(parts, time, stride) {
  const swing = Math.sin(time * 4.2) * 0.24 * stride;
  if (parts.legLeft) parts.legLeft.rotation.x = swing;
  if (parts.legRight) parts.legRight.rotation.x = -swing;
  if (parts.leftArm) parts.leftArm.rotation.x = stride ? -swing * 0.65 : 0.05;
  if (parts.arm) parts.arm.rotation.x = stride ? swing * 0.65 : 0.05;
  return swing;
}
