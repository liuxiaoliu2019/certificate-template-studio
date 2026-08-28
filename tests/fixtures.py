from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def run_script(name: str, *arguments: object) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name), *(str(item) for item in arguments)],
        cwd=ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def make_image(path: Path, size: tuple[int, int], color: str = "white") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="PNG")
    return path


def init_textbook(tmp_path: Path, project_id: str = "audit-course") -> Path:
    cover = make_image(tmp_path / "cover.png", (900, 1200))
    result = run_script(
        "init_project.py",
        "--name",
        "Audit Course",
        "--root",
        tmp_path,
        "--cover",
        cover,
        "--project-id",
        project_id,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return tmp_path / project_id


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()
