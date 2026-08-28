from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable


Validator = Callable[[Any], None]


def resolve_project_path(
    project: Path,
    relative: str | Path,
    *,
    must_exist: bool = False,
    allow_project_root: bool = False,
) -> Path:
    root = project.expanduser().resolve()
    raw = Path(relative)
    if not str(raw).strip():
        raise ValueError("项目相对路径不能为空")
    if raw.is_absolute():
        raise ValueError(f"项目路径必须使用相对路径：{relative}")
    candidate = (root / raw).resolve()
    if candidate == root and not allow_project_root:
        raise ValueError("项目文件路径不能指向项目根目录")
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"路径必须位于项目目录内：{relative}")
    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"项目内找不到文件：{relative}")
    return candidate


def relative_posix(path: Path, project: Path) -> str:
    resolved = path.expanduser().resolve()
    root = project.expanduser().resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"路径必须位于项目目录内：{path}")
    return resolved.relative_to(root).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象：{path}")
    return value


def atomic_write_json(path: Path, value: dict[str, Any], validator: Validator | None = None) -> None:
    if validator:
        validator(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        if validator:
            validator(load_json(temp_path))
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
