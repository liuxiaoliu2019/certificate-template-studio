from __future__ import annotations

import json

from PIL import Image

from derive_title import derive_title
from project_io import sha256_file


def _project(tmp_path):
    project = tmp_path / "project"
    for directory in ("configs", "selected", "bases", "derivatives", "logs"):
        (project / directory).mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (2172, 1536), "white").save(project / "bases/landscape.png")
    Image.new("RGB", (1536, 2172), "white").save(project / "bases/portrait.png")
    Image.new("RGB", (2172, 1536), "white").save(project / "selected/master_landscape.png")
    Image.new("RGB", (1536, 2172), "white").save(project / "selected/master_portrait.png")
    manifest = {
        "landscape": {"status": "approved"}, "portrait": {"status": "approved"},
        "master": {"landscape": "selected/master_landscape.png", "portrait": "selected/master_portrait.png", "title": "OLD"},
        "derivatives": [],
    }
    (project / "configs/project_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return project


def test_dual_master_derivative_keeps_original_master_and_manifest_fields(tmp_path) -> None:
    project = _project(tmp_path)
    master_hashes = {
        name: sha256_file(project / f"selected/master_{name}.png")
        for name in ("landscape", "portrait")
    }
    result = derive_title(project, "NEW CERTIFICATE", "bases/landscape.png", "bases/portrait.png", title_mode="vector_flat", layout_family="modern_two_tier")
    for orientation, expected in (("landscape", (2172, 1536)), ("portrait", (1536, 2172))):
        with Image.open(project / result["outputs"][orientation]["image"]["path"]) as image:
            assert image.size == expected
        assert sha256_file(project / f"selected/master_{orientation}.png") == master_hashes[orientation]
    manifest = json.loads((project / "configs/project_manifest.json").read_text(encoding="utf-8"))
    assert manifest["master"]["title"] == "OLD"
    assert len(manifest["derivatives"]) == 1


def test_repeated_title_never_overwrites_previous_derivative(tmp_path) -> None:
    project = _project(tmp_path)
    first = derive_title(project, "CERTIFICATE", "bases/landscape.png", "bases/portrait.png", title_mode="vector_flat")
    second = derive_title(project, "CERTIFICATE", "bases/landscape.png", "bases/portrait.png", title_mode="vector_flat")
    assert first["slug"] != second["slug"]
    assert (project / "derivatives" / first["slug"]).is_dir()
    assert (project / "derivatives" / second["slug"]).is_dir()
