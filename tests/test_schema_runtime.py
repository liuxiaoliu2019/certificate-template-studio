from __future__ import annotations

import json
from pathlib import Path

import pytest

from schema_runtime import SchemaValidationError, validate_document


def test_valid_style_dna_example_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    instance = json.loads(
        (root / "examples/SunnyFarmCourse/style_dna.json").read_text(encoding="utf-8")
    )
    validate_document(instance, "style_dna.schema.json")


def test_invalid_document_reports_json_path() -> None:
    with pytest.raises(SchemaValidationError, match=r"style_dna\.schema\.json 在 \$"):
        validate_document({}, "style_dna.schema.json")


def test_unknown_schema_is_rejected() -> None:
    with pytest.raises(FileNotFoundError, match="找不到 Schema"):
        validate_document({}, "missing.schema.json")
