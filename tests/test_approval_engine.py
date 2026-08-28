from __future__ import annotations

from pathlib import Path

import pytest

from approval_engine import approval_words_valid, validate_finalization_report
from fixtures import init_textbook, make_image, read_json, run_script, write_json


@pytest.mark.parametrize(
    ("orientation", "words"),
    [
        ("landscape", "确认横版定稿"),
        ("landscape", "确认方案 2 为横版定稿"),
        ("portrait", "确认竖版定稿"),
    ],
)
def test_explicit_positive_approval_is_valid(orientation: str, words: str) -> None:
    assert approval_words_valid(orientation, words)


@pytest.mark.parametrize(
    "words",
    [
        "不要确认横版定稿",
        "横版还不能定稿",
        "暂不确认横版定稿",
        "确认横版定稿吗？",
        "第一个可以",
        "继续",
    ],
)
def test_ambiguous_or_negative_approval_is_invalid(words: str) -> None:
    assert not approval_words_valid("landscape", words)


def test_report_title_mismatch_is_rejected(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    manifest = read_json(project / "configs/project_manifest.json")
    manifest["current_title"] = "RIGHT TITLE"
    source = make_image(tmp_path / "source.png", (1492, 1054))
    result = run_script(
        "finalize_certificate.py",
        "--input",
        source,
        "--output",
        project / "selected/master.png",
        "--report",
        project / "selected/master.finalization.json",
        "--project-root",
        project,
        "--orientation",
        "landscape",
        "--title",
        "WRONG TITLE",
        "--title-mode",
        "vector_flat",
        "--font",
        "C:/Windows/Fonts/arial.ttf",
        "--base-text-free",
    )
    assert result.returncode == 0, result.stderr
    with pytest.raises(ValueError, match="标题与项目当前标题不一致"):
        validate_finalization_report(
            project,
            "selected/master.finalization.json",
            "selected/master.png",
            "landscape",
            manifest,
        )


def test_report_mode_must_match_style_profile(tmp_path: Path) -> None:
    project = init_textbook(tmp_path)
    manifest = read_json(project / "configs/project_manifest.json")
    manifest["current_title"] = "CERTIFICATE"
    source = make_image(tmp_path / "source.png", (1492, 1054))
    result = run_script(
        "finalize_certificate.py",
        "--input",
        source,
        "--output",
        project / "selected/master.png",
        "--report",
        project / "selected/master.finalization.json",
        "--project-root",
        project,
        "--orientation",
        "landscape",
        "--title",
        "CERTIFICATE",
        "--title-mode",
        "vector_effect",
        "--font",
        "C:/Windows/Fonts/arial.ttf",
        "--base-text-free",
    )
    assert result.returncode == 0, result.stderr
    with pytest.raises(ValueError, match="标题模式与 Style Profile 不一致"):
        validate_finalization_report(
            project,
            "selected/master.finalization.json",
            "selected/master.png",
            "landscape",
            manifest,
            style_profile={"title_treatment": {"render_mode": "vector_flat"}},
        )
