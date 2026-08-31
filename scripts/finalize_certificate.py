#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover - depends on local runtime
    raise SystemExit("缺少 Pillow。请先安装 requirements.txt 中的运行依赖。") from exc

from font_registry import FontRegistry
from schema_runtime import validate_document
from title_planner import LAYOUT_FAMILIES, build_plan, normalize_title
from title_renderer import render_title_plan
from metrics import MetricsRecorder


TARGETS = {"landscape": (2172, 1536), "portrait": (1536, 2172)}
RATIO_TOLERANCE_PERCENT = 0.5
PORTRAIT_UP_SHIFT_PX = 110


def parse_hex(value: str) -> tuple[int, int, int, int]:
    text = value.strip().lstrip("#")
    if len(text) not in {6, 8}:
        raise ValueError(f"颜色必须为 #RRGGBB 或 #RRGGBBAA：{value}")
    try:
        parts = tuple(int(text[index : index + 2], 16) for index in range(0, len(text), 2))
    except ValueError as exc:
        raise ValueError(f"颜色格式无效：{value}") from exc
    return (*parts, 255) if len(parts) == 3 else parts


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def display_path(path: Path, project_root: Path | None) -> str:
    resolved = path.resolve()
    if project_root:
        try:
            return resolved.relative_to(project_root.resolve()).as_posix()
        except ValueError:
            pass
    return str(resolved)


def display_font_path(path: Path, source: str, project_root: Path | None) -> str:
    if source == "bundled":
        skill_root = Path(__file__).resolve().parents[1]
        return path.resolve().relative_to(skill_root).as_posix()
    return display_path(path, project_root)


def crop_box(
    width: int,
    height: int,
    target_width: int,
    target_height: int,
) -> tuple[int, int, int, int, float]:
    source_ratio = width / height
    target_ratio = target_width / target_height
    error = abs(source_ratio - target_ratio) / target_ratio * 100
    if error > RATIO_TOLERANCE_PERCENT:
        raise ValueError(
            f"原图宽高比误差 {error:.4f}% 超过 {RATIO_TOLERANCE_PERCENT:.1f}%，必须重新生成，禁止强行裁切。"
        )
    if source_ratio > target_ratio:
        cropped_width = max(1, round(height * target_ratio))
        left = (width - cropped_width) // 2
        box = (left, 0, left + cropped_width, height)
    else:
        cropped_height = max(1, round(width / target_ratio))
        top = (height - cropped_height) // 2
        box = (0, top, width, top + cropped_height)
    return *box, error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把证书底图收尾为固定小程序尺寸并渲染唯一主标题。")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--orientation", required=True, choices=sorted(TARGETS))
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--title-mode", required=True, choices=["vector_flat", "vector_effect", "ai_integrated"]
    )
    parser.add_argument("--title-plan", type=Path)
    parser.add_argument("--template-dna", type=Path, help="模板模式的非文字标题结构锁")
    parser.add_argument("--layout-family", choices=LAYOUT_FAMILIES)
    parser.add_argument("--style-family")
    parser.add_argument("--font", type=Path)
    parser.add_argument("--font-style-hint", default="display_sans", help=argparse.SUPPRESS)
    parser.add_argument("--fill-color", action="append", default=[])
    parser.add_argument("--outline-color")
    parser.add_argument("--outline-width", type=int)
    parser.add_argument("--shadow-color")
    parser.add_argument("--shadow-offset", default="0,0")
    parser.add_argument("--shadow-blur", type=int, default=0)
    parser.add_argument("--base-text-free", action="store_true")
    parser.add_argument("--ai-title-validated", action="store_true")
    parser.add_argument("--metrics", type=Path)
    return parser.parse_args()


