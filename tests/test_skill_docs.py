from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_skill_version_and_required_invariants() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert 'version: "1.7.0"' in text
    for invariant in ("2172×1536", "1536×2172", "x=50%", "唯一可读文字", "确认横版定稿"):
        assert invariant in text


def test_all_skill_relative_links_exist() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    assert links
    for link in links:
        assert (ROOT / link).is_file(), link


def test_title_container_and_retry_rules_do_not_conflict() -> None:
    paths = [ROOT / "SKILL.md", *sorted((ROOT / "references").glob("*.md")), *sorted((ROOT / "prompts").glob("*.md"))]
    content = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "禁止横幅、丝带" not in content
    assert "连续自动修正最多两次" not in content
    assert "每个方向最多自动修正一次" in content
