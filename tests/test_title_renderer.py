from __future__ import annotations

import hashlib

import pytest
from PIL import Image

from title_planner import build_plan
from title_renderer import render_title_plan


@pytest.mark.parametrize(
    ("layout", "title"),
    [
        ("formal_two_tier", "CERTIFICATE OF COMPLETION"),
        ("modern_two_tier", "ACADEMIC ACHIEVEMENT"),
        ("ceremonial_arc", "CERTIFICATE OF COMPLETION"),
        ("double_ribbon", "CERTIFICATE OF COMPLETION"),
        ("playful_children", "LEARNING STAR"),
        ("illustrated_integrated", "CREATIVE EXPLORER"),
    ],
)
def test_all_layout_families_render_and_center(layout: str, title: str) -> None:
    base = Image.new("RGBA", (2172, 1536), "white")
    plan = build_plan(title, "landscape", layout_family=layout)
    result = render_title_plan(base, plan)
    assert result.image.size == base.size
    assert result.center_error_px <= 1
    assert result.bbox[0] < result.bbox[2]
    assert result.bbox[1] < result.bbox[3]
    assert result.font_evidence


def test_portrait_uses_planned_up_shift() -> None:
    base = Image.new("RGBA", (1536, 2172), "white")
    portrait = build_plan("结业证书", "portrait", layout_family="formal_two_tier")
    landscape_shift = dict(portrait)
    landscape_shift["portrait_up_shift_px"] = 0
    shifted = render_title_plan(base, portrait)
    unshifted = render_title_plan(base, landscape_shift)
    shifted_center = (shifted.bbox[1] + shifted.bbox[3]) / 2
    unshifted_center = (unshifted.bbox[1] + unshifted.bbox[3]) / 2
    assert unshifted_center - shifted_center == pytest.approx(110, abs=2)


def test_vector_flat_keeps_pure_color_pixels() -> None:
    base = Image.new("RGBA", (2172, 1536), "white")
    plan = build_plan("CERTIFICATE", "landscape", render_mode="vector_flat")
    result = render_title_plan(base, plan, colors=[(31, 78, 121, 255)])
    pure = sum(1 for pixel in result.image.getdata() if pixel == (31, 78, 121, 255))
    assert pure > 100


def test_effect_render_is_deterministic() -> None:
    base = Image.new("RGBA", (2172, 1536), "white")
    plan = build_plan("CERTIFICATE OF COMPLETION", "landscape", layout_family="double_ribbon")
    first = render_title_plan(base, plan).image.tobytes()
    second = render_title_plan(base, plan).image.tobytes()
    assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()


def test_double_ribbon_contains_only_planned_title_lines() -> None:
    plan = build_plan("CERTIFICATE OF COMPLETION", "landscape", layout_family="double_ribbon")
    assert [line["text"] for line in plan["lines"]] == ["CERTIFICATE", "OF COMPLETION"]
    assert plan["container"]["title_only"] is True
