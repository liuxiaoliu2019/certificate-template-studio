#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import load_json, parse_assignment, project_file, save_json, set_dotted, sha256_file, utc_now

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - depends on local runtime
    raise SystemExit("缺少 Pillow。请先安装 Pillow。") from exc


STYLE_FAMILIES = {
    "S01_classic_ceremonial_gold",
    "S02_modern_academic_geometry",
    "S03_dark_premium_technology",
    "S04_fresh_botanical_watercolor",
    "S05_childrens_flat_education",
    "S06_themed_dynamic_event",
    "S07_chinese_ceremonial_award",
}
SAFE_STAGES = [
    "initialized",
    "analyzing",
    "awaiting_title",
    "exploring_landscape",
    "revising_landscape",
    "awaiting_landscape_approval",
    "generating_portrait",
    "awaiting_portrait_approval",
    "deriving_title",
    "style_analyzed",
    "waiting_for_title",
    "title_confirmed",
    "styles_recommended",
    "landscape_generated",
    "landscape_selected",
    "landscape_revising",
    "portrait_generated",
    "portrait_revising",
]
LOCKED_PREFIXES = (
    "workflow.stage",
    "landscape.status",
    "portrait.status",
    "master",
    "approvals",
    "style_engine.approved_profile",
    "style_engine.master_profile_path",
    "style_engine.style_lock",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="安全更新项目 manifest、风格登记与审批状态。")
    parser.add_argument("project", type=Path, help="证书项目目录")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=JSON", help="更新普通字段，可重复")
    parser.add_argument("--stage", choices=SAFE_STAGES, help="更新非审批工作流阶段")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--register-style-recommendation", metavar="RELATIVE_PATH")
    action.add_argument("--select-landscape", metavar="RELATIVE_PATH")
    action.add_argument("--select-portrait", metavar="RELATIVE_PATH")
    action.add_argument("--approve-landscape", metavar="RELATIVE_PATH")
    action.add_argument("--approve-portrait", metavar="RELATIVE_PATH")
    action.add_argument("--invalidate-landscape", action="store_true")
    parser.add_argument("--style-profile", metavar="RELATIVE_PATH", help="选择或批准横版时绑定的 Style Profile")
    parser.add_argument("--user-confirmation", help="审批时保存用户明确确认的原话")
    parser.add_argument("--finalization-report", metavar="RELATIVE_PATH", help="批准时绑定通过的收尾报告")
    parser.add_argument("--reason", help="使已批准横版失效时的原因")
    return parser.parse_args()


def checked_artifact(project: Path, relative: str) -> str:
    path = project_file(project, relative)
    if not path.is_file():
        raise FileNotFoundError(f"项目内找不到成品：{relative}")
    return path.relative_to(project.resolve()).as_posix()


def checked_profile(project: Path, relative: str) -> tuple[str, dict]:
    path = project_file(project, relative)
    if not path.is_file():
        raise FileNotFoundError(f"项目内找不到 Style Profile：{relative}")
    profile = load_json(path)
    family = profile.get("style_family")
    score = profile.get("compatibility_score")
    if family not in STYLE_FAMILIES or not isinstance(score, int) or score < 70:
        raise ValueError("Style Profile 的家族或兼容性分数不合格")
    return path.relative_to(project.resolve()).as_posix(), profile


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


def register_recommendation(manifest: dict, project: Path, relative: str) -> None:
    if not manifest.get("current_title"):
        raise ValueError("未输入用户标题，不能登记风格推荐")
    path = project_file(project, relative)
    data = load_json(path)
    evaluations = data.get("evaluations", [])
    profiles = data.get("recommended_profiles", [])
    if len(evaluations) != 7 or len({item.get("style_family") for item in evaluations}) != 7:
        raise ValueError("风格推荐必须包含 7 个不同家族的评估")
    if len(profiles) != 3 or len({item.get("style_family") for item in profiles}) != 3:
        raise ValueError("必须推荐 3 个不同的风格家族")
    if any(item.get("compatibility_score", -1) < 70 for item in profiles):
        raise ValueError("候选 Style Profile 兼容性不能低于 70")
    if data.get("diversity_check", {}).get("passed") is not True:
        raise ValueError("三方案风格差异检查未通过")
    profile_paths = []
    for profile in profiles:
        profile_id = profile.get("profile_id")
        if not profile_id:
            raise ValueError("Style Profile 缺少 profile_id")
        target = project / "styles" / f"{profile_id}.json"
        save_json(target, profile)
        profile_paths.append(target.relative_to(project).as_posix())
    state = manifest["style_engine"]
    state["status"] = "recommended"
    state["recommendation_path"] = path.relative_to(project).as_posix()
    state["candidate_profiles"] = profile_paths
    state["selected_profile"] = None
    state["approved_profile"] = None
    state["style_lock"] = "unlocked"
    manifest["workflow"]["stage"] = "styles_recommended"


