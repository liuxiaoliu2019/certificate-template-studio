from __future__ import annotations

from pathlib import Path

import pytest

from project_io import atomic_write_json, load_json, resolve_project_path


def test_project_path_rejects_parent_escape(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(ValueError, match="必须位于项目目录内"):
        resolve_project_path(project, "../outside.json")


def test_project_path_rejects_absolute_path(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(ValueError, match="必须使用相对路径"):
        resolve_project_path(project, tmp_path / "outside.json")


def test_atomic_json_keeps_old_file_when_validation_fails(tmp_path: Path) -> None:
    target = tmp_path / "value.json"
    atomic_write_json(target, {"value": 1})

    def reject(_: object) -> None:
        raise ValueError("rejected")

    with pytest.raises(ValueError, match="rejected"):
        atomic_write_json(target, {"value": 2}, reject)
    assert load_json(target) == {"value": 1}


def test_atomic_json_validates_before_and_after_write(tmp_path: Path) -> None:
    target = tmp_path / "value.json"
    calls: list[int] = []

    def validate(value: dict) -> None:
        calls.append(value["value"])

    atomic_write_json(target, {"value": 3}, validate)
    assert calls == [3, 3]
    assert load_json(target) == {"value": 3}
