import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import {
  analyzeForegroundAlpha,
  foregroundAlphaIssue,
  foregroundLayoutIssues,
  formatForegroundLayout,
} from "./foreground-layout.mjs";

const WIDTH = 1080;
const HEIGHT = 1440;
const METADATA_PATH = resolve("scene-metadata.json");
const ARTIFACTS_DIR = resolve("artifacts");

const fail = (message) => {
  throw new Error(message);
};

const readMetadata = () => {
  let value;
  try {
    value = JSON.parse(readFileSync(METADATA_PATH, "utf8"));
  } catch (error) {
    fail(`Cannot read scene-metadata.json: ${error.message}`);
  }
  if (
    typeof value.scene_id !== "string" ||
    typeof value.output_file !== "string" ||
    value.fps !== 30 ||
    value.width !== WIDTH ||
    value.height !== HEIGHT ||
    !["light", "dark"].includes(value.visual_theme) ||
    !Number.isInteger(value.duration_in_frames) ||
    value.duration_in_frames < 1 ||
    !Number.isInteger(value.background_width) ||
    value.background_width <= WIDTH ||
    !Number.isInteger(value.background_height) ||
    value.background_height <= HEIGHT ||
    typeof value.background_color !== "string" ||
    !value.background_anchor ||
    ![0, 1].includes(value.background_anchor.x) ||
    ![0, 1].includes(value.background_anchor.y) ||
    !value.transition_handles ||
    typeof value.transition_handles.entry !== "boolean" ||
    typeof value.transition_handles.exit !== "boolean"
  ) {
    fail("scene-metadata.json has invalid render metadata");
  }
  return value;
};

const run = (command, args, options = {}) => {
  const result = spawnSync(command, args, {
    cwd: process.cwd(),
    encoding: "utf8",
    stdio: options.capture ? "pipe" : "inherit",
  });
  if (result.error) fail(`${command}: ${result.error.message}`);
  if (result.status !== 0) {
    const detail = options.capture
      ? `${result.stdout || ""}\n${result.stderr || ""}`.trim()
      : "";
    fail(
      `${command} exited with ${result.status}${detail ? `: ${detail}` : ""}`,
    );
  }
  return result;
};

const probeVideo = (metadata) => {
  const result = run(
    "ffprobe",
    [
      "-v",
      "error",
      "-count_frames",
      "-select_streams",
      "v:0",
      "-show_entries",
      "stream=width,height,r_frame_rate,nb_frames,nb_read_frames",
      "-of",
      "json",
      resolve(metadata.output_file),
    ],
    { capture: true },
  );
  const stream = JSON.parse(result.stdout).streams?.[0];
  const frames = Number(stream?.nb_read_frames || stream?.nb_frames);
  if (
    stream?.width !== WIDTH ||
    stream?.height !== HEIGHT ||
    stream?.r_frame_rate !== "30/1" ||
    frames !== metadata.duration_in_frames
  ) {
    fail(
      `${metadata.output_file} must be ${WIDTH}x${HEIGHT}, 30fps, ${metadata.duration_in_frames} frames`,
    );
  }
};

const renderStill = (compositionId, output, frame) => {
  run(process.execPath, [
    "scripts/remotion-cli.mjs",
    "still",
    compositionId,
    output,
    `--frame=${frame}`,
    "--image-format=png",
    "--gl=swangle",
    "--overwrite",
  ]);
};

const extractAlphaPlane = (path) => {
  const result = spawnSync(
    "ffmpeg",
    [
      "-v",
      "error",
      "-i",
      path,
      "-vf",
      "alphaextract",
      "-frames:v",
      "1",
      "-pix_fmt",
      "gray",
      "-f",
      "rawvideo",
      "-",
    ],
    {
      cwd: process.cwd(),
      encoding: null,
      stdio: "pipe",
      maxBuffer: WIDTH * HEIGHT * 4,
    },
  );
  if (result.error) fail(`ffmpeg: ${result.error.message}`);
  if (result.status !== 0) {
    const detail = Buffer.concat([
      result.stdout || Buffer.alloc(0),
      result.stderr || Buffer.alloc(0),
    ])
      .toString("utf8")
      .trim();
    fail(`ffmpeg exited with ${result.status}${detail ? `: ${detail}` : ""}`);
  }
  if (result.stdout.length !== WIDTH * HEIGHT) {
    fail(
      `${path} produced ${result.stdout.length} alpha samples; expected ${WIDTH * HEIGHT}`,
    );
  }
  return result.stdout;
};

