from __future__ import annotations

from pathlib import Path
from typing import Any

from project_io import resolve_project_path


TEXTBOOK_STAGES = (
    "initialized",
    "analyzing_source",
    "awaiting_title",
    "planning_landscape",
    "generating_landscape",
    "validating_landscape",
    "awaiting_landscape_approval",
    "revising_landscape",
    "generating_portrait",
    "validating_portrait",
    "awaiting_portrait_approval",
    "revising_portrait",
    "deriving_title",
    "blocked",
    "complete",
)

TEMPLATE_STAGES = (
    "initialized",
    "analyzing_source",
    "awaiting_title",
    "regenerating_source",
    "validating_source",
    "awaiting_source_approval",
    "deriving_opposite",
    "validating_opposite",
    "awaiting_opposite_approval",
    "revising_source",
    "revising_opposite",
    "deriving_title",
    "blocked",
    "complete",
)


TEXTBOOK_TRANSITIONS = {
    "initialized": {"analyzing_source", "blocked"},
    "analyzing_source": {"awaiting_title", "blocked"},
    "awaiting_title": {"planning_landscape", "blocked"},
    "planning_landscape": {"generating_landscape", "blocked"},
    "generating_landscape": {"validating_landscape", "blocked"},
    "validating_landscape": {"awaiting_landscape_approval", "generating_landscape", "blocked"},
    "awaiting_landscape_approval": {"revising_landscape", "generating_portrait", "blocked"},
    "revising_landscape": {"validating_landscape", "blocked"},
    "generating_portrait": {"validating_portrait", "revising_landscape", "blocked"},
    "validating_portrait": {"awaiting_portrait_approval", "generating_portrait", "revising_landscape", "blocked"},
    "awaiting_portrait_approval": {"revising_portrait", "revising_landscape", "complete", "blocked"},
    "revising_portrait": {"validating_portrait", "blocked"},
    "deriving_title": {"complete", "blocked"},
    "blocked": set(TEXTBOOK_STAGES) - {"blocked", "complete"},
    "complete": {"deriving_title", "revising_landscape", "revising_portrait"},
}

TEMPLATE_TRANSITIONS = {
    "initialized": {"analyzing_source", "blocked"},
    "analyzing_source": {"awaiting_title", "blocked"},
    "awaiting_title": {"regenerating_source", "blocked"},
    "regenerating_source": {"validating_source", "blocked"},
    "validating_source": {"awaiting_source_approval", "regenerating_source", "blocked"},
    "awaiting_source_approval": {"revising_source", "deriving_opposite", "blocked"},
    "revising_source": {"validating_source", "blocked"},
    "deriving_opposite": {"validating_opposite", "revising_source", "blocked"},
    "validating_opposite": {"awaiting_opposite_approval", "deriving_opposite", "revising_source", "blocked"},
    "awaiting_opposite_approval": {"revising_opposite", "revising_source", "complete", "blocked"},
    "revising_opposite": {"validating_opposite", "blocked"},
    "deriving_title": {"complete", "blocked"},
    "blocked": set(TEMPLATE_STAGES) - {"blocked", "complete"},
    "complete": {"deriving_title", "revising_source", "revising_opposite"},
}


def workflow_mode(manifest: dict[str, Any]) -> str:
    mode = manifest.get("selected_mode") or manifest.get("mode")
    if mode not in {"textbook_cover", "template_bidirectional"}:
        raise ValueError("manifest 缺少有效 selected_mode")
    return mode


def _require_title(manifest: dict[str, Any]) -> None:
    title = manifest.get("current_title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("当前阶段必须已有用户手动输入的非空标题")


def _require_file(project: Path | None, relative: object, label: str) -> None:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError(f"当前阶段缺少{label}路径")
    if project is None:
        return
    path = resolve_project_path(project, relative, must_exist=True)
    if not path.is_file():
        raise FileNotFoundError(f"当前阶段缺少{label}：{relative}")


def _check_prerequisites(
    manifest: dict[str, Any], target: str, project: Path | None
) -> None:
    mode = workflow_mode(manifest)
    if mode == "textbook_cover":
        if target in {
            "awaiting_title",
            "planning_landscape",
            "generating_landscape",
            "validating_landscape",
            "awaiting_landscape_approval",
            "revising_landscape",
            "generating_portrait",
            "validating_portrait",
            "awaiting_portrait_approval",
            "revising_portrait",
            "deriving_title",
            "complete",
        }:
            _require_file(project, manifest.get("style_dna_path"), "Style DNA")
            _require_file(project, manifest.get("character_identity_path"), "角色身份档案")
        if target in {
            "planning_landscape",
            "generating_landscape",
            "validating_landscape",
            "awaiting_landscape_approval",
            "revising_landscape",
            "generating_portrait",
            "validating_portrait",
            "awaiting_portrait_approval",
            "revising_portrait",
            "deriving_title",
            "complete",
        }:
            _require_title(manifest)
        if target in {"generating_portrait", "validating_portrait", "awaiting_portrait_approval", "revising_portrait", "complete"}:
            if manifest.get("landscape", {}).get("status") != "approved":
                raise ValueError("横版未批准，不能进入竖版阶段")
        if target == "complete" and manifest.get("portrait", {}).get("status") != "approved":
            raise ValueError("竖版未批准，不能完成项目")
    else:
        if target in set(TEMPLATE_STAGES) - {"initialized", "analyzing_source", "blocked"}:
            _require_file(project, manifest.get("template_dna_path"), "Template DNA")
        if target in set(TEMPLATE_STAGES) - {"initialized", "analyzing_source", "awaiting_title", "blocked"}:
            _require_title(manifest)
        source = manifest.get("source_orientation")
        if target in {"deriving_opposite", "validating_opposite", "awaiting_opposite_approval", "revising_opposite", "complete"}:
            if source not in {"landscape", "portrait"} or manifest.get(source, {}).get("status") != "approved":
                raise ValueError("源方向未批准，不能进入另一方向阶段")
        opposite = manifest.get("opposite_orientation")
        if target == "complete" and (
            opposite not in {"landscape", "portrait"}
            or manifest.get(opposite, {}).get("status") != "approved"
        ):
            raise ValueError("另一方向未批准，不能完成项目")


def transition(
    manifest: dict[str, Any],
    target: str,
    *,
    project: Path | None = None,
    allow_same: bool = False,
) -> None:
    mode = workflow_mode(manifest)
    current = manifest.get("workflow", {}).get("stage")
    transitions = TEXTBOOK_TRANSITIONS if mode == "textbook_cover" else TEMPLATE_TRANSITIONS
    if current not in transitions:
        raise ValueError(f"当前阶段不属于 v1.7 状态机：{current}")
    if target == current and allow_same:
        _check_prerequisites(manifest, target, project)
        return
    if target not in transitions[current]:
        raise ValueError(f"不允许从 {current} 跳转到 {target}")
    _check_prerequisites(manifest, target, project)
    manifest["workflow"]["stage"] = target
