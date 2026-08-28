#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import load_json, project_file, save_json, sha256_file
from cache_engine import build_source_fingerprint

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover - depends on local runtime
    raise SystemExit("缺少 Pillow。请先安装 Pillow，再运行角色原图裁切。") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按身份档案从教材封面确定性裁切角色参考，不做重绘。")
    parser.add_argument("project", type=Path, help="证书模板项目目录")
    parser.add_argument(
        "--registry",
        default="analysis/character_identity.json",
        help="项目内角色身份档案路径",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.015,
        help="相对整图宽高的额外留边，默认 0.015",
    )
    parser.add_argument("--force", action="store_true", help="覆盖已经存在的裁切文件")
    return parser.parse_args()


def pixel_box(region: dict, width: int, height: int, padding: float) -> tuple[int, int, int, int]:
    x = float(region["x"])
    y = float(region["y"])
    w = float(region["width"])
    h = float(region["height"])
    if min(x, y, w, h) < 0 or w <= 0 or h <= 0 or x + w > 1 or y + h > 1:
        raise ValueError(f"source_region 必须位于 0–1 范围内：{region}")
    if not 0 <= padding <= 0.1:
        raise ValueError("--padding 必须位于 0–0.1")
    left = max(0, round((x - padding) * width))
    top = max(0, round((y - padding) * height))
    right = min(width, round((x + w + padding) * width))
    bottom = min(height, round((y + h + padding) * height))
    if right <= left or bottom <= top:
        raise ValueError(f"裁切区域为空：{region}")
    return left, top, right, bottom


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"找不到项目目录：{project}")

    registry_path = project_file(project, args.registry)
    registry = load_json(registry_path)
    cover_path = project_file(project, registry["source_cover"])
    if not cover_path.is_file():
        raise FileNotFoundError(f"找不到身份档案中的封面：{cover_path}")

    characters = registry.get("characters", [])
    with Image.open(cover_path) as opened:
        source = ImageOps.exif_transpose(opened).convert("RGB")
        for character in characters:
            target = project_file(project, character["reference_crop"])
            expected_dir = (project / "analysis" / "character_refs").resolve()
            if target.parent != expected_dir:
                raise ValueError(f"角色裁切必须保存到 analysis/character_refs：{target}")
            if target.exists() and not args.force:
                raise FileExistsError(f"裁切已存在；如需重建请使用 --force：{target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            box = pixel_box(character["source_region"], source.width, source.height, args.padding)
            source.crop(box).save(target, format="PNG", optimize=True)
            character["reference_crop_sha256"] = sha256_file(target)
            print(f"{character['character_id']}: {target}")
    registry["source_cover_sha256"] = sha256_file(cover_path)
    save_json(registry_path, registry)
    fingerprint = build_source_fingerprint(
        project,
        mode="textbook_cover",
        source=registry["source_cover"],
        characters={item["character_id"]: item["reference_crop"] for item in characters},
    )
    save_json(project / "configs" / "source_fingerprint.json", fingerprint)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
