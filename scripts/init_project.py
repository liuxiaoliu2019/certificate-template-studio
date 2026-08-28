#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from _common import safe_slug, save_json, utc_now


PROJECT_DIRS = [
    "input",
    "controls",
    "analysis",
    "analysis/character_refs",
    "styles",
    "concepts",
    "selected",
    "revisions",
    "portrait",
    "derivatives",
    "prompts",
    "configs",
    "scores",
    "logs",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化证书模板项目，不生成图片。")
    parser.add_argument("--name", required=True, help="教材或项目显示名，例如 SunnyFarmCourse")
    parser.add_argument("--root", required=True, type=Path, help="新项目的父目录")
    parser.add_argument("--cover", required=True, type=Path, help="教材封面文件")
    parser.add_argument("--project-id", help="可选安全项目 ID；默认由 name 生成")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cover = args.cover.expanduser().resolve()
    if not cover.is_file():
        raise FileNotFoundError(f"找不到教材封面：{cover}")

    project_id = safe_slug(args.project_id or args.name)
    root = args.root.expanduser().resolve()
    project = root / project_id
    manifest_path = project / "configs" / "project_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"项目已初始化，未做覆盖：{project}")
    if project.exists() and any(project.iterdir()):
        raise FileExistsError(f"目标目录非空，未做覆盖：{project}")

    for directory in PROJECT_DIRS:
        (project / directory).mkdir(parents=True, exist_ok=True)

    cover_target = project / "input" / f"cover{cover.suffix.lower()}"
    shutil.copy2(cover, cover_target)

    skill_root = Path(__file__).resolve().parents[1]
    control_source = skill_root / "assets" / "controls"
    for name in ("landscape_v3.png", "portrait_v3.png"):
        source = control_source / name
        if not source.is_file():
            raise FileNotFoundError(f"Skill 控制模板缺失：{source}")
        shutil.copy2(source, project / "controls" / name)

    now = utc_now()
    generation_config = {
        "schema_version": "1.3",
        "candidate_count": 3,
        "control_mode": "soft",
        "control_templates": {
            "landscape": "controls/landscape_v3.png",
            "portrait": "controls/portrait_v3.png",
        },
        "zone_strengths": {
            "main_decoration": 80,
            "secondary_decoration": 50,
            "transition": 20,
            "signature_quiet_zone": 12,
            "body_safe_zone": 8,
        },
        "title": {
            "value": None,
            "source": "manual_user_input",
            "only_readable_text": True,
            "horizontal_center_x_percent": 50,
            "portrait_up_shift_cm": 1.5,
            "portrait_up_shift_canvas_percent": 5.05,
            "portrait_up_shift_output_px": 110,
            "render_mode": "auto",
            "allowed_render_modes": ["vector_flat", "vector_effect", "ai_integrated"],
            "forbidden_containers": ["banner", "ribbon", "card", "badge", "title_frame"],
        },
        "outputs": {
            "landscape": {"width_px": 2172, "height_px": 1536, "format": "PNG", "purpose": "mini_program"},
            "portrait": {"width_px": 1536, "height_px": 2172, "format": "PNG", "purpose": "mini_program"},
        },
        "revision_policy": {
            "preserve_history": True,
            "allow_rollback": True,
            "levels": [1, 2, 3],
        },
        "identity_policy": {
            "scope": "all_human_and_animal_characters",
            "appearance_policy": "optional_but_faithful_when_used",
            "minimum_score": 85,
            "max_auto_corrections": 2,
            "reference_dir": "analysis/character_refs",
        },
        "concept_roles": ["cover_character_led", "balanced_translation", "frame_led"],
        "style_engine": {
            "enabled": True,
            "library_size": 7,
            "recommendation_count": 3,
            "minimum_compatibility_score": 70,
            "weights": {
                "illustration_style": 35,
                "core_elements": 25,
                "color_palette": 20,
                "mood": 15,
                "composition": 5,
            },
            "require_distinct_families": True,
            "minimum_pairwise_parameter_differences": 3,
        },
        "multi_title_policy": {
            "reuse_approved_master_by_default": True,
            "explore_three_only_on_explicit_request": True,
        },
    }
    manifest = {
        "schema_version": "1.4",
        "selected_mode": "textbook_cover",
        "project_id": project_id,
        "textbook_key": args.name,
        "created_at": now,
        "updated_at": now,
        "source_cover": cover_target.relative_to(project).as_posix(),
        "style_dna_path": "analysis/style_dna.json",
        "character_identity_path": "analysis/character_identity.json",
        "character_reference_dir": "analysis/character_refs",
        "current_title": None,
        "output_contract": {
            "landscape": {"width_px": 2172, "height_px": 1536},
            "portrait": {"width_px": 1536, "height_px": 2172},
            "format": "PNG",
            "purpose": "mini_program",
            "ratio_tolerance_percent": 0.5,
        },
        "workflow": {"stage": "initialized"},
        "controls": {
            "landscape": "controls/landscape_v3.png",
            "portrait": "controls/portrait_v3.png",
            "mode": "soft",
            "zone_strengths": {"Z80": 80, "Z50": 50, "Z20": 20, "Z12": 12, "Z08": 8},
        },
        "landscape": {
            "status": "not_started",
            "concepts": [],
            "selected_file": None,
            "active_revision_id": None,
            "finalization_report": None,
        },
        "portrait": {
            "status": "blocked",
            "concepts": [],
            "selected_file": None,
            "active_revision_id": None,
            "finalization_report": None,
        },
        "style_engine": {
            "status": "not_started",
            "recommendation_path": None,
            "candidate_profiles": [],
            "selected_profile": None,
            "approved_profile": None,
            "master_profile_path": None,
            "style_lock": "unlocked",
        },
        "master": {"landscape": None, "portrait": None, "title": None, "style_profile": None},
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

    save_json(project / "configs" / "generation_config.json", generation_config)
    save_json(manifest_path, manifest)
    save_json(project / "revisions" / "revision_log.json", revision_log)
    (project / "logs" / "run_log.md").write_text(
        f"# Run Log\n\n- {now} 项目初始化；等待 Style DNA 分析、用户标题与风格推荐。\n", encoding="utf-8"
    )
    print(project)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
