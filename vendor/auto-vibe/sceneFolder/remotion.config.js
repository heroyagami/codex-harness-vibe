import { Config } from "@remotion/cli/config";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { resolveSharedBrowserExecutable } from "./scripts/remotion-browser-executable.mjs";

const remotionEntryPoint =
  process.env.REMOTION_ENTRY_POINT || "./remotion/index.tsx";
const configuredBrowserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE;
const browserExecutable =
  typeof configuredBrowserExecutable === "string" &&
  configuredBrowserExecutable.trim().length > 0
    ? configuredBrowserExecutable.trim()
    : resolveSharedBrowserExecutable();

Config.setEntryPoint(remotionEntryPoint);
Config.setChromiumOpenGlRenderer("swangle");
if (existsSync(resolve(process.cwd(), "node_modules/.shared-dependencies"))) {
  Config.setCachingEnabled(false);
}
if (typeof browserExecutable === "string") {
  Config.setBrowserExecutable(browserExecutable);
}
