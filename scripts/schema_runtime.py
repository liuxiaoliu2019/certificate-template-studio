from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


class SchemaValidationError(ValueError):
    """A stable, user-readable schema validation failure."""


def _json_path(parts: list[object]) -> str:
    if not parts:
        return "$"
    result = "$"
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}"
    return result


class SchemaRuntime:
    def __init__(self, skill_root: Path):
        self.skill_root = skill_root.expanduser().resolve()
        self.schema_root = self.skill_root / "schemas"
        self.documents: dict[str, dict[str, Any]] = {}
        resources: list[tuple[str, Resource[Any]]] = []
        for path in sorted(self.schema_root.glob("*.schema.json")):
            with path.open("r", encoding="utf-8") as handle:
                document = json.load(handle)
            Draft202012Validator.check_schema(document)
            self.documents[path.name] = document
            schema_id = document.get("$id")
            if schema_id:
                resources.append((schema_id, Resource.from_contents(document)))
        self.registry = Registry().with_resources(resources)

    def validate(self, instance: Any, schema_name: str) -> None:
        try:
            schema = self.documents[schema_name]
        except KeyError as exc:
            raise FileNotFoundError(f"找不到 Schema：{schema_name}") from exc
        validator = Draft202012Validator(schema, registry=self.registry)
        errors = sorted(
            validator.iter_errors(instance),
            key=lambda item: (list(item.absolute_path), item.message),
        )
        if not errors:
            return
        first = errors[0]
        path = _json_path(list(first.absolute_path))
        raise SchemaValidationError(f"{schema_name} 在 {path} 校验失败：{first.message}")


@lru_cache(maxsize=4)
def runtime_for(skill_root: str) -> SchemaRuntime:
    return SchemaRuntime(Path(skill_root))


def validate_document(instance: Any, schema_name: str, skill_root: Path | None = None) -> None:
    root = (skill_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    runtime_for(str(root)).validate(instance, schema_name)
