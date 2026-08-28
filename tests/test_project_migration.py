from __future__ import annotations

import json

import pytest

from migrate_project import migrate


def _textbook(tmp_path, version):
    project = tmp_path / f"textbook-{version}"
    (project / "configs").mkdir(parents=True)
    data = {
        "schema_version": version, "project_id": "legacy-course", "textbook_key": "Legacy Course",
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
        "source_cover": "input/cover.png", "style_dna_path": "analysis/style_dna.json",
        "current_title": "CERTIFICATE", "workflow": {"stage": "landscape_selected"},
        "controls": {"landscape": "controls/landscape_v3.png", "portrait": "controls/portrait_v3.png", "mode": "soft", "zone_strengths": {"Z80": 80, "Z50": 50, "Z20": 20, "Z12": 12, "Z08": 8}},
        "landscape": {"status": "awaiting_approval", "concepts": [], "selected_file": "selected/legacy.png", "active_revision_id": None},
        "portrait": {"status": "blocked", "concepts": [], "selected_file": None, "active_revision_id": None},
        "master": {"landscape": "selected/legacy.png", "portrait": None, "title": "CERTIFICATE"},
        "derivatives": [], "approvals": [], "revision_log_path": "revisions/revision_log.json",
    }
    (project / "configs/project_manifest.json").write_text(json.dumps(data), encoding="utf-8")
    return project


def _template(tmp_path, version):
    project = tmp_path / f"template-{version}"
    (project / "configs").mkdir(parents=True)
    data = {
        "schema_version": version, "mode": "template_bidirectional", "project_id": "legacy-template", "display_name": "Legacy Template",
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
        "source_template": "input/template.png", "source_orientation": "landscape", "opposite_orientation": "portrait",
        "source_dimensions": {"width_px": 1600, "height_px": 1131}, "template_dna_path": "analysis/template_dna.json",
        "current_title": "CERTIFICATE", "workflow": {"stage": "source_approved"},
        "source_lock": {"status": "source_locked", "user_supplied": True},
        "controls": {"landscape": "controls/landscape_v3.png", "portrait": "controls/portrait_v3.png", "mode": "soft"},
        "landscape": {"status": "approved", "concepts": [], "selected_file": "selected/legacy.png", "active_revision_id": None},
        "portrait": {"status": "ready", "concepts": [], "selected_file": None, "active_revision_id": None},
        "master": {"landscape": "selected/legacy.png", "portrait": None, "title": "CERTIFICATE", "template_dna": "analysis/template_dna.json"},
        "derivatives": [], "approvals": [], "revision_log_path": "revisions/revision_log.json",
    }
    (project / "configs/template_project_manifest.json").write_text(json.dumps(data), encoding="utf-8")
    return project


@pytest.mark.parametrize("version", ["1.0", "1.1", "1.2", "1.3", "1.4"])
def test_all_textbook_versions_migrate_with_backup(tmp_path, version) -> None:
    project = _textbook(tmp_path, version)
    log = migrate(project)
    data = json.loads((project / "configs/project_manifest.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.5"
    assert data["landscape"]["legacy_verification"] == "legacy_unverified"
    assert (project / log["backup"]).is_file()


@pytest.mark.parametrize("version", ["1.0", "1.1", "1.2"])
def test_all_template_versions_migrate(tmp_path, version) -> None:
    project = _template(tmp_path, version)
    migrate(project)
    data = json.loads((project / "configs/template_project_manifest.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.3"
    assert data["workflow"]["stage"] == "deriving_opposite"


def test_failure_does_not_modify_manifest(tmp_path) -> None:
    project = _textbook(tmp_path, "0.1")
    path = project / "configs/project_manifest.json"
    before = path.read_bytes()
    with pytest.raises(ValueError, match="不支持"):
        migrate(project)
    assert path.read_bytes() == before


def test_migration_is_idempotent(tmp_path) -> None:
    project = _textbook(tmp_path, "1.4")
    migrate(project)
    before = (project / "configs/project_manifest.json").read_bytes()
    result = migrate(project)
    assert result["status"] == "already_current"
    assert (project / "configs/project_manifest.json").read_bytes() == before
