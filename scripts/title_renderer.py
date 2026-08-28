from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from font_registry import FontRegistry, ResolvedFont
from schema_runtime import validate_document


RGBA = tuple[int, int, int, int]


@dataclass(frozen=True)
class TitleRenderResult:
    image: Image.Image
    bbox: list[int]
    center_error_px: float
    font_evidence: list[dict[str, Any]]


def _load_font(path: Path, size: int, weight: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), size=max(8, size))
    try:
        axes = font.get_variation_axes()
        if len(axes) == 1:
            minimum = int(axes[0]["minimum"])
            maximum = int(axes[0]["maximum"])
            font.set_variation_by_axes([max(minimum, min(maximum, weight))])
    except (AttributeError, OSError, ValueError):
        pass
    return font


def _advance(font: ImageFont.FreeTypeFont, character: str) -> float:
    try:
        return font.getlength(character)
    except AttributeError:  # pragma: no cover - compatibility with older Pillow
        bbox = font.getbbox(character)
        return bbox[2] - bbox[0]


def _tracked_width(text: str, font: ImageFont.FreeTypeFont, tracking_px: int) -> int:
    if not text:
        return 0
    return round(sum(_advance(font, character) for character in text) + tracking_px * (len(text) - 1))


def _draw_tracked(
    layer: Image.Image,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    tracking_px: int,
    fill: RGBA,
    *,
    stroke_width: int = 0,
    stroke_fill: RGBA | None = None,
    palette: list[RGBA] | None = None,
) -> tuple[int, int, int, int]:
    draw = ImageDraw.Draw(layer)
    width = _tracked_width(text, font, tracking_px)
    x = xy[0] - width / 2
    y = xy[1]
    boxes: list[tuple[int, int, int, int]] = []
    for index, character in enumerate(text):
        color = palette[index % len(palette)] if palette else fill
        bbox = draw.textbbox(
            (x, y),
            character,
            font=font,
            anchor="lt",
            stroke_width=stroke_width,
        )
        draw.text(
            (x, y),
            character,
            font=font,
            anchor="lt",
            fill=color,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill or color,
        )
        boxes.append(bbox)
        x += _advance(font, character) + tracking_px
    if not boxes:
        return (round(xy[0]), round(y), round(xy[0]), round(y))
    return (
        min(item[0] for item in boxes),
        min(item[1] for item in boxes),
        max(item[2] for item in boxes),
        max(item[3] for item in boxes),
    )


def _text_mask(
    size: tuple[int, int],
    center: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    tracking_px: int,
) -> Image.Image:
    mask_rgba = Image.new("RGBA", size, (0, 0, 0, 0))
    _draw_tracked(mask_rgba, center, text, font, tracking_px, (255, 255, 255, 255))
    return mask_rgba.getchannel("A")


def _gradient(size: tuple[int, int], top: int, bottom: int, colors: list[RGBA]) -> Image.Image:
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(result)
    stops = colors if len(colors) > 1 else [colors[0], colors[0]]
    low, high = max(0, top), min(size[1] - 1, max(top + 1, bottom))
    for y in range(low, high + 1):
        progress = (y - low) / max(1, high - low)
        scaled = progress * (len(stops) - 1)
        index = min(len(stops) - 2, int(scaled))
        fraction = scaled - index
        color = tuple(
            round(stops[index][channel] * (1 - fraction) + stops[index + 1][channel] * fraction)
            for channel in range(4)
        )
        draw.line((0, y, size[0] - 1, y), fill=color)
    return result


