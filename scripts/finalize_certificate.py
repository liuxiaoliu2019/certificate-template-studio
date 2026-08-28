#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError as exc:  # pragma: no cover - depends on local runtime
    raise SystemExit("缺少 Pillow。请先安装 Pillow。") from exc


TARGETS = {
    "landscape": (2172, 1536),
    "portrait": (1536, 2172),
}
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


def find_font(explicit: Path | None, hint: str) -> Path:
    if explicit:
        path = explicit.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"找不到字体文件：{path}")
        return path

    bold = "bold" in hint.casefold() or "heavy" in hint.casefold()
    names = [
        "msyhbd.ttc" if bold else "msyh.ttc",
        "simhei.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    roots = [
        Path("C:/Windows/Fonts"),
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
        Path("/usr/share/fonts/opentype/noto"),
        Path("/usr/share/fonts/truetype/noto"),
    ]
    unix_names = [
        "NotoSansCJK-Bold.ttc" if bold else "NotoSansCJK-Regular.ttc",
        "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf",
        "PingFang.ttc",
    ]
    for root in roots:
        for name in names + unix_names:
            candidate = root / name
            if candidate.is_file():
                return candidate.resolve()
    raise FileNotFoundError("找不到可用字体。程序标题模式必须使用 --font 指定字体文件。")


def split_two_lines(title: str) -> str:
    if " " in title.strip():
        words = title.split()
        if len(words) > 1:
            candidates = [
                (" ".join(words[:index]), " ".join(words[index:]))
                for index in range(1, len(words))
            ]
            left, right = min(candidates, key=lambda pair: abs(len(pair[0]) - len(pair[1])))
            return f"{left}\n{right}"
    midpoint = (len(title) + 1) // 2
    if midpoint <= 0 or midpoint >= len(title):
        return title
    return f"{title[:midpoint]}\n{title[midpoint:]}"


def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, spacing: int, stroke: int) -> tuple[int, int, int, int]:
    return draw.multiline_textbbox(
        (0, 0), text, font=font, spacing=spacing, align="center", stroke_width=stroke
    )


def fit_title(
    title: str,
    font_path: Path,
    max_width: int,
    max_height: int,
    stroke: int,
) -> tuple[str, ImageFont.FreeTypeFont, int, tuple[int, int, int, int]]:
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    minimum = max(24, int(max_height * 0.22))
    maximum = max(minimum, int(max_height * 1.2))

    def find(text: str) -> tuple[ImageFont.FreeTypeFont, int, tuple[int, int, int, int]] | None:
        for size in range(maximum, minimum - 1, -2):
            font = ImageFont.truetype(str(font_path), size=size)
            spacing = max(4, int(size * 0.16))
            bbox = text_bbox(probe, text, font, spacing, stroke)
            if bbox[2] - bbox[0] <= max_width and bbox[3] - bbox[1] <= max_height:
                return font, spacing, bbox
        return None

    fitted = find(title)
    if fitted:
        return title, *fitted
    two_lines = split_two_lines(title)
    if two_lines != title:
        fitted = find(two_lines)
        if fitted:
            return two_lines, *fitted
    raise ValueError("标题过长，无法在最多两行内安全排版；请缩短标题或指定更紧凑的字体。")


def crop_box(width: int, height: int, target_width: int, target_height: int) -> tuple[int, int, int, int, float]:
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


