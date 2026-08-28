from __future__ import annotations

from pathlib import Path

import pytest

from font_registry import FONT_ROLES, FontRegistry, FontRegistryError, missing_characters


def test_bundled_fonts_and_hashes_are_valid() -> None:
    registry = FontRegistry()
    registry.validate_assets()
    assert set(registry.manifest["role_candidates"]) == set(FONT_ROLES)


@pytest.mark.parametrize(
    ("role", "text", "expected_id"),
    [
        ("formal_serif", "结业证书", "noto-serif-sc"),
        ("modern_sans", "CERTIFICATE 结业证书", "noto-sans-sc"),
        ("ceremonial_display", "CERTIFICATE OF COMPLETION", "cinzel"),
        ("children_round", "CERTIFICATE", "baloo-2"),
        ("children_round", "结业证书", "noto-sans-sc"),
    ],
)
def test_role_resolution_covers_common_titles(role: str, text: str, expected_id: str) -> None:
    resolved = FontRegistry().resolve(role, text)
    assert resolved.source == "bundled"
    assert resolved.font_id == expected_id
    assert not missing_characters(resolved.path, text)


def test_user_font_has_priority_for_supported_text() -> None:
    registry = FontRegistry()
    bundled = registry.resolve("modern_sans", "CERTIFICATE")
    resolved = registry.resolve("formal_serif", "CERTIFICATE", bundled.path)
    assert resolved.source == "user"
    assert resolved.font_id is None
    assert resolved.path == bundled.path


def test_user_font_missing_glyph_is_explicit_failure() -> None:
    registry = FontRegistry()
    latin_only = registry.resolve("children_round", "CERTIFICATE").path
    with pytest.raises(FontRegistryError, match="用户字体缺少标题字符"):
        registry.resolve("children_round", "结业证书", latin_only)


def test_unknown_role_is_rejected() -> None:
    with pytest.raises(FontRegistryError, match="未知字体角色"):
        FontRegistry().resolve("decorative", "CERTIFICATE")