def _draw_effect_line(
    core: Image.Image,
    shadow: Image.Image,
    center: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    tracking_px: int,
    colors: list[RGBA],
    outline_color: RGBA,
    outline_width: int,
    shadow_color: RGBA,
    shadow_offset: tuple[int, int],
    shadow_blur: int,
) -> tuple[int, int, int, int]:
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    raw = probe.textbbox((0, 0), text, font=font, stroke_width=outline_width)
    height = max(1, raw[3] - raw[1])
    top = round(center[1])
    bottom = top + height + outline_width * 2
    bbox = _draw_tracked(
        core,
        center,
        text,
        font,
        tracking_px,
        colors[0],
        stroke_width=outline_width,
        stroke_fill=outline_color,
    )
    mask = _text_mask(core.size, center, text, font, tracking_px)
    core.alpha_composite(Image.composite(_gradient(core.size, top, bottom, colors), Image.new("RGBA", core.size), mask))
    if shadow_color[3] and (shadow_offset != (0, 0) or shadow_blur):
        shadow_mask = _text_mask(
            core.size,
            (center[0] + shadow_offset[0], center[1] + shadow_offset[1]),
            text,
            font,
            tracking_px,
        )
        if shadow_blur:
            shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(shadow_blur))
        shadow_color_layer = Image.new("RGBA", core.size, shadow_color)
        shadow.alpha_composite(Image.composite(shadow_color_layer, Image.new("RGBA", core.size), shadow_mask))
    return bbox


def _ribbon_polygon(center_x: int, center_y: int, width: int, height: int) -> list[tuple[int, int]]:
    left, right = center_x - width // 2, center_x + width // 2
    top, bottom = center_y - height // 2, center_y + height // 2
    tail = max(20, round(height * 0.42))
    notch = max(12, round(height * 0.24))
    return [
        (left - tail, top + notch),
        (left, top),
        (right, top),
        (right + tail, top + notch),
        (right + tail - notch, center_y),
        (right + tail, bottom - notch),
        (right, bottom),
        (left, bottom),
        (left - tail, bottom - notch),
        (left - tail + notch, center_y),
    ]


