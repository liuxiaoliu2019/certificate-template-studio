from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from PIL import Image

from project_io import load_json, relative_posix, resolve_project_path, sha256_file
from schema_runtime import validate_document


NEGATION_PATTERNS = (
    r"不要.{0,8}(?:确认|定稿)",
    r"(?:不|未|没有|尚未|还没|还不能|不能|暂不|先不).{0,8}(?:确认|定稿)",
    r"(?:确认|定稿).{0,6}(?:不要|不行|取消|有问题|再改|未完成)",
    r"(?:是否|能否|可以不可以|可不可以).{0,8}(?:确认|定稿)",
    r"(?:确认|定稿).{0,8}(?:吗|么|？|\?)$",
)


def normalize_title(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return unicodedata.normalize("NFKC", value).strip()


def approval_words_valid(orientation: str, words: str | None) -> bool:
    if orientation not in {"landscape", "portrait"} or not words:
        return False
    text = unicodedata.normalize("NFKC", words).strip()
    if not text or any(re.search(pattern, text) for pattern in NEGATION_PATTERNS):
        return False
    label = "横版" if orientation == "landscape" else "竖版"
    positive_patterns = (
        rf"确认.{{0,16}}{label}.{{0,8}}定稿",
        rf"确认.{{0,16}}(?:为|作为){label}定稿",
        rf"{label}.{{0,8}}(?:确认|正式).{{0,8}}定稿",
        rf"确认{label}定稿",
    )
    return any(re.search(pattern, text) for pattern in positive_patterns)


def checked_artifact(project: Path, relative: str | None) -> str:
    if not relative:
        raise ValueError("批准或选择方向时必须提供成品路径")
    path = resolve_project_path(project, relative, must_exist=True)
    if not path.is_file():
        raise FileNotFoundError(f"项目内找不到成品：{relative}")
    return relative_posix(path, project)


def _reported_output_matches(project: Path, reported: object, artifact_path: Path) -> bool:
    if not isinstance(reported, str) or not reported.strip():
        return False
    candidate = Path(reported)
    if candidate.is_absolute():
        return candidate.resolve() == artifact_path.resolve()
    return resolve_project_path(project, candidate).resolve() == artifact_path.resolve()


def validate_finalization_report(
    project: Path,
    relative: str | None,
    artifact: str,
    orientation: str,
    manifest: dict[str, Any],
    *,
    style_profile: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    if not relative:
        raise ValueError("新版项目批准 Master 时必须提供 --finalization-report")
    report_path = resolve_project_path(project, relative, must_exist=True)
    if not report_path.is_file():
        raise FileNotFoundError(f"项目内找不到收尾报告：{relative}")
    report = load_json(report_path)
    validate_document(report, "finalization_report.schema.json")
    if report.get("status") != "passed" or report.get("orientation") != orientation:
        raise ValueError("收尾报告未通过或方向不匹配")

    expected_title = normalize_title(manifest.get("current_title"))
    report_title = normalize_title(report.get("title", {}).get("value"))
    if not expected_title or report_title != expected_title:
        raise ValueError("收尾报告标题与项目当前标题不一致")

    expected = {"landscape": (2172, 1536), "portrait": (1536, 2172)}[orientation]
    output = report.get("output", {})
    if (output.get("width_px"), output.get("height_px")) != expected or output.get("format") != "PNG":
        raise ValueError("收尾报告的输出尺寸或格式不合格")
    artifact_path = resolve_project_path(project, artifact, must_exist=True)
    if not _reported_output_matches(project, output.get("path"), artifact_path):
        raise ValueError("收尾报告引用的成品与待批准成品不一致")
    with Image.open(artifact_path) as image:
        if image.size != expected or image.format != "PNG":
            raise ValueError("待批准成品的实际尺寸或格式不合格")
    if output.get("sha256") != sha256_file(artifact_path):
        raise ValueError("待批准成品与收尾报告哈希不一致")

    if style_profile:
        expected_mode = style_profile.get("title_treatment", {}).get("render_mode")
        if expected_mode and report.get("title_render_mode") != expected_mode:
            raise ValueError("收尾报告标题模式与 Style Profile 不一致")

    return relative_posix(report_path, project), report


def approval_event(
    *,
    orientation: str,
    artifact: str,
    artifact_path: Path,
    report_path: str,
    report_file: Path,
    title: str,
    user_confirmation: str,
    approved_at: str,
    style_profile: str | None = None,
    title_layout_plan: str | None = None,
) -> dict[str, Any]:
    return {
        "orientation": orientation,
        "artifact": artifact,
        "artifact_sha256": sha256_file(artifact_path),
        "user_confirmation": user_confirmation.strip(),
        "approval_intent": "explicit_positive",
        "title": normalize_title(title),
        "finalization_report": report_path,
        "finalization_report_sha256": sha256_file(report_file),
        "style_profile": style_profile,
        "title_layout_plan": title_layout_plan,
        "historical": False,
        "approved_at": approved_at,
    }
