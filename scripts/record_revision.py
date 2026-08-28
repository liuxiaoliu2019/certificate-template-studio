#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from _common import load_json, project_file, relative_posix, save_json, sha256_file, utc_now
from revision_engine import invalidate_for_revision, verify_rollback_target
from workflow_engine import transition


STYLE_FAMILIES = [
    "S01_classic_ceremonial_gold",
    "S02_modern_academic_geometry",
    "S03_dark_premium_technology",
    "S04_fresh_botanical_watercolor",
    "S05_childrens_flat_education",
    "S06_themed_dynamic_event",
    "S07_chinese_ceremonial_award",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="保存修订成品、反馈和非破坏性回退记录。")
    parser.add_argument("project", type=Path, help="证书项目目录")
    parser.add_argument("--orientation", required=True, choices=["landscape", "portrait"])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--artifact", type=Path, help="本次新生成的图片")
    mode.add_argument("--rollback", metavar="REVISION_ID", help="回退到既有 revision，不删除任何历史")
    parser.add_argument("--level", type=int, choices=[1, 2, 3], help="新修订必须指定 1/2/3")
    parser.add_argument("--source", help="作为本次修改基础的项目内相对路径或 revision id")
    parser.add_argument("--feedback", action="append", required=True, help="用户反馈，可重复")
    parser.add_argument("--style-family", choices=STYLE_FAMILIES, help="本次修订使用的风格家族")
    parser.add_argument("--profile", help="项目内 Style Profile 相对路径")
    parser.add_argument("--changed-param", action="append", default=[], help="发生变化的 Profile 参数，可重复")
    parser.add_argument("--locked-param", action="append", default=[], help="本次锁定的 Profile 参数，可重复")
    return parser.parse_args()


def invalidate_if_needed(manifest: dict) -> None:
    if manifest["landscape"]["status"] == "approved":
        invalidate_for_revision(manifest, "landscape")


def read_profile(project: Path, relative: str | None) -> tuple[str | None, dict | None]:
    if not relative:
        return None, None
    path = project_file(project, relative)
    if not path.is_file():
        raise FileNotFoundError(f"找不到 Style Profile：{relative}")
    profile = load_json(path)
    if profile.get("style_family") not in STYLE_FAMILIES:
        raise ValueError("Style Profile 的 style_family 无效")
    return path.relative_to(project).as_posix(), profile


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    manifest_path = project / "configs" / "project_manifest.json"
    log_path = project / "revisions" / "revision_log.json"
    if not manifest_path.is_file() or not log_path.is_file():
        raise FileNotFoundError("项目缺少 manifest 或 revision_log，请先运行 init_project.py")

    manifest = load_json(manifest_path)
    log = load_json(log_path)
    if args.orientation == "portrait" and manifest["landscape"]["status"] != "approved":
        raise ValueError("横版未批准，不能记录竖版修订")
    approval_state_before = manifest[args.orientation]["status"]
    profile_path, profile = read_profile(project, args.profile)
    style_family = args.style_family or (profile or {}).get("style_family")
    style_state = manifest.get("style_engine", {})
    active_profile_path = style_state.get("selected_profile") or style_state.get("approved_profile")
    _, active_profile = read_profile(project, active_profile_path)
    if args.artifact and args.level in (1, 2) and active_profile:
        active_family = active_profile.get("style_family")
        if style_family and style_family != active_family:
            raise ValueError("LEVEL1/2 不允许更换风格家族；请使用 LEVEL3")
        style_family = active_family
        profile_path = profile_path or active_profile_path
    log["sequence"] += 1
    revision_id = f"r{log['sequence']:03d}"
    now = utc_now()

    if args.artifact:
        if args.level is None:
            raise ValueError("保存新修订时必须提供 --level 1/2/3")
        source_artifact = args.artifact.expanduser().resolve()
        if not source_artifact.is_file():
            raise FileNotFoundError(f"找不到修订图片：{source_artifact}")
        suffix = source_artifact.suffix.lower() or ".png"
        destination = project / "revisions" / f"{args.orientation}_{revision_id}{suffix}"
        if destination.exists():
            raise FileExistsError(f"修订目标已存在，未覆盖：{destination}")
        shutil.copy2(source_artifact, destination)
        artifact = relative_posix(destination, project)
        entry = {
            "revision_id": revision_id,
            "orientation": args.orientation,
            "action": "revision",
            "level": args.level,
            "source": args.source,
            "artifact": artifact,
            "sha256": sha256_file(destination),
            "feedback": [item.strip() for item in args.feedback if item.strip()],
            "rollback_to": None,
            "created_at": now,
            "style_family": style_family,
            "style_profile": profile_path,
            "changed_parameters": [item.strip() for item in args.changed_param if item.strip()],
            "locked_parameters": [item.strip() for item in args.locked_param if item.strip()],
            "approval_state_before": approval_state_before,
            "approval_state_after": "revising" if args.orientation == "landscape" else "awaiting_approval",
        }
        if not entry["feedback"]:
            raise ValueError("反馈不能为空")
        log["active_by_orientation"][args.orientation] = revision_id
        manifest[args.orientation]["active_revision_id"] = revision_id
        manifest[args.orientation]["selected_file"] = artifact
    else:
        target = next(
            (
                item
                for item in log["entries"]
                if item["revision_id"] == args.rollback
                and item["orientation"] == args.orientation
                and item["action"] == "revision"
            ),
            None,
        )
        if target is None or not target.get("artifact"):
            raise ValueError(f"找不到可回退的 {args.orientation} revision：{args.rollback}")
        verify_rollback_target(project, target)
        entry = {
            "revision_id": revision_id,
            "orientation": args.orientation,
            "action": "rollback",
            "level": None,
            "source": log["active_by_orientation"].get(args.orientation),
            "artifact": None,
            "sha256": None,
            "feedback": [item.strip() for item in args.feedback if item.strip()],
            "rollback_to": args.rollback,
            "created_at": now,
            "style_family": target.get("style_family"),
            "style_profile": target.get("style_profile"),
            "changed_parameters": [],
            "locked_parameters": target.get("locked_parameters", []),
            "approval_state_before": approval_state_before,
            "approval_state_after": "revising" if args.orientation == "landscape" else "awaiting_approval",
        }
        if not entry["feedback"]:
            raise ValueError("反馈不能为空")
        log["active_by_orientation"][args.orientation] = args.rollback
        manifest[args.orientation]["active_revision_id"] = args.rollback
        manifest[args.orientation]["selected_file"] = target["artifact"]

    log["entries"].append(entry)
    if args.orientation == "landscape":
        invalidate_for_revision(manifest, "landscape")
        manifest["landscape"]["status"] = "revising"
        transition(manifest, "revising_landscape", project=project)
    else:
        invalidate_for_revision(manifest, "portrait")
        manifest["portrait"]["status"] = "revising"
        transition(manifest, "revising_portrait", project=project)
    manifest["updated_at"] = now

    save_json(log_path, log)
    save_json(manifest_path, manifest)
    print(revision_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
