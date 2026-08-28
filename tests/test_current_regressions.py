from __future__ import annotations

from pathlib import Path

import pytest

from fixtures import init_textbook, make_image, read_json, run_script, sha256, write_json
from record_revision import invalidate_if_needed
from update_manifest import approval_words_valid, checked_finalization_report


def test_whitespace_only_title_is_rejected(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    result = run_script(
        "update_manifest.py", project, "--set", 'current_title=" "'
    )
    assert result.returncode != 0


@pytest.mark.xfail(strict=True, reason="CTS-102: negated approval contains the keyword")
def test_negated_approval_is_rejected() -> None:
    assert approval_words_valid("landscape", "不要确认横版定稿") is False


@pytest.mark.xfail(strict=True, reason="CTS-103: report title is not bound to manifest title")
def test_report_title_must_match_manifest(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    manifest_path = project / "configs/project_manifest.json"
    manifest = read_json(manifest_path)
    manifest["current_title"] = "RIGHT TITLE"
    write_json(manifest_path, manifest)

    artifact = make_image(project / "selected/master.png", (2172, 1536))
    report = {
        "status": "passed",
        "orientation": "landscape",
        "title_render_mode": "vector_flat",
        "output": {
            "path": "selected/master.png",
            "width_px": 2172,
            "height_px": 1536,
            "format": "PNG",
            "sha256": sha256(artifact),
        },
        "title": {"value": "WRONG TITLE"},
    }
    write_json(project / "selected/master.finalization.json", report)

    with pytest.raises(ValueError):
        checked_finalization_report(
            project,
            "selected/master.finalization.json",
            "selected/master.png",
            "landscape",
        )


def test_landscape_generation_cannot_skip_analysis_and_title(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    result = run_script(
        "update_manifest.py", project, "--stage", "landscape_generated"
    )
    assert result.returncode != 0


@pytest.mark.xfail(strict=True, reason="CTS-105: revision leaves stale finalization report")
def test_landscape_revision_clears_stale_report() -> None:
    manifest = {
        "landscape": {
            "status": "approved",
            "finalization_report": "selected/old.finalization.json",
        },
        "portrait": {
            "status": "approved",
            "finalization_report": "portrait/old.finalization.json",
        },
        "master": {"landscape": "selected/old.png", "portrait": "portrait/old.png"},
    }
    invalidate_if_needed(manifest)
    assert manifest["landscape"]["finalization_report"] is None
    assert manifest["portrait"]["finalization_report"] is None


@pytest.mark.xfail(strict=True, reason="CTS-106: rollback does not check file existence or hash")
def test_rollback_rejects_missing_revision_artifact(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    log_path = project / "revisions/revision_log.json"
    log = read_json(log_path)
    log["sequence"] = 1
    log["entries"].append(
        {
            "revision_id": "r001",
            "orientation": "landscape",
            "action": "revision",
            "level": 1,
            "source": None,
            "artifact": "revisions/missing.png",
            "sha256": "0" * 64,
            "feedback": ["test"],
            "rollback_to": None,
            "created_at": "2026-08-28T00:00:00Z",
            "style_family": None,
            "style_profile": None,
            "changed_parameters": [],
            "locked_parameters": [],
            "approval_state_before": "not_started",
            "approval_state_after": "revising",
        }
    )
    write_json(log_path, log)

    result = run_script(
        "record_revision.py",
        project,
        "--orientation",
        "landscape",
        "--rollback",
        "r001",
        "--feedback",
        "rollback",
    )
    assert result.returncode != 0
