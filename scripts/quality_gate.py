from __future__ import annotations

from pathlib import Path
from typing import Any

from _common import load_json, sha256_file, utc_now
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
    used_character_ids = list(dict.fromkeys(candidate.get("used_character_ids", [])))
    identity_paths = [Path(value).expanduser().resolve() for value in candidate.get("character_identity_reports", [])]
    report_ids: set[str] = set()
    for report_path in identity_paths:
        if not report_path.is_file():
            raise FileNotFoundError(f"找不到角色身份报告：{report_path}")
        identity = load_json(report_path)
        validate_document(identity, "character_identity_report.schema.json")
        if identity["candidate"]["sha256"] != sha256_file(artifact):
            raise ValueError(f"角色身份报告未绑定当前候选：{report_path}")
        report_ids.add(identity["character_id"])
        if identity["status"] == "blocked":
            failures.append("identity_source_insufficient")
        elif identity["status"] != "passed":
            failures.append("identity_hard_fail")
    if set(used_character_ids) != report_ids:
        missing = sorted(set(used_character_ids) - report_ids)
        if missing:
            failures.append("identity_report_missing")
        extra = sorted(report_ids - set(used_character_ids))
        if extra:
            raise ValueError(f"存在未使用角色的身份报告：{', '.join(extra)}")
    failures = list(dict.fromkeys(failures))
    return {
        "candidate_id": candidate["candidate_id"],
        "artifact": {"path": str(artifact), "sha256": sha256_file(artifact)},
        "scores": candidate["scores"],
        "total": total,
        "hard_failures": failures,
        "qualified": total >= 85 and not failures,
        "used_character_ids": used_character_ids,
        "character_identity_reports": [str(path) for path in identity_paths],
    }


def build_character_identity_report(
    character_id: str,
    source_crop: Path,
    candidate: Path,
    score: int,
    immutable_features: dict[str, bool],
    *,
    source_sufficient: bool = True,
) -> dict[str, Any]:
    required = {"hair_or_head", "face", "clothing_or_surface", "accessories", "species", "proportions"}
    if set(immutable_features) != required:
        raise ValueError("角色不可改变特征检查不完整")
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("角色身份分必须是 0–100 整数")
    source = source_crop.expanduser().resolve()
    artifact = candidate.expanduser().resolve()
    if not source.is_file() or not artifact.is_file():
        raise FileNotFoundError("角色原图裁切或候选图不存在")
    if not source_sufficient:
        status = "blocked"
    elif score < 85 or not all(immutable_features.values()):
        status = "hard_fail"
    else:
        status = "passed"
    report = {
        "schema_version": "1.0",
        "character_id": character_id,
        "source_crop": {"path": str(source), "sha256": sha256_file(source)},
        "candidate": {"path": str(artifact), "sha256": sha256_file(artifact)},
        "score": score,
        "immutable_features": immutable_features,
        "source_sufficient": source_sufficient,
        "status": status,
        "created_at": utc_now(),
    }
    validate_document(report, "character_identity_report.schema.json")
    return report


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
