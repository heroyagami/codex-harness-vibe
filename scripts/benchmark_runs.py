from __future__ import annotations

import argparse
import json
from pathlib import Path

from legal_auto_motion.benchmark import write_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare completed Harness runs")
    parser.add_argument("runs", nargs="+", type=Path, help="Run directories to compare")
    parser.add_argument("--output", type=Path, default=Path("benchmark-report.json"))
    args = parser.parse_args()
    report = write_benchmark(args.runs, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
