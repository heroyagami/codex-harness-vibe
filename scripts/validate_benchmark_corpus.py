from __future__ import annotations

import argparse
import json
from pathlib import Path

from legal_auto_motion.benchmark_corpus import validate_corpus


parser = argparse.ArgumentParser()
parser.add_argument("root", nargs="?", default="benchmarks/corpus-v1")
args = parser.parse_args()
report = validate_corpus(Path(args.root))
print(json.dumps(report, ensure_ascii=False, indent=2))
