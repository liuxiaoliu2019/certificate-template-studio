#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


MODE_MENU = """请选择工作模式：
1｜教材封面生成证书
2｜现成模板双向转换

请回复 1 或 2。"""


REQUIRED_FILES = [
    "SKILL.md",
    "references/certificate-style-library.md",
    "references/style-compatibility-scoring.md",
    "references/style-parameter-rules.md",
    "references/character-identity-lock.md",
    "references/template-bidirectional-workflow.md",
    "references/output-and-title-rendering.md",
    "references/context-routing.md",
    "references/title-design-system.md",
    "schemas/character_identity.schema.json",
    "schemas/certificate_style_profile.schema.json",
    "schemas/style_recommendation.schema.json",
    "schemas/master_style_profile.schema.json",
    "schemas/template_dna.schema.json",
    "schemas/template_project_manifest.schema.json",
    "schemas/active_context.schema.json",
    "schemas/derivative_manifest.schema.json",
    "schemas/execution_metrics.schema.json",
    "schemas/migration_log.schema.json",
    "schemas/quality_report.schema.json",
    "schemas/source_fingerprint.schema.json",
    "schemas/title_layout_plan.schema.json",
    "schemas/title_quality_report.schema.json",
    "schemas/workflow_event.schema.json",
    "prompts/recommend-certificate-styles.md",
    "prompts/build-style-profile.md",
    "prompts/validate-style-diversity.md",
    "prompts/analyze-character-identity.md",
    "prompts/analyze-certificate-template.md",
    "prompts/regenerate-source-orientation.md",
    "prompts/derive-opposite-orientation.md",
    "prompts/generate-title-free-base.md",
    "prompts/repair-title-layout.md",
    "prompts/review-certificate-candidates.md",
    "prompts/review-title-quality.md",
    "scripts/extract_character_refs.py",
    "scripts/init_template_project.py",
    "scripts/update_template_manifest.py",
    "scripts/record_template_revision.py",
    "scripts/finalize_certificate.py",
    "scripts/cache_engine.py",
    "scripts/context_router.py",
    "scripts/derive_title.py",
    "scripts/metrics.py",
    "scripts/migrate_project.py",
    "scripts/quality_gate.py",
    "scripts/title_planner.py",
    "scripts/title_quality.py",
    "scripts/title_renderer.py",
    "scripts/workflow_engine.py",
    "schemas/finalization_report.schema.json",
    "assets/controls/landscape_v3.png",
    "assets/controls/portrait_v3.png",
    "examples/TemplateBidirectional/template_dna.json",
    "examples/TemplateBidirectional/template_project_manifest.json",
]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_profile(profile: dict, families: set[str], allowed: dict[str, set[str]]) -> None:
    if profile.get("style_family") not in families:
        raise ValueError(f"未知风格家族：{profile.get('style_family')}")
    score = profile.get("compatibility_score")
    if not isinstance(score, int) or not 70 <= score <= 100:
        raise ValueError(f"Style Profile 分数不合格：{score}")
    params = profile.get("parameters", {})
    for key, values in allowed.items():
        if key in params and params.get(key) not in values:
            raise ValueError(f"Style Profile 参数无效：{key}={params.get(key)}")
    if profile.get("schema_version") in {"1.1", "1.2"}:
        required_new = {"concept_role", "frame_structure", "frame_language"}
        missing = required_new - params.keys()
        if missing:
            raise ValueError(f"v1.1 Style Profile 缺少参数：{sorted(missing)}")
        if not isinstance(profile.get("used_character_ids"), list):
            raise ValueError("v1.1 Style Profile 缺少 used_character_ids")
        if params["concept_role"] == "frame_led":
            if params["frame_structure"] != "full_frame" or params["textbook_fusion"] != "conservative":
                raise ValueError("frame_led 必须使用 full_frame 与 conservative 教材融合")
    if profile.get("schema_version") == "1.2":
        treatment = profile.get("title_treatment", {})
        mode = treatment.get("render_mode")
        if mode not in {"vector_flat", "vector_effect", "ai_integrated"}:
            raise ValueError("v1.2 Style Profile 缺少有效 title_treatment")
        if treatment.get("noise_allowed") is not False:
            raise ValueError("title_treatment 必须固定 noise_allowed=false")
        if mode == "vector_flat":
            if len(treatment.get("fill_colors", [])) != 1:
                raise ValueError("vector_flat 必须只有一个填充色")
            shadow = treatment.get("shadow", {})
            if shadow.get("enabled") is not False or shadow.get("offset_px") != [0, 0] or shadow.get("blur_px") != 0:
                raise ValueError("vector_flat 必须关闭阴影")


