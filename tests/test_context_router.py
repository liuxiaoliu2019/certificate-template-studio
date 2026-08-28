from __future__ import annotations

import pytest

from context_router import STAGE_BUDGETS, build_active_context


def test_each_stage_accepts_only_its_resources() -> None:
    context = build_active_context(
        "analysis",
        "textbook_cover",
        [
            {"kind": "prompt", "path": "skill/prompts/analyze-cover.md", "text_chars": 1200},
            {"kind": "image", "path": "input/cover.png"},
        ],
    )
    assert context["text_chars_used"] == 1200
    with pytest.raises(ValueError, match="禁止加载"):
        build_active_context(
            "analysis",
            "textbook_cover",
            [{"kind": "image", "path": "selected/master_landscape.png"}],
        )


def test_modes_do_not_cross_load_analysis() -> None:
    with pytest.raises(ValueError, match="模板双向模式"):
        build_active_context(
            "planning",
            "template_bidirectional",
            [{"kind": "json", "path": "analysis/style_dna.json"}],
        )
    with pytest.raises(ValueError, match="教材封面模式"):
        build_active_context(
            "planning",
            "textbook_cover",
            [{"kind": "json", "path": "analysis/template_dna.json"}],
        )


def test_unused_character_crop_is_rejected() -> None:
    with pytest.raises(ValueError, match="未实际使用"):
        build_active_context(
            "revision",
            "textbook_cover",
            [
                {
                    "kind": "image",
                    "path": "analysis/character_refs/hero.png",
                    "character_id": "hero",
                }
            ],
            used_character_ids=set(),
        )


def test_used_character_crop_is_allowed() -> None:
    context = build_active_context(
        "revision",
        "textbook_cover",
        [
            {
                "kind": "image",
                "path": "analysis/character_refs/hero.png",
                "character_id": "hero",
            }
        ],
        used_character_ids={"hero"},
    )
    assert context["resources"][0]["character_id"] == "hero"


def test_text_budget_is_enforced() -> None:
    with pytest.raises(ValueError, match="超过预算"):
        build_active_context(
            "approval",
            "textbook_cover",
            [
                {
                    "kind": "reference",
                    "path": "skill/references/output-and-title-rendering.md",
                    "text_chars": STAGE_BUDGETS["approval"] + 1,
                }
            ],
        )
