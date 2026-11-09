// Interpret a Pydantic-emitted JSON schema rather than maintaining another hand-written shape.
// Covers the subset Pydantic emits for the finance contracts: $ref, anyOf, const, enum,
// scalar bounds, date strings, arrays, objects and dict-style additionalProperties.
type Node = Record<string, unknown>;

export function schemaValidator(schema: Node) {
  const defs = (schema.$defs ?? {}) as Record<string, Node>;
  function valid(value: unknown, node: Node): boolean {
    if (typeof node.$ref === "string") return valid(value, defs[node.$ref.split("/").at(-1)!]);
    if (Array.isArray(node.anyOf)) return node.anyOf.some(n => valid(value, n));
    if ("const" in node && value !== node.const) return false;
    if (Array.isArray(node.enum) && !node.enum.includes(value)) return false;
    if (node.type === "null") return value === null;
    if (node.type === "boolean") return typeof value === "boolean";
    if (node.type === "string") {
      if (typeof value !== "string" || (typeof node.minLength === "number" && value.length < node.minLength) || (typeof node.maxLength === "number" && value.length > node.maxLength)) return false;
      if (typeof node.pattern === "string" && !new RegExp(node.pattern).test(value)) return false;
      if (node.format === "date" && (!/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(Date.parse(value)) || new Date(value).toISOString().slice(0, 10) !== value)) return false;
      if (node.format === "date-time" && !Number.isFinite(Date.parse(value))) return false;
      return true;
    }
    if (node.type === "number" || node.type === "integer") {
      if (typeof value !== "number" || !Number.isFinite(value) || (node.type === "integer" && !Number.isInteger(value))) return false;
      return !(typeof node.minimum === "number" && value < node.minimum || typeof node.exclusiveMinimum === "number" && value <= node.exclusiveMinimum
        || typeof node.maximum === "number" && value > node.maximum || typeof node.exclusiveMaximum === "number" && value >= node.exclusiveMaximum);
    }
    if (node.type === "array") return Array.isArray(value) && value.every(item => valid(item, node.items as Node));
    if (node.type === "object") {
      if (!value || typeof value !== "object" || Array.isArray(value)) return false;
      const object = value as Node, properties = (node.properties ?? {}) as Record<string, Node>, extra = node.additionalProperties;
      if ((node.required as string[] | undefined)?.some(key => !(key in object))) return false;
      return Object.entries(object).every(([key, item]) => properties[key] ? valid(item, properties[key])
        : extra === false ? false : typeof extra === "object" && extra ? valid(item, extra as Node) : true);
    }
    return true;
  }
  return (value: unknown, def?: string) => valid(value, def ? defs[def] : schema);
}