def validate_recommendation(path: Path, families: set[str], allowed: dict[str, set[str]]) -> None:
    data = load_json(path)
    weights = data.get("weights", {})
    if weights != {
        "illustration_style": 35,
        "core_elements": 25,
        "color_palette": 20,
        "mood": 15,
        "composition": 5,
    }:
        raise ValueError(f"推荐权重错误：{path}")
    evaluations = data.get("evaluations", [])
    if len(evaluations) != 7 or {item.get("style_family") for item in evaluations} != families:
        raise ValueError(f"必须完整评估 7 个风格家族：{path}")
    qualified = set()
    for item in evaluations:
        total = sum(item.get("scores", {}).values())
        if total != item.get("total"):
            raise ValueError(f"评估总分与分项不一致：{path} / {item.get('style_family')}")
        expected = total >= 70
        if item.get("qualified") is not expected:
            raise ValueError(f"qualified 与 70 分门槛不一致：{path} / {item.get('style_family')}")
        if expected:
            qualified.add(item["style_family"])

    profiles = data.get("recommended_profiles", [])
    if len(profiles) != 3 or len({item.get("style_family") for item in profiles}) != 3:
        raise ValueError(f"必须推荐三个不同风格家族：{path}")
    by_id = {}
    for profile in profiles:
        validate_profile(profile, families, allowed)
        if profile["style_family"] not in qualified:
            raise ValueError(f"推荐了未达标风格：{path} / {profile['style_family']}")
        by_id[profile["profile_id"]] = profile

    versions = {profile.get("schema_version") for profile in profiles}
    if versions & {"1.1", "1.2"}:
        if len(versions) != 1:
            raise ValueError(f"同一推荐文件不可混用新旧 Profile：{path}")
        roles = {profile["parameters"]["concept_role"] for profile in profiles}
        expected_roles = {"cover_character_led", "balanced_translation", "frame_led"}
        if roles != expected_roles:
            raise ValueError(f"v1.1 推荐必须覆盖三个设计角色：{path}")
        frame_profiles = [p for p in profiles if p["parameters"]["concept_role"] == "frame_led"]
        if len(frame_profiles) != 1 or frame_profiles[0]["parameters"]["frame_structure"] != "full_frame":
            raise ValueError(f"v1.1 推荐必须有一个完整边框主导 Profile：{path}")

    diversity = data.get("diversity_check", {})
    if diversity.get("passed") is not True:
        raise ValueError(f"差异检查未通过：{path}")
    pairs = diversity.get("pairwise_differences", [])
    if len(pairs) != 3:
        raise ValueError(f"三个候选必须有三组两两比较：{path}")
    seen_pairs = set()
    for pair in pairs:
        ids = pair.get("profiles", [])
        if len(ids) != 2 or any(item not in by_id for item in ids):
            raise ValueError(f"差异比较引用未知 Profile：{path}")
        pair_key = tuple(sorted(ids))
        if pair_key in seen_pairs:
            raise ValueError(f"差异比较重复：{path} / {pair_key}")
        seen_pairs.add(pair_key)
        left = by_id[ids[0]]["parameters"]
        right = by_id[ids[1]]["parameters"]
        actual = {key for key in left if left.get(key) != right.get(key)}
        if len(actual) < 3:
            raise ValueError(f"Profile 实际差异少于三项：{path} / {pair_key}")
        declared = set(pair.get("different_parameters", []))
        if len(declared) < 3 or not declared.issubset(actual):
            raise ValueError(f"差异声明与实际参数不一致：{path} / {pair_key}")


