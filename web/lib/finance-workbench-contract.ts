import schema from "./finance-workbench.schema.json";
import type { WorkbenchSnapshot } from "./finance-workbench.gen";

type Node = Record<string, unknown>;
// Interpret the emitted schema rather than maintaining another hand-written report shape.
function valid(value: unknown, node: Node): boolean {
  if (typeof node.$ref === "string") return valid(value, (schema.$defs as Record<string, Node>)[node.$ref.split("/").at(-1)!]);
  if (Array.isArray(node.anyOf)) return node.anyOf.some(n => valid(value, n));
  if ("const" in node && value !== node.const) return false;
  if (Array.isArray(node.enum) && !node.enum.includes(value)) return false;
  if (node.type === "null") return value === null;
  if (node.type === "boolean") return typeof value === "boolean";
  if (node.type === "string") {
    if (typeof value !== "string" || (typeof node.minLength === "number" && value.length < node.minLength) || (typeof node.maxLength === "number" && value.length > node.maxLength)) return false;
    if (typeof node.pattern === "string" && !new RegExp(node.pattern).test(value)) return false;
    if (node.format === "date" && (!/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(Date.parse(value)) || new Date(value).toISOString().slice(0, 10) !== value)) return false;
    return true;
  }
  if (node.type === "number" || node.type === "integer") {
    if (typeof value !== "number" || !Number.isFinite(value) || (node.type === "integer" && !Number.isInteger(value))) return false;
    return !(typeof node.minimum === "number" && value < node.minimum || typeof node.exclusiveMinimum === "number" && value <= node.exclusiveMinimum || typeof node.maximum === "number" && value > node.maximum);
  }
  if (node.type === "array") return Array.isArray(value) && value.every(item => valid(item, node.items as Node));
  if (node.type === "object") {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const object = value as Node, properties = node.properties as Record<string, Node>;
    return (!(node.required as string[] | undefined)?.some(key => !(key in object))) && Object.entries(object).every(([key, item]) => properties[key] ? valid(item, properties[key]) : node.additionalProperties !== false);
  }
  return true;
}
export function parseWorkbenchSnapshot(value: unknown): WorkbenchSnapshot {
  if (!valid(value, schema as Node)) throw new Error("Invalid finance workbench contract");
  return value as WorkbenchSnapshot;
}
