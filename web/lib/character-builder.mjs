// Shared Kenney Mini Characters 2.0 geometry (CC0) for office and home.
// Original silhouette, face, hair, palette and rigid joint pivots are retained.
// +Z faces forward. Figure origin remains .8 above the floor for existing callers.
import { models } from './kenney-mini-data.mjs';

export const FIGURE_FOOT_OFFSET = 0.8;
const MODEL_SCALE = 3.4;
const decode = (text, Type) => new Type(Uint8Array.from(atob(text), c => c.charCodeAt(0)).buffer);

export function buildCharacter({ T }, { profile, look, roaming = true, armPitch = .05 }) {
  const modelId = look.asset ?? `character-${profile.feminine ? 'female' : 'male'}-a`;
  const data = models[modelId];
  if (!data) throw new Error(`Unknown bundled Kenney Mini asset: ${modelId}`);
  const root = new T.Group(), rig = new T.Group(), joints = {}, geometries = [];
  root.userData.asset = modelId;
  rig.scale.setScalar(MODEL_SCALE);
  // Seated callers position the hips over an existing chair; discard source root-motion.
  rig.position.y = roaming ? -FIGURE_FOOT_OFFSET : -.28;
  root.add(rig);
  const material = new T.MeshStandardMaterial({ vertexColors: true, roughness: 1, metalness: 0, side: T.DoubleSide });
  for (const name of Object.keys(data.parts)) joints[name] = new T.Group();
  for (const [name, source] of Object.entries(data.parts)) {
    const joint = joints[name];
    joint.name = name;
    joint.position.set(...source.at);
    (joints[source.parent] ?? rig).add(joint);
    const geometry = new T.BufferGeometry();
    geometry.setAttribute('position', new T.BufferAttribute(decode(source.p, Float32Array), 3));
    geometry.setAttribute('normal', new T.BufferAttribute(decode(source.n, Float32Array), 3));
    const rgb = decode(source.c, Uint8Array), colors = new Float32Array(rgb.length), color = new T.Color();
    for (let i = 0; i < rgb.length; i += 3) {
      color.setRGB(rgb[i] / 255, rgb[i + 1] / 255, rgb[i + 2] / 255, T.SRGBColorSpace);
      colors.set([color.r, color.g, color.b], i);
    }
    geometry.setAttribute('color', new T.BufferAttribute(colors, 3));
    const mesh = new T.Mesh(geometry, material);
    mesh.castShadow = mesh.receiveShadow = true;
    joint.add(mesh); geometries.push(geometry);
  }
  const pose = data.poses[roaming ? 'idle' : 'sit'];
  for (const [name, quaternion] of Object.entries(pose)) if (joints[name]) joints[name].quaternion.set(...quaternion);
  const parts = {
    head: joints.head, arm: joints['arm-right'], leftArm: joints['arm-left'],
    ...(roaming ? { legLeft: joints['leg-left'], legRight: joints['leg-right'] } : {}),
  };
  // Keep original arm Z rotations; existing gestures animate only X.
  parts.arm.rotation.x = parts.leftArm.rotation.x = armPitch;
  return { group: root, parts, dispose: () => { geometries.forEach(g => g.dispose()); material.dispose(); } };
}

export function walkPose(parts, time, stride) {
  const swing = Math.sin(time * 4.2) * .24 * stride;
  if (parts.legLeft) parts.legLeft.rotation.x = swing;
  if (parts.legRight) parts.legRight.rotation.x = -swing;
  if (parts.leftArm) parts.leftArm.rotation.x = stride ? -swing * .65 : .05;
  if (parts.arm) parts.arm.rotation.x = stride ? swing * .65 : .05;
  return swing;
}
