import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


TIME_LINE_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}(?:\s+.*)?$"
)


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def is_content_line(line):
    text = line.strip()
    return bool(text) and not text.isdigit() and not TIME_LINE_RE.fullmatch(text)


def extract_prefix(srt_path, length):
    if not srt_path.is_file():
        fail(f"SRT file not found: {srt_path}")
    chars = []
    for line in srt_path.read_text(encoding="utf-8-sig").splitlines():
        if not is_content_line(line):
            continue
        for char in line:
            if char.isalnum():
                chars.append(char)
                if len(chars) >= length:
                    return "".join(chars)
    fail(f"{srt_path}: no Chinese/letter/digit characters found")


def already_named(name, prefix):
    return re.fullmatch(re.escape(prefix) + r"-\d{2}-\d{2}(?:-\d+)?", name) is not None


def unique_target(parent, base_name):
    target = parent / base_name
    if not target.exists():
        return target
    for index in range(2, 1000):
        target = parent / f"{base_name}-{index}"
        if not target.exists():
            return target
    fail(f"Could not find an unused workspace name for {base_name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chars", type=int, default=5)
    args = parser.parse_args()

    if args.chars <= 0:
        fail("--chars must be greater than 0")

    root_dir = Path(__file__).resolve().parent
    prefix = extract_prefix(root_dir / "transcription.srt", args.chars)

    if already_named(root_dir.name, prefix):
        print(f"Workspace already named: {root_dir}")
        return

    timestamp = datetime.now().strftime("%H-%M")
    target = unique_target(root_dir.parent, f"{prefix}-{timestamp}")
    root_dir.rename(target)
    print(f"Renamed workspace: {target}")
    print(f"Continue in: {target}")


if __name__ == "__main__":
    main()