def approval_words_valid(orientation: str, words: str | None) -> bool:
    if not words or not words.strip():
        return False
    keyword = "横版定稿" if orientation == "landscape" else "竖版定稿"
    return keyword in words


def write_master_profile(manifest: dict, project: Path, profile: dict) -> None:
    now = utc_now()
    target = project / "configs" / "master_style_profile.json"
    created_at = now
    if target.is_file():
        created_at = load_json(target).get("created_at", now)
    payload = {
        "schema_version": "1.2" if profile.get("schema_version") == "1.2" else "1.0",
        "textbook_key": manifest["textbook_key"],
        "source_style_dna": manifest["style_dna_path"],
        "approved_style_profile": profile,
        "master_title": manifest["current_title"],
        "masters": {
            "landscape": manifest["master"]["landscape"],
            "portrait": manifest["master"]["portrait"],
        },
        "title_rules": {
            "only_readable_text": True,
            "horizontal_center_x_percent": 50,
            "portrait_up_shift_cm": 1.5,
        },
        "composition_invariants": [
            "左右下角均有清晰可见的视觉锚点",
            "两侧以由大到小的同风格元素形成弱连接",
            "中央变量安全区和右下偏内侧落款区可排版",
            "控制图只控制区域秩序且不进入成品",
        ],
        "created_at": created_at,
        "updated_at": now,
    }
    if payload["schema_version"] == "1.2":
        payload["source_character_identity"] = manifest.get("character_identity_path")
        payload["used_character_ids"] = profile.get("used_character_ids", [])
    save_json(target, payload)
    manifest["style_engine"]["master_profile_path"] = target.relative_to(project).as_posix()


