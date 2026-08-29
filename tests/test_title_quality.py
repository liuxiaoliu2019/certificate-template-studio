from __future__ import annotations

import json

import pytest

from title_planner import build_plan
from title_quality import build_quality_report, request_repair


def _files(tmp_path):
    artifact = tmp_path / "master.png"
    artifact.write_bytes(b"deterministic-title-artifact")
    plan_path = tmp_path / "title-layout.json"
    plan_path.write_text(
        json.dumps(build_plan("CERTIFICATE", "landscape"), ensure_ascii=False),
        encoding="utf-8",
    )
    return artifact, plan_path


def _scores(total: int = 100) -> dict[str, int]:
    full = {
        "font_match": 20,
        "hierarchy": 20,
        "design_quality": 20,
        "balance": 15,
        "readability": 15,
        "cross_orientation_consistency": 10,
    }
    if total < 100:
        full["design_quality"] -= 100 - total
    return full


def test_component_sum_controls_total_and_qualification(tmp_path) -> None:
    artifact, plan = _files(tmp_path)
    report = build_quality_report("landscape", artifact, plan, _scores(86))
    assert report["total"] == 86
    assert report["qualified"] is True
    assert report["repair"]["next_action"] == "submit"


def test_score_below_85_routes_one_repair(tmp_path) -> None:
    artifact, plan = _files(tmp_path)
    report = build_quality_report(
        "landscape",
        artifact,
        plan,
        _scores(82),
        issues=["tracking_or_spacing", "weak_hierarchy"],
    )
    assert report["qualified"] is False
    assert request_repair(report) == "tracking_line_spacing"


def test_hard_failure_overrides_high_score(tmp_path) -> None:
    artifact, plan = _files(tmp_path)
    report = build_quality_report(
        "landscape",
        artifact,
        plan,
        _scores(),
        hard_failures=["spelling_error"],
        issues=["spelling_error"],
    )
    assert report["total"] == 100
    assert report["qualified"] is False
    assert report["repair"]["next_action"] == "repair"


def test_second_repair_is_blocked(tmp_path) -> None:
    artifact, plan = _files(tmp_path)
    report = build_quality_report(
        "landscape",
        artifact,
        plan,
        _scores(82),
        issues=["layout_overload"],
        repair_attempts_used=1,
    )
    assert report["repair"] == {
        "attempts_used": 1,
        "max_attempts": 1,
        "allowed": False,
        "next_action": "blocked",
        "step": None,
    }
    with pytest.raises(ValueError, match="必须暂停"):
        request_repair(report)


@pytest.mark.parametrize(
    ("issue", "step"),
    [
        ("weak_hierarchy", "size_ratio"),
        ("font_mismatch", "compatible_font"),
        ("wrong_semantic_break", "semantic_two_line"),
        ("layout_overload", "layout_downgrade"),
    ],
)
def test_repair_order_is_stable(tmp_path, issue: str, step: str) -> None:
    artifact, plan = _files(tmp_path)
    report = build_quality_report(
        "landscape", artifact, plan, _scores(82), issues=[issue]
    )
    assert report["repair"]["step"] == step


def test_template_title_failure_routes_to_structure_lock_repair(tmp_path) -> None:
    artifact, plan = _files(tmp_path)
    report = build_quality_report(
        "landscape",
        artifact,
        plan,
        _scores(),
        hard_failures=["template_geometry_lost", "unwanted_gradient"],
        issues=["template_geometry_lost", "unwanted_gradient"],
    )
    assert report["qualified"] is False
    assert request_repair(report) == "template_title_lock"
