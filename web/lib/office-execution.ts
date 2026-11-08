import "server-only";
import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { OfficeExecution, ExecutionError } from "./office-execution-runtime";
import { OfficeWorkStore } from "./office-work-store";
import type { ExecutionConfig } from "./office-execution-contract";

const root = path.resolve(process.cwd(), "..");
const run = promisify(execFile);
const globalExecution = globalThis as typeof globalThis & { officeDirectExecution?: OfficeExecution; officeDirectLoading?: Promise<OfficeExecution> };
export { ExecutionError };
export async function execution(): Promise<OfficeExecution> {
  if (globalExecution.officeDirectExecution) return globalExecution.officeDirectExecution;
  if (!globalExecution.officeDirectLoading) {
    globalExecution.officeDirectLoading = (async () => {
      try {
        const { stdout } = await run(path.join(root, ".venv/bin/python3"), [path.join(root, "scripts/office_execution_config.py")], { cwd: root, timeout: 10000, maxBuffer: 16384 });
        const config = JSON.parse(stdout) as ExecutionConfig;
        if (!config.enabled) throw new Error();
        // Server environment PATH selects the installed official CLI; no browser override.
        const instance = new OfficeExecution({ root, binary: "codex", config, archive: new OfficeWorkStore(root) });
        globalExecution.officeDirectExecution = instance;
        process.once("exit", () => instance.close());
        return instance;
      } catch { throw new ExecutionError("execution_not_configured"); }
      finally { globalExecution.officeDirectLoading = undefined; }
    })();
  }
  return globalExecution.officeDirectLoading;
}