def approve(
    manifest: dict,
    project: Path,
    orientation: str,
    relative: str,
    words: str | None,
    style_profile: str | None,
    finalization_report: str | None,
) -> None:
    if not approval_words_valid(orientation, words):
        label = "横版定稿" if orientation == "landscape" else "竖版定稿"
        raise ValueError(f"审批原话必须明确包含“{label}”")
    artifact = checked_artifact(project, relative)
    report_path = None
    if manifest.get("schema_version") == "1.4" or finalization_report:
        report_path = checked_finalization_report(project, finalization_report, artifact, orientation)
    if orientation == "portrait" and manifest["landscape"]["status"] != "approved":
        raise ValueError("横版未批准，不能批准竖版")

    profile = None
    profile_path = None
    style_state = manifest.get("style_engine")
    if style_state:
        if orientation == "landscape":
            profile_path = style_profile or style_state.get("selected_profile")
            if not profile_path:
                raise ValueError("新版项目批准横版时必须绑定 Style Profile")
            profile_path, profile = checked_profile(project, profile_path)
            if profile_path not in style_state.get("candidate_profiles", []):
                raise ValueError("批准的 Style Profile 不在本轮三个候选中")
            style_state["selected_profile"] = profile_path
            style_state["approved_profile"] = profile_path
            style_state["status"] = "approved"
            style_state["style_lock"] = "profile_locked"
        else:
            profile_path = style_state.get("approved_profile")
            if not profile_path:
                raise ValueError("缺少已批准的横版 Style Profile")
            profile_path, profile = checked_profile(project, profile_path)

    now = utc_now()
    state = manifest[orientation]
    state["status"] = "approved"
    state["selected_file"] = artifact
    if "finalization_report" in state:
        state["finalization_report"] = report_path
    manifest["master"][orientation] = artifact
    manifest["master"]["title"] = manifest.get("current_title")
    if profile_path:
        manifest["master"]["style_profile"] = profile_path
    approval = {
            "orientation": orientation,
            "artifact": artifact,
            "user_confirmation": words.strip(),
            "approved_at": now,
        }
    if report_path:
        approval["finalization_report"] = report_path
    manifest["approvals"].append(approval)
    if orientation == "landscape":
        manifest["portrait"]["status"] = "ready"
        manifest["workflow"]["stage"] = "landscape_approved"
    else:
        manifest["workflow"]["stage"] = "complete"
    if profile:
        write_master_profile(manifest, project, profile)


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    manifest_path = project / "configs" / "project_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"找不到 manifest：{manifest_path}")
    manifest = load_json(manifest_path)

    title_changed = False
    for assignment in args.set:
        key, value = parse_assignment(assignment)
        if key.startswith(LOCKED_PREFIXES):
            raise ValueError(f"锁定字段不能用 --set 修改：{key}")
        set_dotted(manifest, key, value)
        if key == "current_title":
            title_changed = True

    if args.stage:
        manifest["workflow"]["stage"] = args.stage
        if args.stage in {"style_analyzed", "waiting_for_title", "awaiting_title"} and "style_engine" in manifest:
            manifest["style_engine"]["status"] = "waiting_for_title"
        elif args.stage == "title_confirmed" and "style_engine" in manifest:
            manifest["style_engine"]["status"] = "ready"
        elif args.stage == "landscape_generated":
            manifest["landscape"]["status"] = "exploring"
        elif args.stage in {"landscape_revising", "revising_landscape"}:
            manifest["landscape"]["status"] = "revising"
        elif args.stage == "portrait_generated":
            if manifest["landscape"]["status"] != "approved":
                raise ValueError("横版未批准，不能登记竖版已生成")
            manifest["portrait"]["status"] = "awaiting_approval"
        elif args.stage == "portrait_revising":
            if manifest["landscape"]["status"] != "approved":
                raise ValueError("横版未批准，不能进入竖版修改")
            manifest["portrait"]["status"] = "awaiting_approval"
    if args.register_style_recommendation:
        if "style_engine" not in manifest:
            raise ValueError("旧项目需先迁移或继续使用旧三方案流程")
        register_recommendation(manifest, project, args.register_style_recommendation)
    elif args.select_landscape:
        artifact = checked_artifact(project, args.select_landscape)
        manifest["landscape"]["selected_file"] = artifact
        manifest["landscape"]["status"] = "candidate_selected"
        manifest["workflow"]["stage"] = "landscape_selected"
        if "style_engine" in manifest:
            if not args.style_profile:
                raise ValueError("新版项目选择横版时必须提供 --style-profile")
            profile_path, _ = checked_profile(project, args.style_profile)
            if profile_path not in manifest["style_engine"]["candidate_profiles"]:
                raise ValueError("所选 Style Profile 不在本轮候选中")
            manifest["style_engine"]["selected_profile"] = profile_path
            manifest["style_engine"]["status"] = "selected"
            manifest["style_engine"]["style_lock"] = "family_locked"
    elif args.select_portrait:
        if manifest["landscape"]["status"] != "approved":
            raise ValueError("横版未批准，不能选择竖版候选")
        artifact = checked_artifact(project, args.select_portrait)
        manifest["portrait"]["selected_file"] = artifact
        manifest["portrait"]["status"] = "awaiting_approval"
        manifest["workflow"]["stage"] = "awaiting_portrait_approval"
    elif args.approve_landscape:
        approve(manifest, project, "landscape", args.approve_landscape, args.user_confirmation, args.style_profile, args.finalization_report)
    elif args.approve_portrait:
        approve(manifest, project, "portrait", args.approve_portrait, args.user_confirmation, None, args.finalization_report)
    elif args.invalidate_landscape:
        if not args.reason or not args.reason.strip():
            raise ValueError("使横版失效时必须提供 --reason")
        manifest["landscape"]["status"] = "revising"
        manifest["portrait"]["status"] = "stale"
        manifest["master"]["landscape"] = None
        manifest["master"]["portrait"] = None
        manifest["workflow"]["stage"] = "landscape_revising"
        if "style_engine" in manifest:
            manifest["style_engine"]["approved_profile"] = None
            manifest["style_engine"]["status"] = "stale"
            manifest["style_engine"]["style_lock"] = "family_locked"

    if title_changed:
        if not manifest.get("current_title"):
            raise ValueError("current_title 不能为空；标题必须来自用户手动输入")
        generation_path = project / "configs" / "generation_config.json"
        if generation_path.is_file():
            generation = load_json(generation_path)
            generation["title"]["value"] = manifest["current_title"]
            save_json(generation_path, generation)
        if manifest.get("master", {}).get("landscape"):
            manifest["workflow"]["stage"] = "deriving_title"
        else:
            manifest["workflow"]["stage"] = "title_confirmed"
            if "style_engine" in manifest:
                manifest["style_engine"]["status"] = "ready"

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