def validate_template_example(root: Path) -> None:
    base = root / "examples" / "TemplateBidirectional"
    dna = load_json(base / "template_dna.json")
    manifest = load_json(base / "template_project_manifest.json")
    if manifest.get("mode") != "template_bidirectional":
        raise ValueError("模板示例 mode 错误")
    if manifest.get("selected_mode") != "template_bidirectional":
        raise ValueError("模板示例 selected_mode 错误")
    source = manifest.get("source_orientation")
    opposite = manifest.get("opposite_orientation")
    expected_opposite = "portrait" if source == "landscape" else "landscape"
    if opposite != expected_opposite:
        raise ValueError("模板示例的源方向与另一方向不互补")
    if dna.get("source_orientation") != source:
        raise ValueError("Template DNA 与 manifest 的源方向不一致")
    dimensions = dna.get("source_dimensions", {})
    if {
        "width_px": dimensions.get("width_px"),
        "height_px": dimensions.get("height_px"),
    } != manifest.get("source_dimensions"):
        raise ValueError("Template DNA 与 manifest 的源尺寸不一致")
    for region in dna.get("text_regions", []):
        if region.get("action") != "remove":
            raise ValueError("模板文字区域必须全部标记为 remove")
        if any(key in region for key in ("content", "text", "transcript", "original_text")):
            raise ValueError("模板 DNA 不得保存或转录源文字")
    title_system = dna.get("title_system")
    if not isinstance(title_system, dict):
        raise ValueError("Template DNA 缺少标题结构锁")
    if title_system.get("placement", {}).get("center_x_percent") != 50:
        raise ValueError("模板标题结构锁必须固定 x=50%")
    treatment = title_system.get("visual_treatment", {})
    if treatment.get("fill_style") == "flat_solid":
        if treatment.get("render_mode") != "vector_flat" or treatment.get("shadow_enabled") is not False:
            raise ValueError("平面模板标题必须使用无阴影 vector_flat")
    forbidden_source_words = {"text", "content", "transcript", "original_text", "source_words"}
    if forbidden_source_words & set(title_system):
        raise ValueError("标题结构锁不得保存或转录源标题文字")
    stage = manifest.get("workflow", {}).get("stage")
    if stage in {"deriving_opposite", "validating_opposite", "awaiting_opposite_approval", "complete"}:
        if manifest[source].get("status") != "approved":
            raise ValueError("生成另一方向前必须有已批准的源方向")
        if manifest[opposite].get("status") not in {"ready", "generating", "awaiting_approval", "approved"}:
            raise ValueError("源方向批准后，另一方向必须解除阻塞")


