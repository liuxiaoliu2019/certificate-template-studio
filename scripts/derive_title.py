from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from _common import load_json, safe_slug, save_json, sha256_file, utc_now
from metrics import MetricsRecorder
from project_io import relative_posix, resolve_project_path
from schema_runtime import validate_document
from title_planner import LAYOUT_FAMILIES


def _manifest_path(project: Path) -> Path:
    textbook = project / "configs/project_manifest.json"
    template = project / "configs/template_project_manifest.json"
    if textbook.is_file():
        return textbook
    if template.is_file():
        return template
    raise FileNotFoundError("项目缺少 manifest")


def _unique_slug(project: Path, title: str) -> str:
    base = safe_slug(title)
    candidate = base
    sequence = 2
    while (project / "derivatives" / candidate).exists():
        candidate = f"{base}-{sequence}"
        sequence += 1
    return candidate


def derive_title(
    project: Path,
    title: str,
    landscape_base: str,
    portrait_base: str,
    *,
    title_mode: str = "vector_effect",
    layout_family: str = "formal_two_tier",
) -> dict[str, Any]:
    root = project.expanduser().resolve()
    manifest_path = _manifest_path(root)
    manifest = load_json(manifest_path)
    if manifest["landscape"]["status"] != "approved" or manifest["portrait"]["status"] != "approved":
        raise ValueError("横版和竖版 Master 都明确批准后才能走多标题快速通道")
    if title_mode == "ai_integrated":
        raise ValueError("AI 融合标题必须具备安全无文字标题区资产；当前快速通道只接受程序标题底图")
    bases = {
        "landscape": resolve_project_path(root, landscape_base, must_exist=True),
        "portrait": resolve_project_path(root, portrait_base, must_exist=True),
    }
    masters: dict[str, Path] = {}
    for orientation in ("landscape", "portrait"):
        master_value = manifest["master"].get(orientation)
        if not master_value:
            raise ValueError(f"manifest 缺少已批准 {orientation} Master")
        masters[orientation] = resolve_project_path(root, master_value, must_exist=True)

    slug = _unique_slug(root, title)
    derivative_dir = root / "derivatives" / slug
    derivative_dir.mkdir(parents=True, exist_ok=False)
    outputs: dict[str, Any] = {}
    finalizer = Path(__file__).resolve().parent / "finalize_certificate.py"
    metrics_path = root / "logs/execution_metrics.json"
    for orientation in ("landscape", "portrait"):
        image_path = derivative_dir / f"{orientation}.png"
        report_path = derivative_dir / f"{orientation}.finalization.json"
        plan_path = derivative_dir / f"{orientation}.title-layout.json"
        command = [
            sys.executable, str(finalizer), "--input", str(bases[orientation]),
            "--output", str(image_path), "--report", str(report_path), "--project-root", str(root),
            "--orientation", orientation, "--title", title, "--title-mode", title_mode,
            "--layout-family", layout_family, "--base-text-free",
        ]
        if metrics_path.is_file():
            command.extend(["--metrics", str(metrics_path)])
        completed = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout)
        generated_plan = report_path.with_name(f"{image_path.stem}.title-layout.json")
        if generated_plan != plan_path:
            generated_plan.replace(plan_path)
        outputs[orientation] = {
            "image": {"path": relative_posix(image_path, root), "sha256": sha256_file(image_path)},
            "report": {"path": relative_posix(report_path, root), "sha256": sha256_file(report_path)},
            "title_plan": {"path": relative_posix(plan_path, root), "sha256": sha256_file(plan_path)},
        }
    derivative = {
        "schema_version": "1.0",
        "title": title.strip(),
        "slug": slug,
        "source_masters": {
            orientation: {"path": relative_posix(path, root), "sha256": sha256_file(path)}
            for orientation, path in masters.items()
        },
        "title_family": layout_family,
        "outputs": outputs,
        "created_at": utc_now(),
    }
    validate_document(derivative, "derivative_manifest.schema.json")
    derivative_path = derivative_dir / "derivative_manifest.json"
    save_json(derivative_path, derivative)
    manifest["derivatives"].append(
        {
            "title": derivative["title"], "slug": slug,
            "source_master": derivative["source_masters"]["landscape"]["path"],
            "landscape": outputs["landscape"]["image"]["path"],
            "portrait": outputs["portrait"]["image"]["path"],
            "created_at": derivative["created_at"], "manifest_path": relative_posix(derivative_path, root),
        }
    )
    save_json(manifest_path, manifest)
    if metrics_path.is_file():
        MetricsRecorder(metrics_path).increment("title_derivatives", stage="derivative", path=relative_posix(derivative_path, root))
    return derivative


def main() -> int:
    parser = argparse.ArgumentParser(description="从已批准横竖 Master 的无文字底图派生新标题。")
    parser.add_argument("project", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--landscape-base", required=True)
    parser.add_argument("--portrait-base", required=True)
    parser.add_argument("--title-mode", choices=["vector_flat", "vector_effect"], default="vector_effect")
    parser.add_argument("--layout-family", choices=LAYOUT_FAMILIES, default="formal_two_tier")
    args = parser.parse_args()
    result = derive_title(args.project, args.title, args.landscape_base, args.portrait_base, title_mode=args.title_mode, layout_family=args.layout_family)
    print(result["slug"])
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}")
        raise SystemExit(1)
