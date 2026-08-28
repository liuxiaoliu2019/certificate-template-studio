from __future__ import annotations

from pathlib import Path
from typing import Any

from _common import sha256_file, utc_now
from schema_runtime import validate_document


SCORE_LIMITS = {
    "style_dna": 20,
    "certificate_style": 20,
    "composition": 20,
    "title": 15,
    "safe_zones": 10,
    "orientation_consistency": 10,
    "text_cleanliness": 5,
}


def _candidate_record(candidate: dict[str, Any]) -> dict[str, Any]:
    if set(candidate["scores"]) != set(SCORE_LIMITS):
        raise ValueError(f"候选 {candidate['candidate_id']} 评分维度不完整")
    for name, maximum in SCORE_LIMITS.items():
        value = candidate["scores"][name]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
            raise ValueError(f"候选 {candidate['candidate_id']} 的 {name} 必须是 0–{maximum} 整数")
    artifact = Path(candidate["artifact"]).expanduser().resolve()
    if not artifact.is_file():
        raise FileNotFoundError(f"找不到候选成品：{artifact}")
    total = sum(candidate["scores"].values())
    failures = list(dict.fromkeys(candidate.get("hard_failures", [])))
    return {
        "candidate_id": candidate["candidate_id"],
        "artifact": {"path": str(artifact), "sha256": sha256_file(artifact)},
        "scores": candidate["scores"],
        "total": total,
        "hard_failures": failures,
        "qualified": total >= 85 and not failures,
    }


def build_quality_gate(
    orientation: str,
    candidates: list[dict[str, Any]],
    *,
    repair_used: bool = False,
    regeneration_used: bool = False,
) -> dict[str, Any]:
    if orientation not in {"landscape", "portrait"}:
        raise ValueError("orientation 必须是 landscape 或 portrait")
    if not candidates:
        raise ValueError("至少需要一个候选")
    records = [_candidate_record(candidate) for candidate in candidates]
    if len({item["candidate_id"] for item in records}) != len(records):
        raise ValueError("candidate_id 不得重复")
    ranked = sorted(records, key=lambda item: (-item["total"], item["candidate_id"]))
    qualified = [item for item in ranked if item["qualified"]]
    viable = [item for item in ranked if not item["hard_failures"]]
    if qualified:
        selected = qualified[0]
        action = "submit_best"
        visible = [selected["candidate_id"]]
        others = [item["candidate_id"] for item in qualified[1:]]
    elif viable and viable[0]["total"] >= 75 and not repair_used:
        selected = viable[0]
        action, visible, others = "repair_best", [], []
    elif viable and not regeneration_used:
        selected = viable[0]
        action, visible, others = "regenerate_best", [], []
    else:
        selected = None
        action, visible, others = "blocked", [], []
    report = {
        "schema_version": "1.0",
        "orientation": orientation,
        "candidates": records,
        "selected_candidate_id": selected["candidate_id"] if selected else None,
        "action": action,
        "default_visible_candidate_ids": visible,
        "other_qualified_candidate_ids": others,
        "created_at": utc_now(),
    }
    validate_document(report, "quality_report.schema.json")
    return report


def user_summary(report: dict[str, Any]) -> str:
    validate_document(report, "quality_report.schema.json")
    if report["action"] == "submit_best":
        return f"已完成内部质量检查，现提交最佳方案 {report['selected_candidate_id']} 供确认。"
    if report["action"] in {"repair_best", "regenerate_best"}:
        return "最佳候选正在进行一次自动优化，完成后再提交。"
    return "当前候选仍未达到提交标准，需要用户决定是否重做或调整要求。"
