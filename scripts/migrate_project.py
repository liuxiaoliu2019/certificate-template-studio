from __future__ import annotations

import argparse
import copy
import re
import shutil
from pathlib import Path
from typing import Any

from _common import load_json, save_json, sha256_file, utc_now
from schema_runtime import validate_document


OUTPUT_CONTRACT = {
    "landscape": {"width_px": 2172, "height_px": 1536},
    "portrait": {"width_px": 1536, "height_px": 2172},
    "format": "PNG",
    "purpose": "mini_program",
    "ratio_tolerance_percent": 0.5,
}
TEXTBOOK_STAGE_MAP = {
    "style_analyzed": "awaiting_title", "characters_analyzed": "awaiting_title",
    "waiting_for_title": "awaiting_title", "title_confirmed": "planning_landscape",
    "styles_recommended": "planning_landscape", "landscape_generated": "validating_landscape",
    "landscape_selected": "awaiting_landscape_approval", "landscape_revising": "revising_landscape",
    "landscape_approved": "generating_portrait", "portrait_generated": "validating_portrait",
    "portrait_revising": "revising_portrait", "portrait_approved": "complete",
    "analyzing": "analyzing_source", "exploring_landscape": "generating_landscape",
}
TEMPLATE_STAGE_MAP = {
    "template_analyzed": "awaiting_title", "waiting_for_title": "awaiting_title",
    "title_confirmed": "regenerating_source", "source_approved": "deriving_opposite",
    "revising": "revising_source",
}


def _orientation(value: Any, *, default_status: str) -> dict[str, Any]:
    state = copy.deepcopy(value) if isinstance(value, dict) else {}
    state.setdefault("status", default_status)
    state.setdefault("concepts", [])
    state.setdefault("selected_file", None)
    state.setdefault("active_revision_id", None)
    state.setdefault("finalization_report", None)
    if state.get("selected_file") and not state.get("finalization_report"):
        state["legacy_verification"] = "legacy_unverified"
    return state


def _migrate_textbook(original: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(original)
    data["schema_version"] = "1.5"
    data["selected_mode"] = "textbook_cover"
    data.setdefault("character_identity_path", "analysis/character_identity.json")
    data.setdefault("character_reference_dir", "analysis/character_refs")
    data.setdefault("output_contract", copy.deepcopy(OUTPUT_CONTRACT))
    data["workflow"] = {"stage": TEXTBOOK_STAGE_MAP.get(data.get("workflow", {}).get("stage"), data.get("workflow", {}).get("stage", "initialized"))}
    controls = data.setdefault("controls", {})
    controls.setdefault("landscape", "controls/landscape_v3.png")
    controls.setdefault("portrait", "controls/portrait_v3.png")
    controls.setdefault("mode", "soft")
    controls.setdefault("zone_strengths", {"Z80": 80, "Z50": 50, "Z20": 20, "Z12": 12, "Z08": 8})
    data["landscape"] = _orientation(data.get("landscape"), default_status="not_started")
    data["portrait"] = _orientation(data.get("portrait"), default_status="blocked")
    master = data.setdefault("master", {})
    for key in ("landscape", "portrait", "title", "style_profile"):
        master.setdefault(key, None)
    data.setdefault("style_engine", {
        "status": "stale", "recommendation_path": None, "candidate_profiles": [],
        "selected_profile": None, "approved_profile": None, "master_profile_path": None,
        "style_lock": "unlocked",
    })
    data.setdefault("derivatives", [])
    data.setdefault("approvals", [])
    data.setdefault("revision_log_path", "revisions/revision_log.json")
    data["updated_at"] = utc_now()
    return data


def _migrate_template(original: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(original)
    data["schema_version"] = "1.3"
    data["mode"] = "template_bidirectional"
    data["selected_mode"] = "template_bidirectional"
    data.setdefault("output_contract", copy.deepcopy(OUTPUT_CONTRACT))
    data.setdefault("source_lock", {"status": "source_locked", "user_supplied": True})
    data["workflow"] = {"stage": TEMPLATE_STAGE_MAP.get(data.get("workflow", {}).get("stage"), data.get("workflow", {}).get("stage", "initialized"))}
    controls = data.setdefault("controls", {})
    controls.setdefault("landscape", "controls/landscape_v3.png")
    controls.setdefault("portrait", "controls/portrait_v3.png")
    controls.setdefault("mode", "soft")
    source = data.get("source_orientation", "landscape")
    data.setdefault("opposite_orientation", "portrait" if source == "landscape" else "landscape")
    data["landscape"] = _orientation(data.get("landscape"), default_status="ready" if source == "landscape" else "blocked")
    data["portrait"] = _orientation(data.get("portrait"), default_status="ready" if source == "portrait" else "blocked")
    master = data.setdefault("master", {})
    for key in ("landscape", "portrait", "title", "template_dna"):
        master.setdefault(key, None)
    data.setdefault("derivatives", [])
    data.setdefault("approvals", [])
    data.setdefault("revision_log_path", "revisions/revision_log.json")
    data["updated_at"] = utc_now()
    return data


def migrate(project: Path) -> dict[str, Any]:
    root = project.expanduser().resolve()
    textbook = root / "configs/project_manifest.json"
    template = root / "configs/template_project_manifest.json"
    if textbook.is_file():
        manifest_path, mode, target, schema = textbook, "textbook_cover", "1.5", "project_manifest.schema.json"
        supported, converter = {"1.0", "1.1", "1.2", "1.3", "1.4"}, _migrate_textbook
    elif template.is_file():
        manifest_path, mode, target, schema = template, "template_bidirectional", "1.3", "template_project_manifest.schema.json"
        supported, converter = {"1.0", "1.1", "1.2"}, _migrate_template
    else:
        raise FileNotFoundError("找不到可迁移的项目 manifest")
    original = load_json(manifest_path)
    source_version = str(original.get("schema_version", ""))
    if source_version == target:
        return {"status": "already_current", "target_version": target, "manifest": str(manifest_path)}
    if source_version not in supported:
        raise ValueError(f"不支持从 {source_version or 'unknown'} 迁移")
    migrated = converter(original)
    validate_document(migrated, schema)

    timestamp = re.sub(r"[^0-9]", "", utc_now())[:14]
    backup_dir = root / "migrations/backups" / f"{timestamp}-{source_version.replace('.', '_')}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_path = backup_dir / manifest_path.name
    shutil.copy2(manifest_path, backup_path)
    before_hash = sha256_file(manifest_path)
    save_json(manifest_path, migrated)
    log = {
        "schema_version": "1.0", "status": "migrated", "mode": mode,
        "source_version": source_version, "target_version": target,
        "manifest": manifest_path.relative_to(root).as_posix(),
        "backup": backup_path.relative_to(root).as_posix(),
        "before_sha256": before_hash, "after_sha256": sha256_file(manifest_path),
        "migrated_at": utc_now(),
    }
    validate_document(log, "migration_log.schema.json")
    save_json(root / "migrations/migration_log.json", log)
    return log


def main() -> int:
    parser = argparse.ArgumentParser(description="把 v1.6 及更早项目迁移到 v1.7 状态与证据格式。")
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    result = migrate(args.project)
    print(result["status"])
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}")
        raise SystemExit(1)
