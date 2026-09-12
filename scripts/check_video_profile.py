from __future__ import annotations

import argparse
import json
from pathlib import Path

from legal_auto_motion.runtime_readiness import repo_runtime_readiness
from legal_auto_motion.video_profile import CURRENT_RENDERER_PROFILE, VERTICAL_9_16_TARGET


parser = argparse.ArgumentParser()
parser.add_argument("--profile", choices=["current", "vertical_9_16"], default="vertical_9_16")
args = parser.parse_args()
profile = CURRENT_RENDERER_PROFILE if args.profile == "current" else VERTICAL_9_16_TARGET
root = Path(__file__).resolve().parents[1]
print(json.dumps(repo_runtime_readiness(root, profile), ensure_ascii=False, indent=2))
