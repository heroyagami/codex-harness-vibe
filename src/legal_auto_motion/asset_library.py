from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


class AssetLibrary:
    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.files = self.root / "files"
        self.files.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        if not self.index_path.exists():
            self.index_path.write_text("[]\n", encoding="utf-8")

    def _load(self) -> list[dict]:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save(self, records: list[dict]) -> None:
        self.index_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def add(
        self, source: Path, *, tags: list[str], license_name: str,
        source_url: str = "", attribution: str = "",
    ) -> dict:
        source = source.resolve()
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        records = self._load()
        existing = next((item for item in records if item["sha256"] == digest), None)
        if existing:
            existing["tags"] = sorted(set(existing.get("tags", [])) | {tag.strip() for tag in tags if tag.strip()})
            self._save(records)
            return existing
        asset_id = digest[:16]
        filename = f"{asset_id}{source.suffix.lower()}"
        shutil.copy2(source, self.files / filename)
        record = {
            "asset_id": asset_id,
            "filename": filename,
            "original_name": source.name,
            "sha256": digest,
            "tags": sorted({tag.strip() for tag in tags if tag.strip()}),
            "license": license_name or "unspecified",
            "source_url": source_url,
            "attribution": attribution,
        }
        records.append(record)
        self._save(records)
        return record

    def select(self, query: str, *, limit: int = 12) -> list[dict]:
        query_lower = query.lower()
        scored = []
        for record in self._load():
            score = sum(1 for tag in record.get("tags", []) if tag.lower() in query_lower)
            if score:
                scored.append((score, record))
        scored.sort(key=lambda item: (-item[0], item[1]["asset_id"]))
        return [record for _, record in scored[:limit]]

    def list_all(self, *, limit: int = 50) -> list[dict]:
        return self._load()[:limit]

    def materialize(self, records: list[dict], destination: Path) -> list[dict]:
        destination.mkdir(parents=True, exist_ok=True)
        manifest = []
        for record in records:
            source = self.files / record["filename"]
            if not source.exists():
                continue
            shutil.copy2(source, destination / record["filename"])
            manifest.append(record | {"relative_path": f"library/{record['filename']}"})
        (destination.parent / "asset-catalog.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return manifest


def asset_root(value: str, config_source: Path | None = None) -> Path:
    if value:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute() and config_source is not None:
            candidate = config_source.parent / candidate
        return candidate.resolve()
    return (Path.home() / ".codex-harness-vibe" / "assets").resolve()
