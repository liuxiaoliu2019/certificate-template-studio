#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from _common import load_json, project_file, relative_posix, save_json, sha256_file, utc_now


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="保存模板双向项目修订并支持非破坏性回退。")
    parser.add_argument("project", type=Path)
    parser.add_argument("--orientation", required=True, choices=["landscape", "portrait"])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--artifact", type=Path)
    mode.add_argument("--rollback", metavar="REVISION_ID")
    parser.add_argument("--level", type=int, choices=[1, 2, 3])
    parser.add_argument("--source", help="项目内基础文件或 revision id")
    parser.add_argument("--feedback", action="append", required=True)
    parser.add_argument("--changed-param", action="append", default=[])
    parser.add_argument("--locked-param", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    manifest_path = project / "configs" / "template_project_manifest.json"
    log_path = project / "revisions" / "revision_log.json"
    if not manifest_path.is_file() or not log_path.is_file():
        raise FileNotFoundError("项目缺少模板 manifest 或 revision_log")
    manifest = load_json(manifest_path)
    log = load_json(log_path)
    source_orientation = manifest["source_orientation"]
    opposite = manifest["opposite_orientation"]
    if args.orientation == opposite and manifest[source_orientation]["status"] != "approved":
        raise ValueError("源方向未批准，不能记录另一方向修订")

    feedback = [item.strip() for item in args.feedback if item.strip()]
    if not feedback:
        raise ValueError("反馈不能为空")
    before = manifest[args.orientation]["status"]
    log["sequence"] += 1
    revision_id = f"r{log['sequence']:03d}"
    now = utc_now()

    if args.artifact:
        if args.level is None:
            raise ValueError("保存新修订时必须提供 --level 1/2/3")
        source_file = args.artifact.expanduser().resolve()
        if not source_file.is_file():
            raise FileNotFoundError(f"找不到修订图片：{source_file}")
        suffix = source_file.suffix.lower() or ".png"
        destination = project / "revisions" / f"{args.orientation}_{revision_id}{suffix}"
        if destination.exists():
            raise FileExistsError(f"修订目标已存在，未覆盖：{destination}")
        shutil.copy2(source_file, destination)
        artifact = relative_posix(destination, project)
        entry = {
            "revision_id": revision_id,
            "orientation": args.orientation,
            "action": "revision",
            "level": args.level,
            "source": args.source,
            "artifact": artifact,
            "sha256": sha256_file(destination),
            "feedback": feedback,
            "rollback_to": None,
            "created_at": now,
            "style_family": None,
            "style_profile": None,
            "changed_parameters": [item.strip() for item in args.changed_param if item.strip()],
            "locked_parameters": [item.strip() for item in args.locked_param if item.strip()],
            "approval_state_before": before,
            "approval_state_after": "awaiting_approval",
        }
        log["active_by_orientation"][args.orientation] = revision_id
        manifest[args.orientation]["active_revision_id"] = revision_id
        manifest[args.orientation]["selected_file"] = artifact
    else:
        target = next(
            (
                item for item in log["entries"]
                if item["revision_id"] == args.rollback
                and item["orientation"] == args.orientation
                and item["action"] == "revision"
            ),
            None,
        )
        if target is None or not target.get("artifact"):
            raise ValueError(f"找不到可回退的 {args.orientation} revision：{args.rollback}")
        project_file(project, target["artifact"])
        entry = {
            "revision_id": revision_id,
            "orientation": args.orientation,
            "action": "rollback",
            "level": None,
            "source": log["active_by_orientation"].get(args.orientation),
            "artifact": None,
            "sha256": None,
            "feedback": feedback,
            "rollback_to": args.rollback,
            "created_at": now,
            "style_family": None,
            "style_profile": None,
            "changed_parameters": [],
            "locked_parameters": target.get("locked_parameters", []),
            "approval_state_before": before,
            "approval_state_after": "awaiting_approval",
        }
        log["active_by_orientation"][args.orientation] = args.rollback
        manifest[args.orientation]["active_revision_id"] = args.rollback
        manifest[args.orientation]["selected_file"] = target["artifact"]

    log["entries"].append(entry)
    manifest[args.orientation]["status"] = "awaiting_approval"
    manifest["master"][args.orientation] = None
    if args.orientation == source_orientation:
        manifest[opposite]["status"] = "stale" if manifest[opposite]["selected_file"] else "blocked"
        manifest["master"][opposite] = None
    manifest["workflow"]["stage"] = "revising"
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
