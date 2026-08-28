from __future__ import annotations

from pathlib import Path

import pytest

from fixtures import init_textbook, read_json, write_json
from workflow_engine import transition


def test_textbook_cannot_skip_from_initialized(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    manifest = read_json(project / "configs/project_manifest.json")
    with pytest.raises(ValueError, match="不允许"):
        transition(manifest, "generating_landscape", project=project)


def test_textbook_requires_analysis_files_before_awaiting_title(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    manifest = read_json(project / "configs/project_manifest.json")
    transition(manifest, "analyzing_source", project=project)
    with pytest.raises(FileNotFoundError, match="style_dna.json"):
        transition(manifest, "awaiting_title", project=project)


def test_textbook_happy_path_reaches_planning(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    manifest = read_json(project / "configs/project_manifest.json")
    transition(manifest, "analyzing_source", project=project)
    write_json(project / manifest["style_dna_path"], {"fixture": True})
    write_json(project / manifest["character_identity_path"], {"fixture": True})
    transition(manifest, "awaiting_title", project=project)
    manifest["current_title"] = "CERTIFICATE"
    transition(manifest, "planning_landscape", project=project)
    assert manifest["workflow"]["stage"] == "planning_landscape"


def test_portrait_generation_requires_approved_landscape(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    manifest = read_json(project / "configs/project_manifest.json")
    manifest["workflow"]["stage"] = "awaiting_landscape_approval"
    manifest["current_title"] = "CERTIFICATE"
    write_json(project / manifest["style_dna_path"], {"fixture": True})
    write_json(project / manifest["character_identity_path"], {"fixture": True})
    with pytest.raises(ValueError, match="横版未批准"):
        transition(manifest, "generating_portrait", project=project)
