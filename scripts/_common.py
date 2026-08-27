from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
    ) as handle:
        handle.write(payload)
        temp_name = handle.name
    os.replace(temp_name, path)


def safe_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    if not slug:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
        slug = f"project-{digest}"
    if not slug[0].isalnum():
        slug = f"project-{slug}"
    return slug


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def project_file(project: Path, relative: str) -> Path:
    candidate = (project / relative).resolve()
    root = project.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"路径必须位于项目目录内：{relative}")
    return candidate


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