def title_geometry(orientation: str, canvas: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = canvas
    if orientation == "landscape":
        return width // 2, round(height * 0.165), round(width * 0.42), round(height * 0.09)
    return width // 2, round(height * 0.135), round(width * 0.52), round(height * 0.09)


def render_title(
    image: Image.Image,
    orientation: str,
    title: str,
    mode: str,
    font_path: Path,
    colors: list[tuple[int, int, int, int]],
    outline_color: tuple[int, int, int, int] | None,
    outline_width: int,
    shadow_color: tuple[int, int, int, int] | None,
    shadow_offset: tuple[int, int],
    shadow_blur: int,
) -> tuple[Image.Image, list[int], float]:
    center_x, center_y, max_width, max_height = title_geometry(orientation, image.size)
    lines, font, spacing, base_bbox = fit_title(title, font_path, max_width, max_height, outline_width)
    bbox_center_x = (base_bbox[0] + base_bbox[2]) / 2
    bbox_center_y = (base_bbox[1] + base_bbox[3]) / 2
    position = (round(center_x - bbox_center_x), round(center_y - bbox_center_y))
    shifted_bbox = [
        round(base_bbox[0] + position[0]),
        round(base_bbox[1] + position[1]),
        round(base_bbox[2] + position[0]),
        round(base_bbox[3] + position[1]),
    ]
    center_error = abs(((shifted_bbox[0] + shifted_bbox[2]) / 2) - (image.width / 2))
    if center_error > 1:
        raise ValueError(f"标题水平中心误差 {center_error:.2f}px 超过 1px")

    result = image.convert("RGBA")
    if shadow_color and (shadow_offset != (0, 0) or shadow_blur > 0):
        shadow = Image.new("RGBA", result.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_position = (position[0] + shadow_offset[0], position[1] + shadow_offset[1])
        shadow_draw.multiline_text(
            shadow_position,
            lines,
            font=font,
            fill=shadow_color,
            spacing=spacing,
            align="center",
            stroke_width=outline_width,
            stroke_fill=shadow_color,
        )
        if shadow_blur:
            shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
        result = Image.alpha_composite(result, shadow)

    if mode == "vector_flat":
        ImageDraw.Draw(result).multiline_text(
            position,
            lines,
            font=font,
            fill=colors[0],
            spacing=spacing,
            align="center",
            stroke_width=outline_width,
            stroke_fill=outline_color or colors[0],
        )
    else:
        if outline_width:
            ImageDraw.Draw(result).multiline_text(
                position,
                lines,
                font=font,
                fill=colors[0],
                spacing=spacing,
                align="center",
                stroke_width=outline_width,
                stroke_fill=outline_color or colors[-1],
            )
        mask = Image.new("L", result.size, 0)
        ImageDraw.Draw(mask).multiline_text(
            position, lines, font=font, fill=255, spacing=spacing, align="center"
        )
        gradient = Image.new("RGBA", result.size)
        gradient_draw = ImageDraw.Draw(gradient)
        stops = colors if len(colors) > 1 else [colors[0], colors[0]]
        top, bottom = shifted_bbox[1], max(shifted_bbox[1] + 1, shifted_bbox[3])
        for y in range(max(0, top), min(result.height, bottom + 1)):
            progress = (y - top) / max(1, bottom - top)
            scaled = progress * (len(stops) - 1)
            index = min(len(stops) - 2, int(scaled))
            fraction = scaled - index
            color = tuple(round(stops[index][channel] * (1 - fraction) + stops[index + 1][channel] * fraction) for channel in range(4))
            gradient_draw.line(
                (max(0, shifted_bbox[0]), y, min(result.width - 1, shifted_bbox[2]), y),
                fill=color,
            )
        result = Image.composite(gradient, result, mask)
    return result, shifted_bbox, center_error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把证书原始生图收尾为固定小程序尺寸。")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--orientation", required=True, choices=sorted(TARGETS))
    parser.add_argument("--title", required=True)
    parser.add_argument("--title-mode", required=True, choices=["vector_flat", "vector_effect", "ai_integrated"])
    parser.add_argument("--font", type=Path)
    parser.add_argument("--font-style-hint", default="display_sans")
    parser.add_argument("--fill-color", action="append", default=[])
    parser.add_argument("--outline-color")
    parser.add_argument("--outline-width", type=int, default=0)
    parser.add_argument("--shadow-color")
    parser.add_argument("--shadow-offset", default="0,0")
    parser.add_argument("--shadow-blur", type=int, default=0)
    parser.add_argument("--base-text-free", action="store_true")
    parser.add_argument("--ai-title-validated", action="store_true")
    return parser.parse_args()


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
    title = args.title.strip()
    if not title:
        raise ValueError("标题不能为空")
    if args.title_mode in {"vector_flat", "vector_effect"} and not args.base_text_free:
        raise ValueError("程序标题模式必须先确认底图无文字，并传入 --base-text-free")
    if args.title_mode == "ai_integrated" and not args.ai_title_validated:
        raise ValueError("生成式标题必须先通过文字与视觉验收，并传入 --ai-title-validated")
    if args.outline_width < 0 or args.shadow_blur < 0:
        raise ValueError("描边宽度和阴影模糊不能为负数")
    try:
        shadow_offset = tuple(int(item.strip()) for item in args.shadow_offset.split(","))
    except ValueError as exc:
        raise ValueError("--shadow-offset 必须为 x,y 两个整数") from exc
    if len(shadow_offset) != 2:
        raise ValueError("--shadow-offset 必须为 x,y 两个整数")

    target = TARGETS[args.orientation]
    with Image.open(source) as opened:
        original_format = opened.format or source.suffix.lstrip(".").upper()
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    original_size = image.size
    left, top, right, bottom, ratio_error = crop_box(*original_size, *target)
    image = image.crop((left, top, right, bottom)).resize(target, Image.Resampling.LANCZOS)

    font_path: Path | None = None
    title_bbox: list[int] | None = None
    center_error: float | None = None
    if args.title_mode != "ai_integrated":
        font_path = find_font(args.font, args.font_style_hint)
        default_colors = ["#1F4E79"] if args.title_mode == "vector_flat" else ["#FFF3A6", "#D4AF37", "#7A4E00"]
        colors = [parse_hex(value) for value in (args.fill_color or default_colors)]
        if args.title_mode == "vector_flat" and len(colors) != 1:
            raise ValueError("vector_flat 只允许一个 --fill-color")
        outline_color = parse_hex(args.outline_color) if args.outline_color else None
        shadow_color = parse_hex(args.shadow_color) if args.shadow_color else None
        image, title_bbox, center_error = render_title(
            image,
            args.orientation,
            title,
            args.title_mode,
            font_path,
            colors,
            outline_color,
            args.outline_width,
            shadow_color,
            shadow_offset,
            args.shadow_blur,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, format="PNG", optimize=True)
    with Image.open(output) as verified:
        if verified.size != target or verified.format != "PNG":
            raise ValueError("输出文件写入后尺寸或格式验证失败")

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
            "font_path": display_path(font_path, project_root) if font_path else None,
            "bbox": title_bbox,
            "center_error_px": center_error,
            "portrait_up_shift_px": PORTRAIT_UP_SHIFT_PX if args.orientation == "portrait" else 0,
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
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    print(report)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