def load_or_build_plan(
    args: argparse.Namespace,
    title: str,
    output: Path,
    report: Path,
    template_dna: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    if args.title_plan:
        path = args.title_plan.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"找不到标题布局计划：{path}")
        plan = json.loads(path.read_text(encoding="utf-8"))
        validate_document(plan, "title_layout_plan.schema.json")
    else:
        plan = build_plan(
            title,
            args.orientation,
            style_family=args.style_family,
            layout_family=args.layout_family,
            render_mode=args.title_mode,
            template_dna=template_dna,
        )
        path = report.with_name(f"{output.stem}.title-layout.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if plan["orientation"] != args.orientation:
        raise ValueError("标题布局计划方向与 --orientation 不一致")
    if plan["render_mode"] != args.title_mode:
        raise ValueError("标题布局计划渲染模式与 --title-mode 不一致")
    if plan["normalized_title"] != normalize_title(title):
        raise ValueError("标题布局计划内容与 --title 不一致")
    return plan, path


def main() -> int:
    args = parse_args()
    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    report = (args.report or output.with_suffix(".finalization.json")).expanduser().resolve()
    project_root = args.project_root.expanduser().resolve() if args.project_root else None
    if not source.is_file():
        raise FileNotFoundError(f"找不到输入图片：{source}")
    if output.suffix.lower() != ".png":
        raise ValueError("正式成品必须使用 .png 扩展名")
    title = normalize_title(args.title)
    template_dna: dict[str, Any] | None = None
    if args.template_dna:
        dna_path = args.template_dna.expanduser().resolve()
        if not dna_path.is_file():
            raise FileNotFoundError(f"找不到 Template DNA：{dna_path}")
        template_dna = json.loads(dna_path.read_text(encoding="utf-8"))
        validate_document(template_dna, "template_dna.schema.json")
        title_system = template_dna.get("title_system")
        if title_system:
            # Template mode uses the source title material as the authority.  An
            # old generic --title-mode must not turn a flat native title into gold.
            args.title_mode = title_system["visual_treatment"]["render_mode"]
    if args.title_mode in {"vector_flat", "vector_effect"} and not args.base_text_free:
        raise ValueError("程序标题模式必须先确认底图无文字，并传入 --base-text-free")
    if args.title_mode == "ai_integrated" and not args.ai_title_validated:
        raise ValueError("生成式标题必须先通过文字与视觉验收，并传入 --ai-title-validated")
    if (args.outline_width is not None and args.outline_width < 0) or args.shadow_blur < 0:
        raise ValueError("描边宽度和阴影模糊不能为负数")
    try:
        offset_items = tuple(int(item.strip()) for item in args.shadow_offset.split(","))
    except ValueError as exc:
        raise ValueError("--shadow-offset 必须为 x,y 两个整数") from exc
    if len(offset_items) != 2:
        raise ValueError("--shadow-offset 必须为 x,y 两个整数")
    shadow_offset = (offset_items[0], offset_items[1])

    target = TARGETS[args.orientation]
    with Image.open(source) as opened:
        original_format = opened.format or source.suffix.lstrip(".").upper()
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    original_size = image.size
    left, top, right, bottom, ratio_error = crop_box(*original_size, *target)
    image = image.crop((left, top, right, bottom)).resize(target, Image.Resampling.LANCZOS)

    title_bbox: list[int] | None = None
    center_error: float | None = None
    title_plan: dict[str, Any] | None = None
    title_plan_path: Path | None = None
    title_plan_sha256: str | None = None
    font_evidence: list[dict[str, Any]] = []
    if args.title_mode != "ai_integrated":
        title_plan, title_plan_path = load_or_build_plan(
            args, title, output, report, template_dna=template_dna
        )
        title_plan_sha256 = sha256_file(title_plan_path)
        default_colors = (
            ["#1F4E79"]
            if args.title_mode == "vector_flat"
            else ["#FFF3A6", "#D4AF37", "#7A4E00"]
        )
        colors = [parse_hex(value) for value in (args.fill_color or default_colors)]
        if args.title_mode == "vector_flat" and len(colors) != 1:
            raise ValueError("vector_flat 只允许一个 --fill-color")
        rendered = render_title_plan(
            image,
            title_plan,
            registry=FontRegistry(),
            user_font=args.font,
            colors=colors,
            outline_color=parse_hex(args.outline_color) if args.outline_color else None,
            outline_width=args.outline_width,
            shadow_color=parse_hex(args.shadow_color) if args.shadow_color else None,
            shadow_offset=shadow_offset,
            shadow_blur=args.shadow_blur,
        )
        image = rendered.image
        title_bbox = rendered.bbox
        center_error = rendered.center_error_px
        font_evidence = rendered.font_evidence

    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, format="PNG", optimize=True)
    with Image.open(output) as verified:
        if verified.size != target or verified.format != "PNG":
            raise ValueError("输出文件写入后尺寸或格式验证失败")

    public_font_evidence = [
        {
            **item,
            "path": display_font_path(Path(str(item["path"])), str(item["source"]), project_root),
        }
        for item in font_evidence
    ]
    font_path = public_font_evidence[0]["path"] if public_font_evidence else None
    payload = {
        "schema_version": "1.0",
        "status": "passed",
        "orientation": args.orientation,
        "title_render_mode": args.title_mode,
        "input": {
            "path": display_path(source, project_root),
            "width_px": original_size[0],
            "height_px": original_size[1],
            "format": original_format,
        },
        "output": {
            "path": display_path(output, project_root),
            "width_px": target[0],
            "height_px": target[1],
            "format": "PNG",
            "sha256": sha256_file(output),
        },
        "ratio_error_percent": round(ratio_error, 6),
        "crop": {"left": left, "top": top, "right": right, "bottom": bottom},
        "title": {
            "value": title,
            "font_path": font_path,
            "bbox": title_bbox,
            "center_error_px": center_error,
            "portrait_up_shift_px": PORTRAIT_UP_SHIFT_PX if args.orientation == "portrait" else 0,
            "layout_family": title_plan["layout_family"] if title_plan else None,
            "layout_plan_path": display_path(title_plan_path, project_root) if title_plan_path else None,
            "layout_plan_sha256": title_plan_sha256,
            "font_evidence": public_font_evidence,
        },
        "checks": {
            "ratio": True,
            "dimensions": True,
            "png": True,
            "no_stretch": True,
            "base_text_free": args.base_text_free if args.title_mode != "ai_integrated" else None,
            "title_validated": True,
            "color_policy": {
                "vector_flat": "flat_deterministic",
                "vector_effect": "effect_deterministic",
                "ai_integrated": "visual_review",
            }[args.title_mode],
        },
        "created_at": utc_now(),
    }
    validate_document(payload, "finalization_report.schema.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.metrics:
        MetricsRecorder(args.metrics).increment(
            "visual_review_calls",
            stage="finalization",
            orientation=args.orientation,
            path=display_path(report, project_root),
        )
    print(output)
    print(report)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
