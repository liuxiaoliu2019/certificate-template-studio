#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import load_json, project_file, save_json, sha256_file, utc_now

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - depends on local runtime
    raise SystemExit("缺少 Pillow。请先安装 Pillow。") from exc


SAFE_STAGES = [
    "template_analyzed",
    "waiting_for_title",
    "regenerating_source",
    "deriving_opposite",
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
    if not relative:
        raise ValueError("选择或批准方向时必须提供 --artifact")
    path = project_file(project, relative)
    if not path.is_file():
        raise FileNotFoundError(f"项目内找不到成品：{relative}")
    return path.relative_to(project.resolve()).as_posix()


def approval_words_valid(orientation: str, words: str | None) -> bool:
    if not words or not words.strip():
        return False
    keyword = "横版定稿" if orientation == "landscape" else "竖版定稿"
    return keyword in words


def checked_finalization_report(project: Path, relative: str | None, artifact: str, orientation: str) -> str:
    if not relative:
        raise ValueError("新版项目批准 Master 时必须提供 --finalization-report")
    report_path = project_file(project, relative)
    if not report_path.is_file():
        raise FileNotFoundError(f"项目内找不到收尾报告：{relative}")
    report = load_json(report_path)
    if report.get("status") != "passed" or report.get("orientation") != orientation:
        raise ValueError("收尾报告未通过或方向不匹配")
    expected = {"landscape": (2172, 1536), "portrait": (1536, 2172)}[orientation]
    output = report.get("output", {})
    if (output.get("width_px"), output.get("height_px")) != expected or output.get("format") != "PNG":
        raise ValueError("收尾报告的输出尺寸或格式不合格")
    artifact_path = project_file(project, artifact)
    reported_path = Path(str(output.get("path", "")))
    if reported_path.is_absolute():
        matches = reported_path.resolve() == artifact_path.resolve()
    else:
        matches = project_file(project, reported_path.as_posix()).resolve() == artifact_path.resolve()
    if not matches:
        raise ValueError("收尾报告引用的成品与待批准成品不一致")
    with Image.open(artifact_path) as image:
        if image.size != expected or image.format != "PNG":
            raise ValueError("待批准成品的实际尺寸或格式不合格")
    if output.get("sha256") != sha256_file(artifact_path):
        raise ValueError("待批准成品与收尾报告哈希不一致")
    return report_path.relative_to(project.resolve()).as_posix()


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
            manifest["workflow"]["stage"] = "deriving_title"
        else:
            manifest["workflow"]["stage"] = "title_confirmed"

    elif args.stage:
        if args.stage == "template_analyzed":
            dna = project_file(project, manifest["template_dna_path"])
            if not dna.is_file():
                raise FileNotFoundError("登记 template_analyzed 前必须保存 analysis/template_dna.json")
            manifest["workflow"]["stage"] = "template_analyzed"
        elif args.stage == "waiting_for_title":
            manifest["workflow"]["stage"] = "waiting_for_title"
        elif args.stage == "regenerating_source":
            if not manifest.get("current_title"):
                raise ValueError("未输入用户标题，不能生成同方向版本")
            manifest[source]["status"] = "generating"
            manifest["workflow"]["stage"] = "regenerating_source"
        elif args.stage == "deriving_opposite":
            if manifest[source]["status"] != "approved":
                raise ValueError("源方向未批准，不能生成另一方向")
            manifest[opposite]["status"] = "generating"
            manifest["workflow"]["stage"] = "deriving_opposite"

    elif args.select_orientation:
        orientation = args.select_orientation
        if orientation == opposite and manifest[source]["status"] != "approved":
            raise ValueError("源方向未批准，不能选择另一方向候选")
        artifact = checked_artifact(project, args.artifact)
        report_path = None
        if manifest.get("schema_version") == "1.2" or args.finalization_report:
            report_path = checked_finalization_report(project, args.finalization_report, artifact, orientation)
        manifest[orientation]["selected_file"] = artifact
        if "finalization_report" in manifest[orientation]:
            manifest[orientation]["finalization_report"] = report_path
        manifest[orientation]["concepts"] = [artifact]
        manifest[orientation]["status"] = "awaiting_approval"
        manifest["workflow"]["stage"] = (
            "awaiting_source_approval" if orientation == source else "awaiting_opposite_approval"
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
        if manifest.get("schema_version") == "1.2" or args.finalization_report:
            report_path = checked_finalization_report(
                project, args.finalization_report, artifact, orientation
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
        approval = {
                "orientation": orientation,
                "artifact": artifact,
                "user_confirmation": args.user_confirmation.strip(),
                "approved_at": now,
            }
        if report_path:
            approval["finalization_report"] = report_path
        manifest["approvals"].append(approval)
        if orientation == source:
            if manifest[opposite]["status"] == "approved":
                manifest["workflow"]["stage"] = "complete"
            else:
                manifest[opposite]["status"] = "ready"
                manifest["workflow"]["stage"] = "source_approved"
        else:
            manifest["workflow"]["stage"] = "complete"

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
