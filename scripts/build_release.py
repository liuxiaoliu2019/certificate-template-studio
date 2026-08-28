#!/usr/bin/env python3
"""Build a deterministic release archive for the skill."""

from __future__ import annotations

import argparse
import hashlib
import re
import zipfile
from pathlib import Path

from font_registry import FontRegistry


EXCLUDED_PARTS = {".git", "__pycache__", "build", "dist"}
EXCLUDED_SUFFIXES = {".pyc", ".zip"}
ARCHIVE_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def skill_version(root: Path) -> str:
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r'^\s*version:\s*["\']?([^"\'\s]+)', text, re.MULTILINE)
    if not match:
        raise ValueError("SKILL.md 未声明 metadata.version")
    return match.group(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_include(relative: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    return relative.suffix.lower() not in EXCLUDED_SUFFIXES


def main() -> int:
    parser = argparse.ArgumentParser(description="构建 certificate-template-studio 发布 ZIP。")
    parser.add_argument("skill", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.skill.expanduser().resolve()
    FontRegistry(root).validate_assets()
    version = skill_version(root)
    output = args.output or root / "dist" / f"certificate-template-studio-v{version}.zip"
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(
        path for path in root.rglob("*")
        if path.is_file() and should_include(path.relative_to(root)) and path.resolve() != output
    )
    if not files:
        raise ValueError("没有可打包文件")

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(root)
            archive_name = (Path("certificate-template-studio") / relative).as_posix()
            info = zipfile.ZipInfo(archive_name, ARCHIVE_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.name == "install.sh" else 0o644) << 16
            archive.writestr(info, path.read_bytes())

    print(f"Built: {output}")
    print(f"SHA256: {sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
