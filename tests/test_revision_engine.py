from __future__ import annotations

from pathlib import Path

import pytest

from fixtures import make_image, sha256
from revision_engine import invalidate_for_revision, verify_rollback_target


def textbook_manifest() -> dict:
    return {
        "selected_mode": "textbook_cover",
        "landscape": {
            "status": "approved",
            "selected_file": "selected/landscape.png",
            "finalization_report": "selected/landscape.json",
        },
        "portrait": {
            "status": "approved",
            "selected_file": "portrait/portrait.png",
            "finalization_report": "portrait/portrait.json",
        },
        "master": {
            "landscape": "selected/landscape.png",
            "portrait": "portrait/portrait.png",
            "title": "CERTIFICATE",
            "style_profile": "styles/approved.json",
        },
        "style_engine": {
            "approved_profile": "styles/approved.json",
            "status": "approved",
            "style_lock": "profile_locked",
        },
        "approvals": [
            {"orientation": "landscape", "historical": False},
            {"orientation": "portrait", "historical": False},
        ],
    }


def test_landscape_revision_invalidates_both_orientations() -> None:
    manifest = textbook_manifest()
    invalidate_for_revision(manifest, "landscape")
    assert manifest["master"]["landscape"] is None
    assert manifest["master"]["portrait"] is None
    assert manifest["landscape"]["finalization_report"] is None
    assert manifest["portrait"]["finalization_report"] is None
    assert all(item["historical"] for item in manifest["approvals"])


def test_portrait_revision_keeps_landscape_master() -> None:
    manifest = textbook_manifest()
    invalidate_for_revision(manifest, "portrait")
    assert manifest["master"]["landscape"] == "selected/landscape.png"
    assert manifest["master"]["portrait"] is None
    assert manifest["landscape"]["finalization_report"] == "selected/landscape.json"
    assert manifest["portrait"]["finalization_report"] is None


def test_rollback_target_requires_matching_hash(tmp_path: Path) -> None:
    project = tmp_path / "project"
    artifact = make_image(project / "revisions/r001.png", (100, 100))
    entry = {"artifact": "revisions/r001.png", "sha256": sha256(artifact)}
    assert verify_rollback_target(project, entry) == artifact.resolve()
    artifact.write_bytes(b"changed")
    with pytest.raises(ValueError, match="哈希"):
        verify_rollback_target(project, entry)


def test_rollback_target_requires_existing_file(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(FileNotFoundError):
        verify_rollback_target(
            project, {"artifact": "revisions/missing.png", "sha256": "0" * 64}
        )