const probeForeground = (path) => {
  const probe = run(
    "ffprobe",
    [
      "-v",
      "error",
      "-select_streams",
      "v:0",
      "-show_entries",
      "stream=width,height,pix_fmt",
      "-of",
      "json",
      path,
    ],
    { capture: true },
  );
  const stream = JSON.parse(probe.stdout).streams?.[0];
  if (
    stream?.width !== WIDTH ||
    stream?.height !== HEIGHT ||
    !String(stream?.pix_fmt || "").includes("a")
  ) {
    fail(`${path} must be a ${WIDTH}x${HEIGHT} PNG with an alpha channel`);
  }

  const analysis = analyzeForegroundAlpha(
    extractAlphaPlane(path),
    WIDTH,
    HEIGHT,
  );
  const alphaIssue = foregroundAlphaIssue(analysis);
  if (alphaIssue) fail(`${path} ${alphaIssue}`);

  const layoutIssues = foregroundLayoutIssues(analysis, WIDTH, HEIGHT);
  if (layoutIssues.length > 0) {
    fail(
      `${path} has unsafe foreground layout: ${layoutIssues.join("; ")} ` +
        `(${formatForegroundLayout(analysis)}). Place the horizontal main ` +
        `layout around x=${WIDTH / 2} with visible edge inset; explicitly set ` +
        `AbsoluteFill flexDirection when using alignItems or justifyContent.`,
    );
  }
};

const renderHandle = (name, frame) => {
  const foregroundName = `transition-${name}-foreground.png`;
  const compositeName = `transition-${name}-composite.png`;
  const foregroundPath = resolve(ARTIFACTS_DIR, foregroundName);
  const compositePath = resolve(ARTIFACTS_DIR, compositeName);
  renderStill("foreground", foregroundPath, frame);
  renderStill("default", compositePath, frame);
  probeForeground(foregroundPath);
  return {
    scene_frame: frame,
    foreground: `artifacts/${foregroundName}`,
    composite: `artifacts/${compositeName}`,
  };
};

const main = () => {
  const metadata = readMetadata();
  probeVideo(metadata);
  mkdirSync(ARTIFACTS_DIR, { recursive: true });

  const handles = {};
  if (metadata.transition_handles.entry) {
    handles.entry = renderHandle("in", 0);
  }
  if (metadata.transition_handles.exit) {
    handles.exit = renderHandle("out", metadata.duration_in_frames - 1);
  }

  const manifest = {
    scene_id: metadata.scene_id,
    output_file: metadata.output_file,
    fps: metadata.fps,
    width: metadata.width,
    height: metadata.height,
    timeline_origin_seconds: metadata.timeline_origin_seconds,
    frame_range: metadata.frame_range,
    render_range_seconds: metadata.render_range_seconds,
    duration_in_frames: metadata.duration_in_frames,
    visual_theme: metadata.visual_theme,
    background: `public/${metadata.background_image}`,
    background_width: metadata.background_width,
    background_height: metadata.background_height,
    background_color: metadata.background_color,
    background_anchor: metadata.background_anchor,
    handles,
  };
  writeFileSync(
    resolve(ARTIFACTS_DIR, "scene-manifest.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
  );
  console.log(
    `[transition-handles] ${metadata.scene_id}: ${Object.keys(handles).join(", ") || "none"}`,
  );
};

try {
  main();
} catch (error) {
  console.error(
    `[transition-handles] ${error instanceof Error ? error.message : String(error)}`,
  );
  process.exit(1);
}
