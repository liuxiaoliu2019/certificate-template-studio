from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path
from typing import Any

from _common import save_json, utc_now
from schema_runtime import validate_document


STAGE_BUDGETS = {
    "analysis": 18000,
    "planning": 22000,
    "landscape": 18000,
    "revision": 10000,
    "portrait": 16000,
    "derivative": 9000,
    "approval": 8000,
}

COMMON = {
    "skill/references/v3-title-rules.md",
    "skill/references/output-and-title-rendering.md",
    "configs/generation_config.json",
    "configs/project_manifest.json",
    "configs/template_project_manifest.json",
}

POLICIES = {
    "analysis": COMMON
    | {
        "skill/references/design-rules.md",
        "skill/references/character-identity-lock.md",
        "skill/references/template-bidirectional-workflow.md",
        "skill/prompts/analyze-cover.md",
        "skill/prompts/analyze-character-identity.md",
        "skill/prompts/analyze-certificate-template.md",
        "input/*",
    },
    "planning": COMMON
    | {
        "skill/references/certificate-style-library.md",
        "skill/references/style-compatibility-scoring.md",
        "skill/references/style-parameter-rules.md",
        "skill/prompts/recommend-certificate-styles.md",
        "skill/prompts/build-style-profile.md",
        "analysis/*.json",
        "styles/*.json",
        "controls/*.png",
        "input/*",
        "analysis/character_refs/*.png",
    },
    "landscape": COMMON
    | {
        "skill/prompts/landscape-three-concepts.md",
        "skill/prompts/generate-title-free-base.md",
        "analysis/*.json",
        "styles/*.json",
        "controls/landscape_v3.png",
        "input/*",
        "analysis/character_refs/*.png",
    },
    "revision": COMMON
    | {
        "skill/references/revision-levels-and-state-lock.md",
        "skill/prompts/revise-level1.md",
        "skill/prompts/revise-level2.md",
        "skill/prompts/revise-level3.md",
        "styles/*.json",
        "selected/*.png",
        "revisions/*.png",
        "analysis/character_identity.json",
        "analysis/character_refs/*.png",
        "**/title-layout*.json",
        "feedback/current.txt",
    },
    "portrait": COMMON
    | {
        "skill/prompts/portrait-derivative.md",
        "skill/prompts/derive-opposite-orientation.md",
        "analysis/*.json",
        "styles/*.json",
        "controls/portrait_v3.png",
        "selected/*.png",
        "analysis/character_refs/*.png",
        "input/*",
    },
    "derivative": COMMON
    | {
        "skill/references/multi-title-rules.md",
        "skill/prompts/multi-title-derivative.md",
        "selected/*.png",
        "styles/*.json",
        "**/title-layout*.json",
    },
    "approval": COMMON
    | {
        "skill/references/revision-levels-and-state-lock.md",
        "selected/*.png",
        "portrait/*.png",
        "**/*.finalization.json",
        "scores/*.json",
        "**/title-layout*.json",
    },
}


def _allowed(path: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def build_active_context(
    stage: str,
    mode: str,
    resources: list[dict[str, Any]],
    *,
    used_character_ids: set[str] | None = None,
) -> dict[str, Any]:
    if stage not in STAGE_BUDGETS:
        raise ValueError(f"未知上下文阶段：{stage}")
    if mode not in {"textbook_cover", "template_bidirectional"}:
        raise ValueError(f"未知工作模式：{mode}")
    used = used_character_ids or set()
    normalized: list[dict[str, Any]] = []
    for resource in resources:
        item = {
            "kind": resource["kind"],
            "path": str(resource["path"]).replace("\\", "/").lstrip("./"),
            "text_chars": int(resource.get("text_chars", 0)),
            "character_id": resource.get("character_id"),
        }
        if not _allowed(item["path"], POLICIES[stage]):
            raise ValueError(f"阶段 {stage} 禁止加载资源：{item['path']}")
        if mode == "template_bidirectional" and (
            "style_dna" in item["path"] or "character_" in item["path"] or "character_refs" in item["path"]
        ):
            raise ValueError("模板双向模式不得加载教材 Style DNA 或角色资料")
        if mode == "textbook_cover" and "template_dna" in item["path"]:
            raise ValueError("教材封面模式不得加载 Template DNA")
        if item["character_id"] and item["character_id"] not in used:
            raise ValueError(f"不得加载未实际使用的角色裁切：{item['character_id']}")
        normalized.append(item)

    text_used = sum(item["text_chars"] for item in normalized)
    budget = STAGE_BUDGETS[stage]
    if text_used > budget:
        raise ValueError(f"阶段 {stage} 文本上下文 {text_used} 字符超过预算 {budget}")
    context = {
        "schema_version": "1.0",
        "stage": stage,
        "mode": mode,
        "text_budget_chars": budget,
        "text_chars_used": text_used,
        "resources": normalized,
        "created_at": utc_now(),
    }
    validate_document(context, "active_context.schema.json")
    return context


def _parse_resource(value: str) -> dict[str, Any]:
    parts = value.split(":", 2)
    if len(parts) < 2:
        raise argparse.ArgumentTypeError("--resource 必须为 KIND:PATH[:TEXT_CHARS]")
    chars = int(parts[2]) if len(parts) == 3 else 0
    return {"kind": parts[0], "path": parts[1], "text_chars": chars}


def main() -> int:
    parser = argparse.ArgumentParser(description="建立当前阶段的最小上下文清单。")
    parser.add_argument("--stage", required=True, choices=sorted(STAGE_BUDGETS))
    parser.add_argument("--mode", required=True, choices=["textbook_cover", "template_bidirectional"])
    parser.add_argument("--resource", action="append", type=_parse_resource, default=[])
    parser.add_argument("--used-character-id", action="append", default=[])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    context = build_active_context(
        args.stage,
        args.mode,
        args.resource,
        used_character_ids=set(args.used_character_id),
    )
    save_json(args.output.expanduser().resolve(), context)
    print(args.output.expanduser().resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}")
        raise SystemExit(1)
