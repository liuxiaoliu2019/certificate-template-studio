from __future__ import annotations

from pathlib import Path
from typing import Any

from project_io import resolve_project_path, sha256_file


def _mark_historical(manifest: dict[str, Any], orientations: set[str]) -> None:
    for approval in manifest.get("approvals", []):
        if approval.get("orientation") in orientations:
            approval["historical"] = True


def _clear_orientation(manifest: dict[str, Any], orientation: str, status: str) -> None:
    state = manifest[orientation]
    state["status"] = status
    if "finalization_report" in state:
        state["finalization_report"] = None
    manifest["master"][orientation] = None


def invalidate_for_revision(
    manifest: dict[str, Any], orientation: str, *, mode: str | None = None
) -> None:
    selected_mode = mode or manifest.get("selected_mode") or manifest.get("mode") or "textbook_cover"
    if orientation not in {"landscape", "portrait"}:
        raise ValueError(f"未知方向：{orientation}")

    if selected_mode == "template_bidirectional":
        source = manifest["source_orientation"]
        opposite = manifest["opposite_orientation"]
        if orientation == source:
            _clear_orientation(manifest, source, "revising")
            opposite_status = "stale" if manifest[opposite].get("selected_file") else "blocked"
            _clear_orientation(manifest, opposite, opposite_status)
            _mark_historical(manifest, {source, opposite})
        else:
            _clear_orientation(manifest, opposite, "revising")
            _mark_historical(manifest, {opposite})
        manifest["master"]["title"] = None
        return

    if orientation == "landscape":
        _clear_orientation(manifest, "landscape", "revising")
        portrait_status = "stale" if manifest["portrait"].get("selected_file") else "blocked"
        _clear_orientation(manifest, "portrait", portrait_status)
        _mark_historical(manifest, {"landscape", "portrait"})
        manifest["master"]["title"] = None
        if "style_profile" in manifest["master"]:
            manifest["master"]["style_profile"] = None
        style_state = manifest.get("style_engine")
        if style_state:
            style_state["approved_profile"] = None
            style_state["status"] = "stale"
            style_state["style_lock"] = "family_locked"
    else:
        _clear_orientation(manifest, "portrait", "revising")
        _mark_historical(manifest, {"portrait"})


def verify_rollback_target(project: Path, entry: dict[str, Any]) -> Path:
    relative = entry.get("artifact")
    expected_hash = entry.get("sha256")
    if not isinstance(relative, str) or not relative:
        raise ValueError("回退 revision 缺少成品路径")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError("回退 revision 缺少有效成品哈希")
    path = resolve_project_path(project, relative, must_exist=True)
    if not path.is_file():
        raise FileNotFoundError(f"回退成品不存在：{relative}")
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise ValueError("回退成品哈希与 revision 记录不一致")
    return path
