from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont, TTLibError

from schema_runtime import validate_document


FONT_ROLES = ("formal_serif", "modern_sans", "ceremonial_display", "children_round")


class FontRegistryError(ValueError):
    """A stable, user-readable font selection failure."""


@dataclass(frozen=True)
class ResolvedFont:
    path: Path
    source: str
    font_id: str | None
    family: str
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_codepoints(text: str) -> set[int]:
    return {
        ord(character)
        for character in unicodedata.normalize("NFC", text)
        if not character.isspace() and unicodedata.category(character) != "Cf"
    }


@lru_cache(maxsize=32)
def _font_codepoints(path_value: str) -> frozenset[int]:
    path = Path(path_value)
    try:
        font = TTFont(path, lazy=True)
        try:
            codepoints: set[int] = set()
            for table in font["cmap"].tables:
                if table.isUnicode():
                    codepoints.update(table.cmap)
            return frozenset(codepoints)
        finally:
            font.close()
    except (TTLibError, KeyError, OSError) as exc:
        raise FontRegistryError(f"字体无法读取：{path}") from exc


def missing_characters(path: Path, text: str) -> list[str]:
    missing = _required_codepoints(text) - set(_font_codepoints(str(path.resolve())))
    return [chr(codepoint) for codepoint in sorted(missing)]


class FontRegistry:
    def __init__(self, skill_root: Path | None = None):
        self.skill_root = (skill_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
        self.font_root = self.skill_root / "assets" / "fonts"
        manifest_path = self.font_root / "font_manifest.json"
        try:
            self.manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FontRegistryError(f"字体清单无法读取：{manifest_path}") from exc
        validate_document(self.manifest, "font_manifest.schema.json", self.skill_root)
        self.entries = {entry["id"]: entry for entry in self.manifest["fonts"]}
        if len(self.entries) != len(self.manifest["fonts"]):
            raise FontRegistryError("字体清单包含重复 id")

    def validate_assets(self) -> None:
        referenced: set[Path] = set()
        for entry in self.manifest["fonts"]:
            font_path = (self.font_root / entry["file"]).resolve()
            license_path = (self.font_root / entry["license_file"]).resolve()
            metadata_path = (self.font_root / entry["metadata_file"]).resolve()
            for path in (font_path, license_path, metadata_path):
                try:
                    path.relative_to(self.font_root.resolve())
                except ValueError as exc:
                    raise FontRegistryError(f"字体资产路径越界：{path}") from exc
                if not path.is_file() or path.stat().st_size == 0:
                    raise FontRegistryError(f"字体资产缺失：{path}")
            if _sha256(font_path) != entry["sha256"]:
                raise FontRegistryError(f"字体哈希不符：{entry['file']}")
            if "SIL OPEN FONT LICENSE Version 1.1" not in license_path.read_text(
                encoding="utf-8"
            ):
                raise FontRegistryError(f"字体许可证不是 OFL 1.1：{entry['license_file']}")
            referenced.add(font_path)

        for role in FONT_ROLES:
            candidates = self.manifest["role_candidates"].get(role, [])
            if not candidates or any(font_id not in self.entries for font_id in candidates):
                raise FontRegistryError(f"字体角色候选无效：{role}")

        actual = {path.resolve() for path in self.font_root.rglob("*.ttf")}
        if actual != referenced:
            unexpected = sorted(str(path.relative_to(self.font_root)) for path in actual - referenced)
            missing = sorted(str(path.relative_to(self.font_root)) for path in referenced - actual)
            raise FontRegistryError(f"字体文件未完整登记：unexpected={unexpected}, missing={missing}")

    def _resolved(self, path: Path, *, source: str, font_id: str | None, family: str) -> ResolvedFont:
        return ResolvedFont(
            path=path,
            source=source,
            font_id=font_id,
            family=family,
            sha256=_sha256(path),
        )

    def resolve(self, role: str, text: str, user_font: Path | None = None) -> ResolvedFont:
        if role not in FONT_ROLES:
            raise FontRegistryError(f"未知字体角色：{role}")
        if not text.strip():
            raise FontRegistryError("标题不能为空")

        if user_font is not None:
            path = user_font.expanduser().resolve()
            if not path.is_file():
                raise FontRegistryError(f"用户字体不存在：{path}")
            missing = missing_characters(path, text)
            if missing:
                preview = "".join(missing[:12])
                raise FontRegistryError(f"用户字体缺少标题字符：{preview}")
            return self._resolved(path, source="user", font_id=None, family=path.stem)

        attempted: list[str] = []
        for font_id in self.manifest["role_candidates"][role]:
            entry = self.entries[font_id]
            path = (self.font_root / entry["file"]).resolve()
            attempted.append(entry["family"])
            if not path.is_file():
                continue
            if not missing_characters(path, text):
                return self._resolved(
                    path, source="bundled", font_id=font_id, family=entry["family"]
                )
        raise FontRegistryError(f"字体角色 {role} 无法覆盖全部标题字符；已检查：{', '.join(attempted)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="检查并选择证书标题字体。")
    parser.add_argument("--role", required=True, choices=FONT_ROLES)
    parser.add_argument("--text", required=True)
    parser.add_argument("--font", type=Path, help="用户项目字体；指定后不静默回退")
    parser.add_argument("--skill-root", type=Path)
    args = parser.parse_args()

    registry = FontRegistry(args.skill_root)
    registry.validate_assets()
    resolved = registry.resolve(args.role, args.text, args.font)
    print(
        json.dumps(
            {
                "path": str(resolved.path),
                "source": resolved.source,
                "font_id": resolved.font_id,
                "family": resolved.family,
                "sha256": resolved.sha256,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}")
        raise SystemExit(1)
