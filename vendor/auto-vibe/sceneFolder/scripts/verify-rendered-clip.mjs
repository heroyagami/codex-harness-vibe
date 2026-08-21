import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const fail = (message) => {
  throw new Error(message);
};

const readSpec = () => {
  const candidates = ["transition-spec.json", "scene-metadata.json"];
  const name = candidates.find((candidate) => existsSync(resolve(candidate)));
  if (!name) fail(`Expected ${candidates.join(" or ")}`);
  try {
    return JSON.parse(readFileSync(resolve(name), "utf8"));
  } catch (error) {
    fail(`Cannot read ${name}: ${error.message}`);
  }
};

const probe = (outputFile) => {
  const result = spawnSync(
    "ffprobe",
    [
      "-v",
      "error",
      "-count_frames",
      "-show_entries",
      "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,nb_frames,nb_read_frames",
      "-of",
      "json",
      resolve(outputFile),
    ],
    { encoding: "utf8" },
  );
  if (result.error) fail(`ffprobe: ${result.error.message}`);
  if (result.status !== 0) {
    fail((result.stderr || result.stdout || "ffprobe failed").trim());
  }
  return JSON.parse(result.stdout).streams || [];
};

const main = () => {
  const spec = readSpec();
  if (
    typeof spec.output_file !== "string" ||
    spec.fps !== 30 ||
    spec.width !== 1080 ||
    spec.height !== 1440 ||
    !Number.isInteger(spec.duration_in_frames) ||
    spec.duration_in_frames < 1
  ) {
    fail(
      "Render spec must define output_file, 30fps, 1080x1440, and duration_in_frames",
    );
  }

  const streams = probe(spec.output_file);
  const videos = streams.filter((stream) => stream.codec_type === "video");
  const audios = streams.filter((stream) => stream.codec_type === "audio");
  if (videos.length !== 1 || audios.length > 0) {
    fail("Rendered clip must contain one video stream and no audio streams");
  }
  const video = videos[0];
  const frames = Number(video.nb_read_frames || video.nb_frames);
  if (
    video.codec_name !== "h264" ||
    video.pix_fmt !== "yuv420p" ||
    video.width !== spec.width ||
    video.height !== spec.height ||
    video.r_frame_rate !== `${spec.fps}/1` ||
    frames !== spec.duration_in_frames
  ) {
    fail(
      `Expected H.264 yuv420p ${spec.width}x${spec.height} at ${spec.fps}fps with ` +
        `${spec.duration_in_frames} frames; got ${JSON.stringify(video)}`,
    );
  }
  console.log(
    `[render-verify] ${spec.output_file}: ${frames} frames, ${video.width}x${video.height}, ${video.profile}`,
  );
};

try {
  main();
} catch (error) {
  console.error(
    `[render-verify] ${error instanceof Error ? error.message : String(error)}`,
  );
  process.exit(1);
}
