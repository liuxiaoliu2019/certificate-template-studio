from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from project_io import load_json


MODE_MENU = """请选择工作模式：
1｜教材封面生成证书
2｜现成模板双向转换

请回复 1 或 2。"""

TEXTBOOK_PATTERNS = (
    r"(?:模式|选择)\s*1(?:\D|$)",
    r"教材封面",
    r"教材封面(?:生成|制作|创建).{0,8}(?:证书|奖状)",
    r"(?:证书|奖状).{0,8}教材封面",
)
TEMPLATE_PATTERNS = (
    r"(?:模式|选择)\s*2(?:\D|$)",
    r"(?:现成)?模板.{0,8}(?:双向|横竖|转换)",
    r"(?:横版|竖版).{0,8}模板.{0,8}(?:转换|重制)",
)


def _matches(message: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, message, re.IGNORECASE) for pattern in patterns)


def route_start(message: str, existing_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    if existing_manifest:
        mode = existing_manifest.get("selected_mode") or existing_manifest.get("mode")
        stage = existing_manifest.get("workflow", {}).get("stage")
        if mode in {"textbook_cover", "template_bidirectional"} and stage:
            return {"action": "resume", "selected_mode": mode, "stage": stage}

    normalized = " ".join(message.strip().split())
    textbook = _matches(normalized, TEXTBOOK_PATTERNS)
    template = _matches(normalized, TEMPLATE_PATTERNS)
    if textbook and not template:
        return {"action": "start", "selected_mode": "textbook_cover"}
    if template and not textbook:
        return {"action": "start", "selected_mode": "template_bidirectional"}
    return {"action": "menu", "selected_mode": None, "message": MODE_MENU}


def main() -> int:
    parser = argparse.ArgumentParser(description="解析 certificate-template-studio 智能启动模式。")
    parser.add_argument("--message", required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    manifest = load_json(args.manifest.expanduser().resolve()) if args.manifest else None
    print(json.dumps(route_start(args.message, manifest), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
