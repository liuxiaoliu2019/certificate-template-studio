#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from _common import safe_slug, save_json, utc_now

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover - depends on local runtime
    raise SystemExit("缺少 Pillow。请先安装 Pillow，再初始化模板双向项目。") from exc


PROJECT_DIRS = [
    "input",
    "controls",
    "analysis",
    "analysis/character_refs",
    "landscape",
    "portrait",
    "selected",
    "revisions",
    "scores",
    "prompts",
    "configs",
    "logs",
    "derivatives",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化横竖双向证书模板项目，不生成图片。")
    parser.add_argument("--name", required=True, help="项目显示名")
    parser.add_argument("--root", required=True, type=Path, help="新项目父目录")
    parser.add_argument("--template", required=True, type=Path, help="横版或竖版证书模板")
    parser.add_argument("--project-id", help="可选安全项目 ID；默认由 name 生成")
    parser.add_argument(
        "--source-orientation",
        choices=["landscape", "portrait"],
        help="仅正方形或方向无法自动判断时使用",
    )
    return parser.parse_args()


def detect_orientation(path: Path, override: str | None) -> tuple[str, int, int]:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened)
        width, height = image.size
    if width == height:
        if not override:
            raise ValueError("模板为正方形，必须使用 --source-orientation 明确指定 landscape 或 portrait")
        return override, width, height
    detected = "landscape" if width > height else "portrait"
    if override and override != detected:
        raise ValueError(f"指定方向 {override} 与图像尺寸检测结果 {detected} 冲突")
    return detected, width, height


def main() -> int:
    args = parse_args()
    template = args.template.expanduser().resolve()
    if not template.is_file():
        raise FileNotFoundError(f"找不到证书模板：{template}")
    orientation, width, height = detect_orientation(template, args.source_orientation)
    opposite = "portrait" if orientation == "landscape" else "landscape"

    project_id = safe_slug(args.project_id or args.name)
    root = args.root.expanduser().resolve()
    project = root / project_id
    manifest_path = project / "configs" / "template_project_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"项目已初始化，未做覆盖：{project}")
    if project.exists() and any(project.iterdir()):
        raise FileExistsError(f"目标目录非空，未做覆盖：{project}")

    for directory in PROJECT_DIRS:
        (project / directory).mkdir(parents=True, exist_ok=True)

    source_target = project / "input" / f"source_template{template.suffix.lower()}"
    shutil.copy2(template, source_target)
    skill_root = Path(__file__).resolve().parents[1]
    for name in ("landscape_v3.png", "portrait_v3.png"):
        source = skill_root / "assets" / "controls" / name
        if not source.is_file():
            raise FileNotFoundError(f"Skill 控制模板缺失：{source}")
        shutil.copy2(source, project / "controls" / name)

    now = utc_now()
    states = {
        "landscape": {
            "status": "ready" if orientation == "landscape" else "blocked",
            "concepts": [],
            "selected_file": None,
            "active_revision_id": None,
            "finalization_report": None,
        },
        "portrait": {
            "status": "ready" if orientation == "portrait" else "blocked",
            "concepts": [],
            "selected_file": None,
            "active_revision_id": None,
            "finalization_report": None,
        },
    }
    manifest = {
        "schema_version": "1.2",
        "mode": "template_bidirectional",
        "selected_mode": "template_bidirectional",
        "project_id": project_id,
        "display_name": args.name,
        "created_at": now,
        "updated_at": now,
        "source_template": source_target.relative_to(project).as_posix(),
        "source_orientation": orientation,
        "opposite_orientation": opposite,
        "source_dimensions": {"width_px": width, "height_px": height},
        "template_dna_path": "analysis/template_dna.json",
        "current_title": None,
        "output_contract": {
            "landscape": {"width_px": 2172, "height_px": 1536},
            "portrait": {"width_px": 1536, "height_px": 2172},
            "format": "PNG",
            "purpose": "mini_program",
            "ratio_tolerance_percent": 0.5,
        },
        "workflow": {"stage": "initialized"},
        "source_lock": {"status": "source_locked", "user_supplied": True},
        "controls": {
            "landscape": "controls/landscape_v3.png",
            "portrait": "controls/portrait_v3.png",
            "mode": "soft",
        },
        "landscape": states["landscape"],
        "portrait": states["portrait"],
        "master": {"landscape": None, "portrait": None, "title": None, "template_dna": None},
        "derivatives": [],
        "approvals": [],
        "revision_log_path": "revisions/revision_log.json",
    }
    revision_log = {
        "schema_version": "1.1",
        "project_id": project_id,
        "sequence": 0,
        "active_by_orientation": {"landscape": None, "portrait": None},
        "entries": [],
    }
    save_json(manifest_path, manifest)
    save_json(project / "revisions" / "revision_log.json", revision_log)
    (project / "logs" / "run_log.md").write_text(
        f"# Run Log\n\n- {now} 模板双向项目初始化；源方向为 {orientation}；等待 Template DNA 分析。\n",
        encoding="utf-8",
    )
    print(project)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
