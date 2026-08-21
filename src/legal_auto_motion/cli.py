from __future__ import annotations

import argparse
import json
import sys
import shutil
from pathlib import Path

from .pipeline import (
    assemble, audit_scene, build_from_director, init_run, prepare, reset_directed_outputs,
    run_scenes, run_transitions, scene_fingerprints, sync_run_inputs,
)
from .director import direct
from .sequence_review import build_sequence_review
from .config import config_for_run
from .state import StateGraph, input_hash
from .doctor import doctor as run_doctor


def main() -> None:
    parser = argparse.ArgumentParser(prog="legal-motion")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="Create an isolated production workspace")
    new.add_argument("--srt", type=Path, required=True)
    new.add_argument("--audio", type=Path, required=True)
    new.add_argument("--out", type=Path, required=True)
    new.add_argument("--config", type=Path)

    produce = sub.add_parser("produce", help="Run or resume the complete audio+SRT production workflow")
    produce.add_argument("--srt", type=Path, required=True)
    produce.add_argument("--audio", type=Path, required=True)
    produce.add_argument("--out", type=Path, required=True)
    produce.add_argument("--scene-concurrency", type=int)
    produce.add_argument("--transition-concurrency", type=int)
    produce.add_argument("--creative-revisions", type=int)
    produce.add_argument("--timeout", type=int)
    produce.add_argument("--config", type=Path)

    plan = sub.add_parser("plan-from-director", help="Convert a validated semantic director plan")
    plan.add_argument("--run", type=Path, required=True)
    plan.add_argument("--director-plan", type=Path, required=True)

    director = sub.add_parser("direct", help="Create and validate a semantic director plan from the full SRT")
    director.add_argument("--run", type=Path, required=True)
    director.add_argument("--timeout", type=int, default=900)

    prep = sub.add_parser("prepare", help="Create isolated Remotion scene and transition workers")
    prep.add_argument("--run", type=Path, required=True)

    audit = sub.add_parser("audit-scene", help="Reject unsupported visible facts before rendering")
    audit.add_argument("--scene", type=Path, required=True)

    workers = sub.add_parser("run-scenes", help="Author, fact-check and render isolated scenes")
    workers.add_argument("--run", type=Path, required=True)
    workers.add_argument("--scenes", nargs="*", default=[])
    workers.add_argument("--concurrency", type=int, default=3)
    workers.add_argument("--timeout", type=int, default=900)
    workers.add_argument("--creative-revisions", type=int, default=1)
    workers.add_argument("--skip-critic", action="store_true")

    transitions = sub.add_parser("run-transitions", help="Stage and render non-hard-cut boundaries")
    transitions.add_argument("--run", type=Path, required=True)
    transitions.add_argument("--transitions", nargs="*", default=[])
    transitions.add_argument("--concurrency", type=int, default=2)
    transitions.add_argument("--timeout", type=int, default=900)

    review = sub.add_parser("review", help="Build midpoint contact sheet and sequence readiness report")
    review.add_argument("--run", type=Path, required=True)

    assembly = sub.add_parser("assemble", help="Assemble scenes, transitions, narration and captions")
    assembly.add_argument("--run", type=Path, required=True)
    assembly.add_argument("--output", type=Path)

    sub.add_parser("doctor", help="Verify local tools and purchased-source synchronization")

    args = parser.parse_args()
    try:
        if args.command == "new":
            init_run(
                args.out.resolve(), args.srt.resolve(), args.audio.resolve(),
                args.config.resolve() if args.config else None,
            )
        elif args.command == "produce":
            run_dir = args.out.resolve()
            if not run_dir.exists():
                init_run(
                    run_dir, args.srt.resolve(), args.audio.resolve(),
                    args.config.resolve() if args.config else None,
                )
            elif args.config:
                shutil.copy2(args.config.resolve(), run_dir / "harness.toml")
            sync_run_inputs(run_dir, args.srt.resolve(), args.audio.resolve())
            config = config_for_run(run_dir)
            timeout = args.timeout or int(config.production["timeout_seconds"])
            scene_concurrency = args.scene_concurrency or int(config.production["scene_concurrency"])
            transition_concurrency = args.transition_concurrency or int(config.production["transition_concurrency"])
            creative_revisions = (
                args.creative_revisions if args.creative_revisions is not None
                else int(config.budget["max_revision_attempts"])
            )
            directed_fingerprint = input_hash(
                [run_dir / "transcription.srt"],
                [config.route("director").provider, config.route("director").model],
            )
            graph = StateGraph(run_dir / "harness-state.json")
            if (run_dir / "scene-plan.json").exists() and not graph.is_current("directed", directed_fingerprint):
                reset_directed_outputs(run_dir)
            if not (run_dir / "scene-plan.json").exists():
                direct(run_dir, timeout=timeout)
                build_from_director(run_dir, run_dir / "director-plan.json")
            state_path = run_dir / "run-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("status") != "prepared":
                prepare(run_dir)
            plan_data = json.loads((run_dir / "scene-plan.json").read_text(encoding="utf-8"))
            pending_scenes = []
            for index in range(1, len(plan_data["scenes"]) + 1):
                scene_id = f"scene-{index:03d}"
                scene_dir = run_dir / "scenes" / scene_id
                video_ready = (scene_dir / f"{scene_id}.mov").exists()
                critique_path = scene_dir / "artifacts" / "creative-critique.json"
                critique_ready = critique_path.exists() and json.loads(critique_path.read_text(encoding="utf-8")).get("verdict") == "pass"
                scene_graph = StateGraph(scene_dir / "scene-state.json")
                authored_fingerprint, critic_fingerprint = scene_fingerprints(scene_dir, config)
                fingerprints_ready = (
                    scene_graph.is_current("authored", authored_fingerprint)
                    and scene_graph.is_current("critic_passed", critic_fingerprint)
                )
                if not (video_ready and critique_ready and fingerprints_ready):
                    pending_scenes.append(scene_id)
            if pending_scenes:
                scene_results = run_scenes(
                    run_dir, pending_scenes, concurrency=scene_concurrency, timeout=timeout,
                    max_creative_revisions=max(0, creative_revisions), critic_enabled=True,
                )
                if any(item["status"] != "rendered" for item in scene_results):
                    print(json.dumps({"status": "incomplete", "stage": "scenes", "results": scene_results}, ensure_ascii=False, indent=2))
                    raise SystemExit(2)
            build_sequence_review(run_dir)
            pending_transitions = []
            for boundary, transition in enumerate(plan_data.get("transitions", []), start=1):
                if transition.get("type") == "hard_cut":
                    continue
                transition_id = f"transition-{boundary:03d}"
                output = run_dir / "transitions" / transition_id / f"{transition_id}.mov"
                if not output.exists() or output.stat().st_size == 0:
                    pending_transitions.append(transition_id)
            if pending_transitions:
                transition_results = run_transitions(
                    run_dir, pending_transitions, concurrency=transition_concurrency, timeout=timeout
                )
                if any(item["status"] != "rendered" for item in transition_results):
                    print(json.dumps({"status": "incomplete", "stage": "transitions", "results": transition_results}, ensure_ascii=False, indent=2))
                    raise SystemExit(2)
            print(json.dumps(assemble(run_dir), ensure_ascii=False, indent=2))
        elif args.command == "plan-from-director":
            build_from_director(args.run.resolve(), args.director_plan.resolve())
        elif args.command == "direct":
            result = direct(args.run.resolve(), timeout=args.timeout)
            build_from_director(args.run.resolve(), args.run.resolve() / "director-plan.json")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "prepare":
            prepare(args.run.resolve())
        elif args.command == "audit-scene":
            report = audit_scene(args.scene.resolve())
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if report["status"] != "accepted":
                raise SystemExit(2)
        elif args.command == "run-scenes":
            results = run_scenes(
                args.run.resolve(), args.scenes, concurrency=args.concurrency, timeout=args.timeout,
                max_creative_revisions=max(0, args.creative_revisions), critic_enabled=not args.skip_critic,
            )
            print(json.dumps(results, ensure_ascii=False, indent=2))
            if any(item["status"] != "rendered" for item in results):
                raise SystemExit(2)
        elif args.command == "run-transitions":
            results = run_transitions(
                args.run.resolve(), args.transitions, concurrency=args.concurrency, timeout=args.timeout
            )
            print(json.dumps(results, ensure_ascii=False, indent=2))
            if any(item["status"] == "failed" for item in results):
                raise SystemExit(2)
        elif args.command == "review":
            print(json.dumps(build_sequence_review(args.run.resolve()), ensure_ascii=False, indent=2))
        elif args.command == "assemble":
            print(json.dumps(assemble(args.run.resolve(), args.output.resolve() if args.output else None), ensure_ascii=False, indent=2))
        elif args.command == "doctor":
            report = run_doctor(Path(__file__).resolve().parents[2])
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if report["status"] != "pass":
                raise SystemExit(2)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
