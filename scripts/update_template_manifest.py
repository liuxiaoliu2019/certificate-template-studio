#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import load_json, project_file, save_json, utc_now
from approval_engine import (
    approval_event,
    approval_words_valid as strict_approval_words_valid,
    checked_artifact as strict_checked_artifact,
    validate_finalization_report,
)
from project_io import resolve_project_path
from workflow_engine import transition


SAFE_STAGES = [
    "analyzing_source",
    "awaiting_title",
    "regenerating_source",
    "validating_source",
    "deriving_opposite",
    "validating_opposite",
    "revising_source",
    "revising_opposite",
    "blocked",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="安全更新模板双向项目的标题、阶段、选择和审批。")
    parser.add_argument("project", type=Path, help="模板双向项目目录")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--set-title", help="保存用户手动输入的唯一标题")
    action.add_argument("--stage", choices=SAFE_STAGES, help="推进非审批阶段")
    action.add_argument("--select-orientation", choices=["landscape", "portrait"])
    action.add_argument("--approve-orientation", choices=["landscape", "portrait"])
    parser.add_argument("--artifact", help="选择或批准时的项目内成品相对路径")
    parser.add_argument("--user-confirmation", help="批准时保存用户明确确认原话")
    parser.add_argument("--finalization-report", help="批准时绑定通过的项目内收尾报告")
    return parser.parse_args()


def checked_artifact(project: Path, relative: str | None) -> str:
    return strict_checked_artifact(project, relative)


def approval_words_valid(orientation: str, words: str | None) -> bool:
    return strict_approval_words_valid(orientation, words)


def checked_finalization_report(project: Path, relative: str | None, artifact: str, orientation: str) -> str:
    manifest = load_json(project / "configs/template_project_manifest.json")
    report_path, _ = validate_finalization_report(
        project, relative, artifact, orientation, manifest
    )
    return report_path


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    manifest_path = project / "configs" / "template_project_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"找不到模板项目 manifest：{manifest_path}")
    manifest = load_json(manifest_path)
    if manifest.get("mode") != "template_bidirectional":
        raise ValueError("该项目不是模板双向生成模式")

    source = manifest["source_orientation"]
    opposite = manifest["opposite_orientation"]

    if args.set_title is not None:
        title = args.set_title.strip()
        if not title:
            raise ValueError("标题不能为空；标题必须来自用户手动输入")
        manifest["current_title"] = title
        if manifest["master"]["landscape"] and manifest["master"]["portrait"]:
            transition(manifest, "deriving_title", project=project)
        elif manifest["workflow"]["stage"] == "awaiting_title":
            transition(manifest, "regenerating_source", project=project)

    elif args.stage:
        transition(manifest, args.stage, project=project)
        if args.stage == "regenerating_source":
            manifest[source]["status"] = "generating"
        elif args.stage == "deriving_opposite":
            manifest[opposite]["status"] = "generating"

    elif args.select_orientation:
        orientation = args.select_orientation
        if orientation == opposite and manifest[source]["status"] != "approved":
            raise ValueError("源方向未批准，不能选择另一方向候选")
        artifact = checked_artifact(project, args.artifact)
        report_path = None
        if manifest.get("schema_version") in {"1.2", "1.3"} or args.finalization_report:
            report_path, _ = validate_finalization_report(
                project, args.finalization_report, artifact, orientation, manifest
            )
        manifest[orientation]["selected_file"] = artifact
        if "finalization_report" in manifest[orientation]:
            manifest[orientation]["finalization_report"] = report_path
        manifest[orientation]["concepts"] = [artifact]
        manifest[orientation]["status"] = "awaiting_approval"
        transition(
            manifest,
            "awaiting_source_approval" if orientation == source else "awaiting_opposite_approval",
            project=project,
        )

    elif args.approve_orientation:
        orientation = args.approve_orientation
        if not manifest.get("current_title"):
            raise ValueError("未输入用户标题，不能批准成品")
        if not approval_words_valid(orientation, args.user_confirmation):
            keyword = "横版定稿" if orientation == "landscape" else "竖版定稿"
            raise ValueError(f"审批原话必须明确包含“{keyword}”")
        if orientation == opposite and manifest[source]["status"] != "approved":
            raise ValueError("源方向未批准，不能批准另一方向")
        artifact = checked_artifact(project, args.artifact)
        report_path = None
        if manifest.get("schema_version") in {"1.2", "1.3"} or args.finalization_report:
            report_path, _ = validate_finalization_report(
                project, args.finalization_report, artifact, orientation, manifest
            )
        now = utc_now()
        manifest[orientation]["selected_file"] = artifact
        manifest[orientation]["status"] = "approved"
        if "finalization_report" in manifest[orientation]:
            manifest[orientation]["finalization_report"] = report_path
        manifest["master"][orientation] = artifact
        manifest["master"]["title"] = manifest.get("current_title")
        dna = project_file(project, manifest["template_dna_path"])
        if not dna.is_file():
            raise FileNotFoundError("缺少 Template DNA，不能批准")
        manifest["master"]["template_dna"] = manifest["template_dna_path"]
        approval = approval_event(
            orientation=orientation,
            artifact=artifact,
            artifact_path=resolve_project_path(project, artifact, must_exist=True),
            report_path=report_path,
            report_file=resolve_project_path(project, report_path, must_exist=True),
            title=manifest["current_title"],
            user_confirmation=args.user_confirmation or "",
            approved_at=now,
        )
        manifest["approvals"].append(approval)
        if orientation == source:
            if manifest[opposite]["status"] == "approved":
                transition(manifest, "complete", project=project)
            else:
                manifest[opposite]["status"] = "ready"
                transition(manifest, "deriving_opposite", project=project)
        else:
            transition(manifest, "complete", project=project)

    manifest["updated_at"] = utc_now()
    save_json(manifest_path, manifest)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
