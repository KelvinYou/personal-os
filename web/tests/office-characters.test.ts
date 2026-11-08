import { test } from "vitest";
import assert from "node:assert/strict";
import * as characters from "@/lib/office-character";

test("Coach Planner gets gym clothes and exposed legs, without changing its cosmetic identity", () => {
  const id = "skill:coach-planner", before = characters.characterProfile(id), look = characters.characterWardrobe(id, "coach-planner");
  assert.equal(look.family, "athletic"); assert.equal(look.bottom, "shorts"); assert.equal(look.shoes, "trainers");
  assert.deepEqual(characters.characterProfile(id), before);
  assert.deepEqual(characters.characterWardrobe(id, "coach-planner"), look);
});
test("costumes require an explicit skill and never turn transcript text or a nickname into a role", () => {
  assert.equal(characters.characterWardrobe("coach-planner mentioned in a task title").family, "casual");
  assert.equal(characters.characterWardrobe("skill:wealth-manager").family, "casual");
  assert.equal(characters.characterWardrobe("generic-thread", "future-skill").family, "casual");
  assert.equal(characters.characterWardrobe("generic-thread", "constructor").family, "casual");
  assert.equal(characters.characterWardrobe("generic-thread", "travel-plan").accessory, "backpack");
  assert.equal(characters.characterWardrobe("generic-thread", "wealth-manager").outfit, "blazer");
  assert.equal(characters.characterWardrobe("generic-thread", "learning-agent").outfit, "cardigan");
  assert.equal(characters.characterWardrobe("kelvin.ai", undefined, true).family, "host");
});
test("the current named roles have purposeful stable wardrobes while retaining individual identity seeds", () => {
  const expected: Record<string, string[]> = {
    athletic: ["coach-planner"], creative: ["design-doc", "diagram-flow", "skill-creator", "contract-guardian", "repo-orchestrator", "git-commit"],
    study: ["learning-agent", "profile-optimizer", "daily-report", "weekly-review", "decision-log", "decision-review", "identity-audit", "meta-coach"],
    business: ["wealth-manager", "quant-backtest-review"], travel: ["travel-plan"],
  };
  for (const [family, roles] of Object.entries(expected)) for (const skill of roles) {
    const look = characters.characterWardrobe(`skill:${skill}`, skill);
    assert.equal(look.family, family); assert.ok(/^#[0-9a-f]{6}$/i.test(look.shirt));
    if (family !== "athletic") assert.equal(look.bottom, "trousers");
  }
  const looks = expected.creative.map(skill => characters.characterWardrobe(`skill:${skill}`, skill));
  assert.ok(new Set(looks.map(look => look.outfit)).size >= 3, "makers have varied garment silhouettes, not only shirt colors");
});
