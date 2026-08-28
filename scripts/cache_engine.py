from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from _common import load_json, save_json, sha256_file, utc_now
from project_io import resolve_project_path
from schema_runtime import validate_document


STAGE_ORDER = (
    "analysis",
    "profiles",
    "landscape_candidates",
    "master_landscape",
    "master_portrait",
    "title_plan",
    "title_render",
    "reports",
    "derivatives",
)


def file_record(project: Path, relative: str) -> dict[str, str]:
    path = resolve_project_path(project, relative, must_exist=True)
    return {"path": Path(relative).as_posix(), "sha256": sha256_file(path)}


def build_source_fingerprint(
    project: Path,
    *,
    mode: str,
    source: str,
    landscape_control: str = "controls/landscape_v3.png",
    portrait_control: str = "controls/portrait_v3.png",
    characters: dict[str, str] | None = None,
) -> dict[str, Any]:
    root = project.expanduser().resolve()
    fingerprint = {
        "schema_version": "1.0",
        "mode": mode,
        "source": file_record(root, source),
        "controls": {
            "landscape": file_record(root, landscape_control),
            "portrait": file_record(root, portrait_control),
        },
        "characters": {
            character_id: file_record(root, relative)
            for character_id, relative in sorted((characters or {}).items())
        },
        "updated_at": utc_now(),
    }
    validate_document(fingerprint, "source_fingerprint.schema.json")
    return fingerprint


def canonical_input_hash(inputs: dict[str, Any]) -> str:
    payload = json.dumps(inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CacheEngine:
    def __init__(self, project: Path):
        self.project = project.expanduser().resolve()
        self.path = self.project / "configs" / "cache_state.json"
        if self.path.is_file():
            self.state = load_json(self.path)
        else:
            self.state = {"schema_version": "1.0", "entries": {}}

    def lookup(self, stage: str, inputs: dict[str, Any]) -> dict[str, Any] | None:
        entry = self.state["entries"].get(stage)
        if not entry or entry["input_hash"] != canonical_input_hash(inputs):
            return None
        for artifact in entry["artifacts"]:
            path = resolve_project_path(self.project, artifact["path"])
            if not path.is_file() or sha256_file(path) != artifact["sha256"]:
                return None
        return entry

    def record(self, stage: str, inputs: dict[str, Any], artifacts: list[str]) -> dict[str, Any]:
        if stage not in STAGE_ORDER:
            raise ValueError(f"未知缓存阶段：{stage}")
        records = [file_record(self.project, relative) for relative in artifacts]
        entry = {
            "input_hash": canonical_input_hash(inputs),
            "artifacts": records,
            "created_at": utc_now(),
        }
        self.state["entries"][stage] = entry
        self.save()
        return entry

    def invalidate(self, stages: set[str]) -> list[str]:
        removed = []
        for stage in STAGE_ORDER:
            if stage in stages and self.state["entries"].pop(stage, None) is not None:
                removed.append(stage)
        self.save()
        return removed

    def invalidate_change(
        self,
        change: str,
        *,
        orientation: str | None = None,
        character_id: str | None = None,
        character_usage: dict[str, list[str]] | None = None,
    ) -> list[str]:
        if change == "title":
            stages = {"title_plan", "title_render", "reports", "derivatives"}
        elif change == "source":
            stages = set(STAGE_ORDER)
        elif change == "control":
            if orientation == "landscape":
                stages = {
                    "landscape_candidates", "master_landscape", "master_portrait",
                    "title_render", "reports", "derivatives",
                }
            elif orientation == "portrait":
                stages = {"master_portrait", "title_render", "reports", "derivatives"}
            else:
                raise ValueError("控制图变化必须指定 orientation")
        elif change == "character":
            if not character_id:
                raise ValueError("角色变化必须指定 character_id")
            used_by = set((character_usage or {}).get(character_id, []))
            if not used_by:
                return []
            stages = {"landscape_candidates", "master_landscape", "master_portrait", "reports", "derivatives"}
        else:
            raise ValueError(f"未知缓存变化类型：{change}")
        return self.invalidate(stages)

    def save(self) -> None:
        save_json(self.path, self.state)
