import { readFileSync, readdirSync, realpathSync, statSync } from "node:fs";
import path from "node:path";
import type { OfficeSkill } from "./office-room";

// Server-side only: the repository skill directory owns membership. No home/plugin
// scan and no SKILL.md bodies or private absolute paths are sent to the browser.
// Rule-only skills (`user-invocable: false` in frontmatter) cannot take a task, so they get no desk.
function isAssignable(file: string): boolean {
  const head = readFileSync(file, "utf8").slice(0, 2000);
  const frontmatter = /^---\r?\n([\s\S]*?)\r?\n---/.exec(head)?.[1] ?? "";
  return !/^user-invocable:\s*false\s*$/m.test(frontmatter);
}

export function loadOfficeSkills(root: string): OfficeSkill[] {
  const directory = realpathSync(path.join(root, ".agents/skills"));
  return readdirSync(directory, { withFileTypes: true })
    .filter(entry => entry.isDirectory() && /^[a-z0-9][a-z0-9-]*$/.test(entry.name))
    .filter(entry => {
      try {
        const file = realpathSync(path.join(directory, entry.name, "SKILL.md"));
        return file.startsWith(directory + path.sep) && statSync(file).isFile();
      } catch { return false; }
    })
    .filter(entry => isAssignable(path.join(directory, entry.name, "SKILL.md")))
    .map(entry => ({ id: entry.name, name: entry.name.split("-").map(word => word[0].toUpperCase() + word.slice(1)).join(" "), path: `.agents/skills/${entry.name}/SKILL.md` }))
    .sort((a, b) => a.id.localeCompare(b.id));
}
