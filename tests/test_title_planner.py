from __future__ import annotations

import pytest

from schema_runtime import validate_document
from title_planner import build_plan, semantic_lines


def test_certificate_of_completion_has_required_semantic_break() -> None:
    assert semantic_lines("CERTIFICATE OF COMPLETION") == ["CERTIFICATE", "OF COMPLETION"]


@pytest.mark.parametrize(
    "style_family",
    [
        "S01_classic_ceremonial_gold",
        "S02_modern_academic_geometry",
        "S05_childrens_flat_education",
        "S06_themed_dynamic_event",
    ],
)
def test_completion_title_never_uses_single_line(style_family: str) -> None:
    plan = build_plan(
        "CERTIFICATE OF COMPLETION",
        "landscape",
        style_family=style_family,
    )
    assert [line["text"] for line in plan["lines"]] == ["CERTIFICATE", "OF COMPLETION"]
    assert plan["layout_family"] in {
        "formal_two_tier",
        "ceremonial_arc",
        "double_ribbon",
    }


def test_portrait_plan_has_fixed_center_and_shift() -> None:
    plan = build_plan("结业证书", "portrait", style_family="S07_chinese_ceremonial_award")
    assert plan["center_x_percent"] == 50
    assert plan["portrait_up_shift_px"] == 110
    assert 58 <= plan["width_percent"] <= 72
    validate_document(plan, "title_layout_plan.schema.json")


def test_double_ribbon_is_title_only() -> None:
    plan = build_plan(
        "CERTIFICATE OF COMPLETION",
        "landscape",
        layout_family="double_ribbon",
    )
    assert plan["container"] == {"type": "double_ribbon", "title_only": True}
    assert all(line["path"] == "ribbon" for line in plan["lines"])


def test_short_title_remains_one_line() -> None:
    assert semantic_lines("CERTIFICATE") == ["CERTIFICATE"]
