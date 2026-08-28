from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path
from typing import Any

from _common import save_json, utc_now
from schema_runtime import validate_document


LAYOUT_FAMILIES = (
    "formal_two_tier",
    "modern_two_tier",
    "ceremonial_arc",
    "double_ribbon",
    "playful_children",
    "illustrated_integrated",
)
RENDER_MODES = ("vector_flat", "vector_effect", "ai_integrated")
SMALL_ENGLISH_WORDS = {"a", "an", "and", "for", "in", "of", "on", "the", "to", "with"}


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    if not normalized:
        raise ValueError("标题不能为空")
    return normalized


def detect_language(title: str) -> str:
    has_cjk = bool(re.search(r"[\u3400-\u9fff]", title))
    has_latin = bool(re.search(r"[A-Za-z]", title))
    if has_cjk and has_latin:
        return "mixed"
    if has_cjk:
        return "zh"
    if has_latin:
        return "en"
    return "other"


def semantic_lines(title: str) -> list[str]:
    normalized = normalize_title(title)
    if normalized.casefold() == "certificate of completion":
        return ["CERTIFICATE", "OF COMPLETION"]

    words = normalized.split()
    if len(words) > 1:
        if len(normalized) <= 20:
            return [normalized]
        candidates: list[tuple[int, int, list[str]]] = []
        for index in range(1, len(words)):
            left_words, right_words = words[:index], words[index:]
            left, right = " ".join(left_words), " ".join(right_words)
            penalty = abs(len(left) - len(right))
            if left_words[-1].casefold() in SMALL_ENGLISH_WORDS:
                penalty += 12
            if right_words[0].casefold() in SMALL_ENGLISH_WORDS and len(right_words) == 1:
                penalty += 12
            candidates.append((penalty, index, [left, right]))
        return min(candidates, key=lambda item: (item[0], item[1]))[2]

    single_word_limit = 18 if re.fullmatch(r"[A-Za-z0-9'’&-]+", normalized) else 10
    if len(normalized) <= single_word_limit:
        return [normalized]
    midpoint = len(normalized) // 2
    return [normalized[:midpoint], normalized[midpoint:]]


def choose_layout(title: str, style_family: str | None, requested: str | None) -> str:
    if requested:
        if requested not in LAYOUT_FAMILIES:
            raise ValueError(f"未知标题布局家族：{requested}")
        return requested
    exact_completion = normalize_title(title).casefold() == "certificate of completion"
    if exact_completion:
        if style_family in {"S05_childrens_flat_education", "S06_themed_dynamic_event"}:
            return "double_ribbon"
        if style_family in {"S01_classic_ceremonial_gold", "S07_chinese_ceremonial_award"}:
            return "ceremonial_arc"
        return "formal_two_tier"
    return {
        "S01_classic_ceremonial_gold": "formal_two_tier",
        "S02_modern_academic_geometry": "modern_two_tier",
        "S03_dark_premium_technology": "modern_two_tier",
        "S04_fresh_botanical_watercolor": "ceremonial_arc",
        "S05_childrens_flat_education": "playful_children",
        "S06_themed_dynamic_event": "illustrated_integrated",
        "S07_chinese_ceremonial_award": "formal_two_tier",
    }.get(style_family, "formal_two_tier")


def _layout_defaults(layout: str) -> tuple[str, str, str, str]:
    mapping = {
        "formal_two_tier": ("none", "formal_serif", "formal_serif", "straight"),
        "modern_two_tier": ("none", "modern_sans", "modern_sans", "straight"),
        "ceremonial_arc": ("arc", "ceremonial_display", "formal_serif", "arc_up"),
        "double_ribbon": ("double_ribbon", "ceremonial_display", "modern_sans", "ribbon"),
        "playful_children": ("none", "children_round", "children_round", "straight"),
        "illustrated_integrated": ("illustrated_base", "children_round", "modern_sans", "straight"),
    }
    return mapping[layout]


def build_plan(
    title: str,
    orientation: str,
    *,
    style_family: str | None = None,
    layout_family: str | None = None,
    render_mode: str = "vector_effect",
) -> dict[str, Any]:
    if orientation not in {"landscape", "portrait"}:
        raise ValueError("orientation 必须是 landscape 或 portrait")
    if render_mode not in RENDER_MODES:
        raise ValueError(f"未知标题渲染模式：{render_mode}")
    normalized = normalize_title(title)
    layout = choose_layout(normalized, style_family, layout_family)
    lines = semantic_lines(normalized)
    container, primary_font, secondary_font, primary_path = _layout_defaults(layout)

    line_records = []
    for index, text in enumerate(lines):
        secondary = index == 1
        size_ratio = 0.52 if secondary else 1.0
        tracking = 0.16 if secondary else (0.05 if layout != "playful_children" else 0.02)
        path = "ribbon" if layout == "double_ribbon" else (primary_path if index == 0 else "straight")
        line_records.append(
            {
                "text": text,
                "role": "secondary" if secondary else "primary",
                "size_ratio": size_ratio,
                "tracking_em": tracking,
                "baseline_offset_em": 0,
                "path": path,
            }
        )

    width = 62 if orientation == "landscape" else 66
    plan = {
        "schema_version": "1.0",
        "title": title.strip(),
        "normalized_title": normalized,
        "language": detect_language(normalized),
        "orientation": orientation,
        "layout_family": layout,
        "render_mode": render_mode,
        "center_x_percent": 50,
        "width_percent": width,
        "portrait_up_shift_px": 110 if orientation == "portrait" else 0,
        "container": {"type": container, "title_only": True},
        "lines": line_records,
        "font_roles": {"primary": primary_font, "secondary": secondary_font},
        "created_at": utc_now(),
    }
    validate_document(plan, "title_layout_plan.schema.json")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="建立证书标题语义与布局计划。")
    parser.add_argument("--title", required=True)
    parser.add_argument("--orientation", required=True, choices=["landscape", "portrait"])
    parser.add_argument("--style-family")
    parser.add_argument("--layout-family", choices=LAYOUT_FAMILIES)
    parser.add_argument("--render-mode", choices=RENDER_MODES, default="vector_effect")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    plan = build_plan(
        args.title,
        args.orientation,
        style_family=args.style_family,
        layout_family=args.layout_family,
        render_mode=args.render_mode,
    )
    save_json(args.output.expanduser().resolve(), plan)
    print(args.output.expanduser().resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}")
        raise SystemExit(1)
