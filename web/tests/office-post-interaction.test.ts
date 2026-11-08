// F interaction uses a synthetic scene; no WebGL or private records.
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { test, vi } from "vitest";
import { Vector3 } from "three";
const state = vi.hoisted(() => ({ frame: null as null | (() => void), objects: new Map<string, unknown>() }));
vi.mock("@react-three/fiber", () => ({
  useThree: (selector: (value: unknown) => unknown) => selector({ scene: { getObjectByName: (name: string) => state.objects.get(name) } }),
  useFrame: (callback: () => void) => { state.frame = callback; },
}));
const { InteractWatch } = await import("@/components/office/office-player");
const object = (x: number, z: number) => ({ position: new Vector3(x, 0, z), getWorldPosition: (value: Vector3) => value.set(x, 0, z) });
test("F selects the nearest board or colleague once per interaction and respects range", () => {
  let opened = 0; const selected: string[] = [];
  const controls = { interact: { current: 0 }, player: { current: { x: 0, z: 0 } } } as unknown as Parameters<typeof InteractWatch>[0]["controls"];
  state.objects.set("worker-person", object(3, 0)); state.objects.set("office-posts-board", object(2, 0));
  renderToString(createElement(InteractWatch, { controls, ids: ["person"], targets: [{ name: "office-posts-board", onInteract: () => opened++ }], onSelect: id => selected.push(id) }));
  state.frame!(); assert.equal(opened, 0);
  controls.interact.current++; state.frame!(); state.frame!(); assert.equal(opened, 1); assert.deepEqual(selected, []);
  state.objects.set("worker-person", object(1, 0)); controls.interact.current++; state.frame!(); assert.deepEqual(selected, ["person"]);
  state.objects.set("worker-person", object(100, 0)); state.objects.set("office-posts-board", object(100, 0));
  controls.interact.current++; state.frame!(); assert.equal(opened, 1); assert.equal(selected.length, 1);
});
