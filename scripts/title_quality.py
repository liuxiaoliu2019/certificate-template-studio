from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from _common import load_json, save_json, sha256_file, utc_now
from schema_runtime import validate_document
from metrics import MetricsRecorder


SCORE_LIMITS = {
    "font_match": 20,
    "hierarchy": 20,
    "design_quality": 20,
    "balance": 15,
    "readability": 15,
    "cross_orientation_consistency": 10,
}
HARD_FAILURES = {
    "spelling_error",
    "missing_glyph",
    "wrong_semantic_break",
    "center_offset",
    "low_contrast",
    "container_collision",
    "flat_noise",
    "extra_text",
}
ISSUES = {
    "tracking_or_spacing",
    "weak_hierarchy",
    "font_mismatch",
    "missing_glyph",
    "wrong_semantic_break",
    "layout_overload",
    "low_contrast",
    "container_collision",
    "flat_noise",
    "spelling_error",
    "extra_text",
    "center_offset",
}
REPAIR_PRIORITY = (
    ({"tracking_or_spacing", "low_contrast", "center_offset"}, "tracking_line_spacing"),
    ({"weak_hierarchy"}, "size_ratio"),
    ({"font_mismatch", "missing_glyph"}, "compatible_font"),
    ({"wrong_semantic_break"}, "semantic_two_line"),
)


def choose_repair_step(issues: list[str]) -> str:
    issue_set = set(issues)
    for candidates, step in REPAIR_PRIORITY:
        if issue_set & candidates:
            return step
    return "layout_downgrade"


def build_quality_report(
    orientation: str,
    artifact_path: Path,
    layout_plan_path: Path,
    scores: dict[str, int],
    *,
    hard_failures: list[str] | None = None,
    issues: list[str] | None = None,
    repair_attempts_used: int = 0,
) -> dict[str, Any]:
    if orientation not in {"landscape", "portrait"}:
        raise ValueError("orientation 必须是 landscape 或 portrait")
    if set(scores) != set(SCORE_LIMITS):
        raise ValueError("标题评分维度不完整")
    for name, maximum in SCORE_LIMITS.items():
        value = scores[name]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
            raise ValueError(f"标题评分 {name} 必须是 0–{maximum} 的整数")
    if repair_attempts_used not in {0, 1}:
        raise ValueError("每个方向最多自动修正一次")

    failures = list(dict.fromkeys(hard_failures or []))
    issue_list = list(dict.fromkeys(issues or []))
    unknown_failures = set(failures) - HARD_FAILURES
    unknown_issues = set(issue_list) - ISSUES
    if unknown_failures:
        raise ValueError(f"未知标题硬失败：{', '.join(sorted(unknown_failures))}")
    if unknown_issues:
        raise ValueError(f"未知标题问题：{', '.join(sorted(unknown_issues))}")

    artifact = artifact_path.expanduser().resolve()
    plan_path = layout_plan_path.expanduser().resolve()
    if not artifact.is_file():
        raise FileNotFoundError(f"找不到标题成品：{artifact}")
    if not plan_path.is_file():
        raise FileNotFoundError(f"找不到标题布局计划：{plan_path}")
    plan = load_json(plan_path)
    validate_document(plan, "title_layout_plan.schema.json")
    if plan["orientation"] != orientation:
        raise ValueError("标题布局计划方向与评分方向不一致")

    total = sum(scores.values())
    qualified = total >= 85 and not failures
    if qualified:
        next_action, step = "submit", None
    elif repair_attempts_used == 0:
        next_action, step = "repair", choose_repair_step(issue_list)
    else:
        next_action, step = "blocked", None
    report = {
        "schema_version": "1.0",
        "orientation": orientation,
        "artifact": {"path": str(artifact), "sha256": sha256_file(artifact)},
        "layout_plan": {"path": str(plan_path), "sha256": sha256_file(plan_path)},
        "scores": scores,
        "total": total,
        "hard_failures": failures,
        "issues": issue_list,
        "qualified": qualified,
        "repair": {
            "attempts_used": repair_attempts_used,
            "max_attempts": 1,
            "allowed": next_action == "repair",
            "next_action": next_action,
            "step": step,
        },
        "created_at": utc_now(),
    }
    validate_document(report, "title_quality_report.schema.json")
    return report


def request_repair(report: dict[str, Any]) -> str:
    validate_document(report, "title_quality_report.schema.json")
    repair = report["repair"]
    if repair["next_action"] != "repair" or not repair["allowed"]:
        if repair["attempts_used"] >= repair["max_attempts"]:
            raise ValueError("该方向已经使用一次自动修正，必须暂停并请用户决定")
        raise ValueError("当前标题无需自动修正")
    return str(repair["step"])


def main() -> int:
    parser = argparse.ArgumentParser(description="生成标题专项质量报告与单次修正路由。")
    parser.add_argument("--orientation", required=True, choices=["landscape", "portrait"])
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--layout-plan", required=True, type=Path)
    for name, maximum in SCORE_LIMITS.items():
        parser.add_argument(f"--{name.replace('_', '-')}", required=True, type=int, metavar=f"0-{maximum}")
    parser.add_argument("--hard-failure", action="append", default=[], choices=sorted(HARD_FAILURES))
    parser.add_argument("--issue", action="append", default=[], choices=sorted(ISSUES))
    parser.add_argument("--repair-attempts-used", type=int, choices=[0, 1], default=0)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metrics", type=Path)
    args = parser.parse_args()
    scores = {name: getattr(args, name) for name in SCORE_LIMITS}
    report = build_quality_report(
        args.orientation,
        args.artifact,
        args.layout_plan,
        scores,
        hard_failures=args.hard_failure,
        issues=args.issue,
        repair_attempts_used=args.repair_attempts_used,
    )
    save_json(args.output.expanduser().resolve(), report)
    if args.metrics:
        recorder = MetricsRecorder(args.metrics)
        recorder.increment("visual_review_calls", stage="title_quality", orientation=args.orientation)
    print(args.output.expanduser().resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}")
        raise SystemExit(1)
