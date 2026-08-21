import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scene_plan import (
    ScenePlanError,
    parse_subtitle_cues,
    read_scene_plan_document,
)


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def run(command):
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        fail(f"Command failed ({result.returncode}): {' '.join(command)}\n{detail}")
    return result.stdout


def probe_clip(path, expected_frames):
    if not path.is_file():
        fail(f"Timeline clip not found: {path}")
    output = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,nb_frames,nb_read_frames",
            "-of",
            "json",
            str(path),
        ]
    )
    streams = json.loads(output).get("streams", [])
    video_streams = [item for item in streams if item.get("codec_type") == "video"]
    audio_streams = [item for item in streams if item.get("codec_type") == "audio"]
    if len(video_streams) != 1 or audio_streams:
        fail(f"{path}: expected one video stream and no audio streams")
    stream = video_streams[0]
    frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    if frames != expected_frames:
        fail(f"{path}: expected {expected_frames} frames, got {frames}")
    if (
        stream.get("codec_name") != "h264"
        or stream.get("width") != 1080
        or stream.get("height") != 1440
        or stream.get("r_frame_rate") != "30/1"
        or stream.get("pix_fmt") != "yuv420p"
    ):
        fail(
            f"{path}: expected H.264, yuv420p, 1080x1440 at 30fps; "
            f"got {stream}"
        )
    signature = {
        key: stream.get(key)
        for key in (
            "codec_name",
            "profile",
            "width",
            "height",
            "pix_fmt",
            "r_frame_rate",
        )
    }
    return signature, frames


def extract_output_prefix(srt_path, length=5):
    cues = parse_subtitle_cues(
        srt_path.read_text(encoding="utf-8-sig"), str(srt_path)
    )
    chars = []
    for cue in cues:
        for char in cue["text"]:
            if char.isalnum():
                chars.append(char)
                if len(chars) == length:
                    return "".join(chars)
    if chars:
        return "".join(chars)
    fail(f"{srt_path}: no Chinese/letter/digit characters found")


def quote_ffconcat_path(path):
    return str(path).replace("'", "'\\''")


def resolve_segment_path(root_dir, segment):
    if segment["kind"] == "scene":
        return root_dir / "scenes" / segment["id"] / segment["output_file"]
    return root_dir / "transitions" / segment["id"] / segment["output_file"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scene_plan_path")
    parser.add_argument("--output")
    args = parser.parse_args()

    plan_path = Path(args.scene_plan_path).resolve()
    root_dir = plan_path.parent
    try:
        document = read_scene_plan_document(plan_path)
    except ScenePlanError as exc:
        fail(str(exc))

    output_path = (
        Path(args.output).resolve()
        if args.output
        else root_dir / f"{extract_output_prefix(root_dir / 'transcription.srt')}.mov"
    )
    clips = []
    baseline_signature = None
    planned_frame_sum = 0
    for segment in document["timeline_segments"]:
        clip_path = resolve_segment_path(root_dir, segment).resolve()
        signature, frames = probe_clip(clip_path, segment["duration_in_frames"])
        if baseline_signature is None:
            baseline_signature = signature
        elif signature != baseline_signature:
            fail(
                f"{clip_path}: technical specification differs from the first timeline clip"
            )
        clips.append(clip_path)
        planned_frame_sum += frames

    if planned_frame_sum != document["total_duration_frames"]:
        fail(
            f"Timeline clips contain {planned_frame_sum} frames, expected "
            f"{document['total_duration_frames']}"
        )
    if output_path in clips:
        fail(f"Output path must differ from timeline clip paths: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    concat_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".ffconcat",
            prefix="timeline-",
            dir=root_dir,
            delete=False,
        ) as file:
            concat_path = Path(file.name)
            file.write("ffconcat version 1.0\n")
            for clip in clips:
                file.write(f"file '{quote_ffconcat_path(clip)}'\n")
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-map",
                "0:v:0",
                "-an",
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
    finally:
        if concat_path is not None:
            concat_path.unlink(missing_ok=True)

    final_signature, final_frames = probe_clip(
        output_path, document["total_duration_frames"]
    )
    if final_signature != baseline_signature:
        fail(f"{output_path}: final technical specification changed during concat")
    print(
        f"Assembled {output_path.name}: {final_frames} frames at 30fps "
        f"({final_frames / 30:.3f}s)"
    )


if __name__ == "__main__":
    main()
