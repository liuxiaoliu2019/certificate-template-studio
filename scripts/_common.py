from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from project_io import (
    atomic_write_json,
    load_json,
    relative_posix,
    resolve_project_path,
    sha256_file,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def save_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_json(path, value)


def safe_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    if not slug:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
        slug = f"project-{digest}"
    if not slug[0].isalnum():
        slug = f"project-{slug}"
    return slug


def project_file(project: Path, relative: str) -> Path:
    return resolve_project_path(project, relative)


def parse_assignment(value: str) -> tuple[str, Any]:
    if "=" not in value:
        raise ValueError(f"--set 需要 KEY=VALUE：{value}")
    key, raw = value.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError("--set 的 KEY 不能为空")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return key, parsed


def set_dotted(target: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    current: dict[str, Any] = target
    for part in parts[:-1]:
        existing = current.get(part)
        if not isinstance(existing, dict):
            raise KeyError(f"无法设置不存在的对象路径：{dotted}")
        current = existing
    if parts[-1] not in current:
        raise KeyError(f"无法设置未知字段：{dotted}")
    current[parts[-1]] = value
