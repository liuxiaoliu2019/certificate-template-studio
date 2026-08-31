from __future__ import annotations

import pytest

import json
from pathlib import Path

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


def test_template_title_lock_overrides_generic_layout_and_effect() -> None:
    root = Path(__file__).resolve().parents[1]
    dna = json.loads((root / "examples" / "TemplateBidirectional" / "template_dna.json").read_text(encoding="utf-8"))
    dna["title_system"] = {
        "geometry": "double_ribbon_arc",
        "container": "source_native",
        "line_structure": "primary_secondary",
        "font_roles": {"primary": "children_round", "secondary": "children_round"},
        "visual_treatment": {
            "render_mode": "vector_flat",
            "fill_style": "flat_solid",
            "outline_style": "solid",
            "outline_width_px": 5,
            "shadow_enabled": False,
            "primary_fill_color": "#5A2A1D",
            "secondary_fill_color": "#C9576B",
            "outline_color": "#FFF7E7",
        },
        "placement": {
            "center_x_percent": 50,
            "width_percent": 64,
            "source_title_region": {"x": 0.24, "y": 0.08, "width": 0.52, "height": 0.20},
            "primary_arc_degrees": 24,
            "secondary_arc_degrees": 10,
        },
    }
    plan = build_plan("CERTIFICATE OF COMPLETION", "landscape", template_dna=dna)
    assert plan["render_mode"] == "vector_flat"
    assert plan["container"]["type"] == "source_native"
    assert [line["path"] for line in plan["lines"]] == ["arc_up", "arc_up"]
    assert [line["arc_degrees"] for line in plan["lines"]] == [24, 10]
    assert [line["fill_color"] for line in plan["lines"]] == ["#5A2A1D", "#C9576B"]
    assert plan["template_title_lock"]["forbid_unrequested_gradient"] is True


def test_legacy_template_dna_requires_title_structure_reanalysis() -> None:
    root = Path(__file__).resolve().parents[1]
    dna = json.loads((root / "examples" / "TemplateBidirectional" / "template_dna.json").read_text(encoding="utf-8"))
    dna.pop("title_system")
    with pytest.raises(ValueError, match="缺少 title_system"):
        build_plan("CERTIFICATE", "landscape", template_dna=dna)