def _draw_container(
    layer: Image.Image,
    container: str,
    center_x: int,
    center_y: int,
    widths: list[int],
    line_height: int,
    palette: list[RGBA],
) -> None:
    draw = ImageDraw.Draw(layer)
    if container in {"double_ribbon", "single_ribbon"}:
        offsets = [-(line_height * 2 // 3), line_height * 2 // 3] if len(widths) > 1 else [0]
        for index, (width, offset) in enumerate(zip(widths, offsets)):
            height = max(54, round(line_height * (0.9 if index == 0 else 0.72)))
            color = palette[min(index, len(palette) - 1)]
            polygon = _ribbon_polygon(center_x, center_y + offset, width + height, height)
            draw.polygon(polygon, fill=color, outline=(255, 255, 255, 210), width=max(2, height // 24))
    elif container == "illustrated_base":
        width = max(widths) + line_height
        height = line_height + 30
        box = (
            center_x - width // 2,
            center_y - height // 2,
            center_x + width // 2,
            center_y + height // 2,
        )
        draw.rounded_rectangle(box, radius=height // 2, fill=palette[0], outline=palette[-1], width=5)
        for direction in (-1, 1):
            x = center_x + direction * (width // 2 + 18)
            draw.ellipse((x - 14, center_y - 14, x + 14, center_y + 14), fill=palette[-1])


def _draw_arc_line(
    layer: Image.Image,
    center: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    colors: list[RGBA],
    outline_color: RGBA,
    outline_width: int,
    max_width: int,
) -> None:
    advances = [_advance(font, character) for character in text]
    total = max(1.0, sum(advances))
    span = min(math.radians(36), total / max(1, max_width) * math.radians(44))
    radius = max(max_width * 1.2, total / max(span, 0.01))
    progress = 0.0
    for index, (character, advance) in enumerate(zip(text, advances)):
        midpoint = progress + advance / 2
        theta = -span / 2 + span * midpoint / total
        x = center[0] + math.sin(theta) * radius
        y = center[1] + (1 - math.cos(theta)) * radius
        glyph_bbox = font.getbbox(character, stroke_width=outline_width)
        glyph_size = (
            max(8, glyph_bbox[2] - glyph_bbox[0] + outline_width * 4 + 8),
            max(8, glyph_bbox[3] - glyph_bbox[1] + outline_width * 4 + 8),
        )
        glyph = Image.new("RGBA", glyph_size, (0, 0, 0, 0))
        ImageDraw.Draw(glyph).text(
            (glyph_size[0] / 2, glyph_size[1] / 2),
            character,
            font=font,
            anchor="mm",
            fill=colors[len(colors) // 2],
            stroke_width=outline_width,
            stroke_fill=outline_color,
        )
        rotated = glyph.rotate(
            math.degrees(theta) * 0.72,
            resample=Image.Resampling.BICUBIC,
            expand=True,
        )
        layer.alpha_composite(rotated, (round(x - rotated.width / 2), round(y - rotated.height / 2)))
        progress += advance


def _translate(layer: Image.Image, dx: int, dy: int = 0) -> Image.Image:
    translated = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    translated.alpha_composite(layer, (dx, dy))
    return translated


def _font_record(role: str, resolved: ResolvedFont) -> dict[str, Any]:
    return {
        "role": role,
        "path": str(resolved.path),
        "source": resolved.source,
        "font_id": resolved.font_id,
        "family": resolved.family,
        "sha256": resolved.sha256,
    }


def render_title_plan(
    image: Image.Image,
    plan: dict[str, Any],
    *,
    registry: FontRegistry | None = None,
    user_font: Path | None = None,
    colors: list[RGBA] | None = None,
    outline_color: RGBA | None = None,
    outline_width: int = 3,
    shadow_color: RGBA | None = None,
    shadow_offset: tuple[int, int] = (7, 9),
    shadow_blur: int = 4,
) -> TitleRenderResult:
    validate_document(plan, "title_layout_plan.schema.json")
    if plan["render_mode"] == "ai_integrated":
        raise ValueError("ai_integrated 标题不由确定性标题渲染器绘制")

    registry = registry or FontRegistry()
    width, height = image.size
    center_x = round(width * plan["center_x_percent"] / 100)
    baseline_y = round(height * (0.165 if plan["orientation"] == "landscape" else 0.186))
    center_y = baseline_y - plan["portrait_up_shift_px"]
    max_width = round(width * plan["width_percent"] / 100)
    max_height = round(height * (0.19 if plan["orientation"] == "landscape" else 0.16))

    roles: list[str] = []
    resolved_fonts: list[ResolvedFont] = []
    for line in plan["lines"]:
        role = plan["font_roles"][line["role"]]
        roles.append(role)
        resolved_fonts.append(registry.resolve(role, line["text"], user_font))

    primary_size = min(190, round(max_height * (0.62 if len(plan["lines"]) > 1 else 0.82)))
    fitted: list[tuple[ImageFont.FreeTypeFont, int, int, int]] = []
    while primary_size >= 42:
        fitted.clear()
        total_height = 0
        widest = 0
        for line, resolved in zip(plan["lines"], resolved_fonts):
            size = max(24, round(primary_size * line["size_ratio"]))
            weight = 760 if line["role"] == "primary" else 600
            font = _load_font(resolved.path, size, weight)
            tracking = round(size * line["tracking_em"])
            line_width = _tracked_width(line["text"], font, tracking)
            bbox = font.getbbox(line["text"], stroke_width=outline_width)
            line_height = max(1, bbox[3] - bbox[1])
            fitted.append((font, tracking, line_width, line_height))
            widest = max(widest, line_width)
            total_height += line_height
        fit_gap_ratio = 0.3 if plan["layout_family"] == "ceremonial_arc" else 0.18
        total_height += max(0, len(fitted) - 1) * round(primary_size * fit_gap_ratio)
        width_factor = 1.18 if plan["container"]["type"] in {"double_ribbon", "single_ribbon"} else 1
        if widest * width_factor <= max_width and total_height <= max_height:
            break
        primary_size -= 3
    else:
        raise ValueError("标题无法在安全区域内完成最多两行的结构化排版")

    default_colors = (
        [(31, 78, 121, 255)]
        if plan["render_mode"] == "vector_flat"
        else [(255, 247, 184, 255), (219, 173, 55, 255), (111, 70, 14, 255)]
    )
    palette = colors or default_colors
    outline = outline_color or ((91, 57, 13, 255) if plan["render_mode"] == "vector_effect" else palette[0])
    shadow_fill = shadow_color or (39, 27, 10, 110)
    if plan["render_mode"] == "vector_flat":
        palette = [palette[0]]
        outline = palette[0]
        outline_width = 0
        shadow_fill = (0, 0, 0, 0)
        shadow_offset = (0, 0)
        shadow_blur = 0

    core = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    gap_ratio = 0.3 if plan["layout_family"] == "ceremonial_arc" else 0.18
    line_gap = round(primary_size * gap_ratio)
    heights = [item[3] for item in fitted]
    total_height = sum(heights) + line_gap * max(0, len(heights) - 1)
    cursor_y = center_y - total_height // 2
    centers: list[tuple[int, int]] = []
    for index, line_height in enumerate(heights):
        centers.append((center_x, round(cursor_y + line_height / 2)))
        cursor_y += line_height + line_gap

    container_palette = [(35, 86, 130, 235), (102, 64, 21, 235), (230, 185, 66, 255)]
    _draw_container(
        core,
        plan["container"]["type"],
        center_x,
        center_y,
        [item[2] for item in fitted],
        primary_size,
        container_palette,
    )

    for index, (line, fitted_line) in enumerate(zip(plan["lines"], fitted)):
        font, tracking, _, line_height = fitted_line
        line_center = (centers[index][0], round(centers[index][1] - line_height / 2))
        text_palette = palette
        if plan["layout_family"] == "playful_children" and plan["render_mode"] != "vector_flat":
            text_palette = [
                (244, 85, 70, 255),
                (247, 177, 45, 255),
                (47, 153, 109, 255),
                (42, 127, 195, 255),
                (126, 87, 194, 255),
            ]
        if line["path"] == "arc_up":
            _draw_arc_line(
                core,
                (center_x, line_center[1]),
                line["text"],
                font,
                text_palette,
                outline,
                outline_width,
                max_width,
            )
        elif plan["render_mode"] == "vector_flat" or plan["layout_family"] == "playful_children":
            _draw_tracked(
                core,
                line_center,
                line["text"],
                font,
                tracking,
                text_palette[0],
                stroke_width=outline_width,
                stroke_fill=outline,
                palette=text_palette if plan["layout_family"] == "playful_children" else None,
            )
        else:
            _draw_effect_line(
                core,
                shadow,
                line_center,
                line["text"],
                font,
                tracking,
                text_palette,
                outline,
                outline_width,
                shadow_fill,
                shadow_offset,
                shadow_blur,
            )

    bbox = core.getbbox()
    if not bbox:
        raise ValueError("标题渲染结果为空")
    dx = round(center_x - ((bbox[0] + bbox[2]) / 2))
    core = _translate(core, dx)
    shadow = _translate(shadow, dx)
    bbox = core.getbbox()
    if not bbox:
        raise ValueError("标题渲染结果为空")
    center_error = abs(((bbox[0] + bbox[2]) / 2) - center_x)
    if center_error > 1:
        raise ValueError(f"标题水平中心误差 {center_error:.2f}px 超过 1px")

    result = image.convert("RGBA")
    result = Image.alpha_composite(result, shadow)
    result = Image.alpha_composite(result, core)
    evidence = [_font_record(role, resolved) for role, resolved in zip(roles, resolved_fonts)]
    deduplicated = list({(item["role"], item["sha256"]): item for item in evidence}.values())
    return TitleRenderResult(result, list(bbox), center_error, deduplicated)
