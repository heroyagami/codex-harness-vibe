import { readFileSync } from "node:fs";
import { basename, resolve } from "node:path";
import {
  ensureSharedBrowserExecutable,
  runLocalRemotionCli,
} from "./remotion-browser-executable.mjs";

// Video compositions already include the opaque shared background. Alpha
// transition handles are rendered separately as PNG stills.
const DEFAULT_CODEC = "h264";
const DEFAULT_PRORES_PROFILE = "light";
const DEFAULT_PRORES_PIXEL_FORMAT = "yuv422p10le";
const DEFAULT_H264_PIXEL_FORMAT = "yuv420p";
const DEFAULT_H264_CRF = "18";
const DEFAULT_X264_PRESET = "medium";
const DEFAULT_IMAGE_FORMAT = "png";
const DEFAULT_SCALE = "1";
const DEFAULT_COMPOSITION_ID = "default";

const compositionId = (
  process.env.REMOTION_COMPOSITION_ID || DEFAULT_COMPOSITION_ID
).trim();
const fps = (process.env.REMOTION_FPS || "").trim();
const defaultOutputPath = `${basename(process.cwd())}.mov`;
const outputPath = (process.env.REMOTION_OUTPUT || defaultOutputPath).trim();
const codec = (process.env.REMOTION_CODEC || DEFAULT_CODEC).trim();
const proresProfile = (
  process.env.REMOTION_PRORES_PROFILE || DEFAULT_PRORES_PROFILE
).trim();
const pixelFormat = (
  process.env.REMOTION_PIXEL_FORMAT ||
  (codec === "prores" ? DEFAULT_PRORES_PIXEL_FORMAT : DEFAULT_H264_PIXEL_FORMAT)
).trim();
const crf = (
  process.env.REMOTION_CRF || (codec === "h264" ? DEFAULT_H264_CRF : "")
).trim();
const x264Preset = (
  process.env.REMOTION_X264_PRESET ||
  (codec === "h264" ? DEFAULT_X264_PRESET : "")
).trim();
const imageFormat = (
  process.env.REMOTION_IMAGE_FORMAT || DEFAULT_IMAGE_FORMAT
).trim();
const scale = (process.env.REMOTION_SCALE || DEFAULT_SCALE).trim();
// Keep WebGL/canvas-heavy scenes renderable in chrome-headless-shell by
// defaulting to the software GL backend. Override with REMOTION_GL if needed.
const gl = (process.env.REMOTION_GL || "swangle").trim();
const propsJson = process.env.REMOTION_PROPS_JSON;
const propsFilePath = process.env.REMOTION_PROPS_FILE;

const resolvePropsJson = () => {
  if (typeof propsJson === "string" && propsJson.trim().length > 0) {
    return propsJson.trim();
  }

  if (typeof propsFilePath !== "string" || propsFilePath.trim().length === 0) {
    return "";
  }

  const absolutePropsFilePath = resolve(process.cwd(), propsFilePath.trim());
  const fileContent = readFileSync(absolutePropsFilePath, "utf8");
  const parsed = JSON.parse(fileContent);
  return JSON.stringify(parsed);
};

const run = async () => {
  const resolvedPropsJson = resolvePropsJson();
  const fpsForLog = fps.length > 0 ? fps : "composition-default";
  const browserExecutable = await ensureSharedBrowserExecutable({
    logPrefix: "[Remotion][Browser]",
  });

  const args = [
    "render",
    compositionId,
    outputPath,
    "--codec",
    codec,
    "--pixel-format",
    pixelFormat,
    "--image-format",
    imageFormat,
    "--muted",
    "--scale",
    scale,
    "--gl",
    gl,
  ];

  if (codec === "prores") {
    args.push("--prores-profile", proresProfile);
  }

  if (crf.length > 0) {
    args.push("--crf", crf);
  }

  if (x264Preset.length > 0) {
    args.push("--x264-preset", x264Preset);
  }

  if (fps.length > 0) {
    args.push("--fps", fps);
  }

  if (resolvedPropsJson.length > 0) {
    args.push("--props", resolvedPropsJson);
  }

  if (browserExecutable) {
    args.push("--browser-executable", browserExecutable);
  }

  const env = browserExecutable
    ? { ...process.env, REMOTION_BROWSER_EXECUTABLE: browserExecutable }
    : process.env;

  console.log(
    `[Remotion] render ${compositionId} -> ${outputPath} (fps=${fpsForLog}, codec=${codec})`,
  );
  if (browserExecutable) {
    console.log(`[Remotion] browserExecutable=${browserExecutable}`);
  }

  const result = runLocalRemotionCli({
    args,
    stdio: "inherit",
    env,
  });

  if (result.error) {
    console.error(`[Remotion] failed to run render: ${result.error.message}`);
    process.exit(1);
  }

  if (typeof result.status === "number" && result.status !== 0) {
    process.exit(result.status);
  }
};

run().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`[Remotion] ${message}`);
  process.exit(1);
});