def main() -> int:
    parser = argparse.ArgumentParser(description="快速验证 certificate-template-studio 结构与风格引擎不变量。")
    parser.add_argument("skill", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.skill.expanduser().resolve()
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"缺少或为空：{relative}")

    skill_path = root / "SKILL.md"
    if skill_path.is_file():
        text = skill_path.read_text(encoding="utf-8")
        if not re.search(r"^name:\s*certificate-template-studio\s*$", text, re.MULTILINE):
            errors.append("SKILL.md name 不正确")
        if not re.search(r'version:\s*"1\.7\.1"', text):
            errors.append("SKILL.md 版本不是 1.7.1")
        if text.count(MODE_MENU) != 1:
            errors.append("SKILL.md 缺少固定模式菜单或菜单文案发生变化")
        for invariant in (
            "用户已明确模式时不重复菜单",
            "已有项目按 manifest 恢复",
            "默认只提交最高分且无硬失败的一套",
            "每个方向最多自动修正一次",
        ):
            if invariant not in text:
                errors.append(f"SKILL.md 缺少模式菜单不变量：{invariant}")
        if re.search(r"\b(?:TODO|TBD)\b|待定", text, re.IGNORECASE):
            errors.append("SKILL.md 含未完成占位内容")
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in link and not (root / link).is_file():
                errors.append(f"SKILL.md 引用不存在：{link}")

    ignored_runtime_parts = {".pytest-temp", ".pytest_cache", "__pycache__", "dist", "build"}
    for path in root.rglob("*.json"):
        if ignored_runtime_parts & set(path.relative_to(root).parts):
            continue
        try:
            load_json(path)
        except Exception as exc:
            errors.append(f"JSON 无法解析：{path.relative_to(root)} / {exc}")

    for path in (root / "scripts").glob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"Python 语法错误：{path.name}:{exc.lineno} / {exc.msg}")

    try:
        profile_schema = load_json(root / "schemas" / "certificate_style_profile.schema.json")
        families = set(profile_schema["$defs"]["styleFamily"]["enum"])
        if len(families) != 7:
            raise ValueError("风格家族数量不是 7")
        parameter_properties = profile_schema["properties"]["parameters"]["properties"]
        allowed = {
            key: set(value.get("enum", [value.get("const")]))
            for key, value in parameter_properties.items()
        }
        for path in (root / "examples").rglob("style_recommendation.json"):
            validate_recommendation(path, families, allowed)
        for path in (root / "examples").rglob("master_style_profile.json"):
            validate_profile(load_json(path)["approved_style_profile"], families, allowed)
    except Exception as exc:
        errors.append(f"风格引擎不变量失败：{exc}")

    try:
        validate_template_example(root)
    except Exception as exc:
        errors.append(f"模板双向模式不变量失败：{exc}")

    try:
        textbook_schema = load_json(root / "schemas" / "project_manifest.schema.json")
        template_schema = load_json(root / "schemas" / "template_project_manifest.schema.json")
        if textbook_schema["properties"]["selected_mode"].get("const") != "textbook_cover":
            raise ValueError("教材 manifest selected_mode 约束错误")
        if template_schema["properties"]["selected_mode"].get("const") != "template_bidirectional":
            raise ValueError("模板 manifest selected_mode 约束错误")
        textbook_init = (root / "scripts" / "init_project.py").read_text(encoding="utf-8")
        template_init = (root / "scripts" / "init_template_project.py").read_text(encoding="utf-8")
        if '"selected_mode": "textbook_cover"' not in textbook_init:
            raise ValueError("教材初始化脚本未写入 selected_mode")
        if '"selected_mode": "template_bidirectional"' not in template_init:
            raise ValueError("模板初始化脚本未写入 selected_mode")
        generation = load_json(root / "examples" / "SunnyFarmCourse" / "generation_config.json")
        if generation.get("schema_version") != "1.4":
            raise ValueError("示例 generation_config 不是 v1.4")
        if generation.get("outputs") != {
            "landscape": {"width_px": 2172, "height_px": 1536, "format": "PNG", "purpose": "mini_program"},
            "portrait": {"width_px": 1536, "height_px": 2172, "format": "PNG", "purpose": "mini_program"},
        }:
            raise ValueError("小程序输出合同不正确")
    except Exception as exc:
        errors.append(f"模式菜单状态不变量失败：{exc}")

    if errors:
        for item in errors:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    recommendation_count = len(list((root / "examples").rglob("style_recommendation.json")))
    print(f"PASS: certificate-template-studio v1.7.1；固定小程序尺寸；六类标题设计；模板标题结构锁；质量托管；最小上下文；缓存；角色身份锁；模板双向审批锁；7 个风格家族；{recommendation_count} 组推荐测试。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
