#!/usr/bin/env python3
"""Validate the repository before a public release."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import jsonschema
import yaml
from PIL import Image
from referencing import Registry, Resource


REQUIRED_PUBLIC_FILES = (
    "README.md",
    "README.en.md",
    "LICENSE",
    "LICENSE-ASSETS.md",
    "NOTICE.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "install.ps1",
    "install.sh",
    "requirements-dev.txt",
    "agents/openai.yaml",
)

EXAMPLE_SCHEMAS = {
    "examples/SunnyFarmCourse/style_dna.json": "schemas/style_dna.schema.json",
    "examples/SunnyFarmCourse/generation_config.json": "schemas/generation_config.schema.json",
    "examples/SunnyFarmCourse/project_manifest.json": "schemas/project_manifest.schema.json",
    "examples/SunnyFarmCourse/revision_log.json": "schemas/revision_log.schema.json",
    "examples/SunnyFarmCourse/character_identity.json": "schemas/character_identity.schema.json",
    "examples/SunnyFarmCourse/style_recommendation.json": "schemas/style_recommendation.schema.json",
    "examples/SunnyFarmCourse/master_style_profile.json": "schemas/master_style_profile.schema.json",
    "examples/FormalNature/style_dna.json": "schemas/style_dna.schema.json",
    "examples/FormalNature/style_recommendation.json": "schemas/style_recommendation.schema.json",
    "examples/UrbanMotionCourse/style_dna.json": "schemas/style_dna.schema.json",
    "examples/UrbanMotionCourse/style_recommendation.json": "schemas/style_recommendation.schema.json",
    "examples/TemplateBidirectional/template_dna.json": "schemas/template_dna.schema.json",
    "examples/TemplateBidirectional/template_project_manifest.json": "schemas/template_project_manifest.schema.json",
}

ALLOWED_IMAGES = {
    Path("assets/controls/landscape_v3.png"),
    Path("assets/controls/portrait_v3.png"),
}

TEXT_SUFFIXES = {
    "",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
}

FORBIDDEN_SUFFIXES = {
    ".bmp",
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".log",
    ".pdf",
    ".pyc",
    ".webp",
    ".zip",
}


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def validate_structure(root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_PUBLIC_FILES:
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"缺少公开发布文件：{relative}")

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in {".git", "dist", "build"} for part in relative.parts):
            continue
        if path.is_dir() and path.name == "__pycache__":
            errors.append(f"包含缓存目录：{relative}")
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            errors.append(f"包含不应发布的文件类型：{relative}")
        if suffix == ".png" and relative not in ALLOWED_IMAGES:
            errors.append(f"仅允许发布两张控制图 PNG：{relative}")


def validate_text_safety(root: Path, errors: list[str]) -> None:
    private_path = re.compile(r"(?i)\b[a-z]:[\\/](?:users|documents and settings)[\\/]")
    drive_path = re.compile(r"(?i)\b(?:d|e|f):[\\/]")
    sensitive_names = (
        "Cam" + "bridge",
        "Power" + " Up",
        "Think" + " 1",
        "Syn" + "ology",
        "le" + "novo",
    )
    credential_patterns = (
        re.compile(r"ghp_[A-Za-z0-9]{20,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"),
    )

    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in {".git", "dist", "build"} for part in relative.parts):
            continue
        if path.name == Path(__file__).name or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"文本文件不是 UTF-8：{relative}")
            continue
        if private_path.search(text) or drive_path.search(text):
            errors.append(f"包含本机绝对路径：{relative}")
        for name in sensitive_names:
            if name.casefold() in text.casefold():
                errors.append(f"包含应匿名化的示例品牌或本机标识：{relative}")
                break
        if any(pattern.search(text) for pattern in credential_patterns):
            errors.append(f"疑似包含凭据：{relative}")


def validate_formats(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*.json"):
        if "dist" in path.parts:
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
        data = yaml.safe_load((root / "agents/openai.yaml").read_text(encoding="utf-8"))
        if data["interface"]["default_prompt"] != "使用 $certificate-template-studio 开始工作。":
            raise ValueError("default_prompt 不正确")
    except Exception as exc:
        errors.append(f"agents/openai.yaml 无效：{exc}")


def validate_examples(root: Path, errors: list[str]) -> None:
    schema_documents = [load_json(path) for path in (root / "schemas").glob("*.schema.json")]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema))
        for schema in schema_documents
        if isinstance(schema, dict) and "$id" in schema
    )
    for example_relative, schema_relative in EXAMPLE_SCHEMAS.items():
        try:
            instance = load_json(root / example_relative)
            schema = load_json(root / schema_relative)
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.Draft202012Validator(schema, registry=registry).validate(instance)
        except Exception as exc:
            errors.append(f"Schema 校验失败：{example_relative} / {exc}")


def validate_control_assets(root: Path, errors: list[str]) -> None:
    try:
        manifest = load_json(root / "assets/controls/asset_manifest.json")
        if not isinstance(manifest, dict) or manifest.get("author") != "刘小刘":
            raise ValueError("控制图作者信息缺失")
        if manifest.get("license") != "CC-BY-4.0":
            raise ValueError("控制图许可不是 CC-BY-4.0")
        entries = manifest.get("assets", [])
        if len(entries) != 2:
            raise ValueError("控制图数量不是 2")
        for entry in entries:
            relative = Path("assets/controls") / entry["file"]
            if relative not in ALLOWED_IMAGES:
                raise ValueError(f"未知控制图：{relative}")
            path = root / relative
            with Image.open(path) as image:
                if image.size != (entry["width_px"], entry["height_px"]):
                    raise ValueError(f"控制图尺寸不符：{relative}")
            if sha256(path) != entry["sha256"]:
                raise ValueError(f"控制图哈希不符：{relative}")
    except Exception as exc:
        errors.append(f"控制图校验失败：{exc}")


def validate_smoke_tests(root: Path, errors: list[str]) -> None:
    quick = run([sys.executable, "scripts/quick_validate.py", str(root)], root)
    if quick.returncode != 0:
        errors.append(f"quick_validate 失败：{quick.stderr or quick.stdout}")

    with tempfile.TemporaryDirectory(prefix="certificate-studio-release-") as temp_value:
        temp = Path(temp_value)
        landscape = temp / "landscape.png"
        portrait = temp / "portrait.png"
        square = temp / "square.png"
        Image.new("RGB", (1492, 1054), "white").save(landscape)
        Image.new("RGB", (1055, 1491), "white").save(portrait)
        Image.new("RGB", (900, 900), "white").save(square)

        font_candidates = [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/System/Library/Fonts/PingFang.ttc"),
        ]
        test_font = next((path for path in font_candidates if path.is_file()), None)
        if not test_font:
            errors.append("找不到用于收尾冒烟测试的系统字体")
        else:
            final_dir = temp / "finalized"
            final_dir.mkdir()
            final_schema = load_json(root / "schemas/finalization_report.schema.json")
            for orientation, source_image, mode, expected in (
                ("landscape", landscape, "vector_flat", (2172, 1536)),
                ("portrait", portrait, "vector_effect", (1536, 2172)),
            ):
                output = final_dir / f"{orientation}.png"
                report_path = final_dir / f"{orientation}.json"
                command = [
                    sys.executable,
                    "scripts/finalize_certificate.py",
                    "--input",
                    str(source_image),
                    "--output",
                    str(output),
                    "--report",
                    str(report_path),
                    "--orientation",
                    orientation,
                    "--title",
                    "CERTIFICATE",
                    "--title-mode",
                    mode,
                    "--font",
                    str(test_font),
                    "--base-text-free",
                ]
                if mode == "vector_effect":
                    command.extend(["--outline-color", "#6B4B12", "--outline-width", "3"])
                result = run(command, root)
                if result.returncode != 0:
                    errors.append(f"{mode} 收尾失败：{result.stderr or result.stdout}")
                    continue
                try:
                    with Image.open(output) as image:
                        if image.size != expected or image.format != "PNG":
                            raise ValueError("最终尺寸或格式不正确")
                    report_data = load_json(report_path)
                    jsonschema.validate(report_data, final_schema)
                    if report_data.get("status") != "passed":
                        raise ValueError("收尾报告未通过")
                    if report_data.get("title", {}).get("center_error_px", 999) > 1:
                        raise ValueError("标题没有精确水平居中")
                    if mode == "vector_flat":
                        with Image.open(output).convert("RGB") as image:
                            pure_pixels = sum(
                                1 for pixel in image.getdata() if pixel == (31, 78, 121)
                            )
                        if pure_pixels < 100:
                            raise ValueError("纯色标题没有保留足够的确定性纯色像素")
                    else:
                        duplicate = final_dir / f"{orientation}-duplicate.png"
                        duplicate_report = final_dir / f"{orientation}-duplicate.json"
                        duplicate_command = command.copy()
                        duplicate_command[duplicate_command.index("--output") + 1] = str(duplicate)
                        duplicate_command[duplicate_command.index("--report") + 1] = str(
                            duplicate_report
                        )
                        duplicate_result = run(duplicate_command, root)
                        if duplicate_result.returncode != 0 or sha256(duplicate) != sha256(output):
                            raise ValueError("同一参数的效果标题不能确定性复现")
                except Exception as exc:
                    errors.append(f"{mode} 收尾结果无效：{exc}")

            bad_ratio = temp / "bad-ratio.png"
            Image.new("RGB", (1200, 900), "white").save(bad_ratio)
            rejected_final = run(
                [
                    sys.executable,
                    "scripts/finalize_certificate.py",
                    "--input",
                    str(bad_ratio),
                    "--output",
                    str(final_dir / "bad.png"),
                    "--orientation",
                    "landscape",
                    "--title",
                    "CERTIFICATE",
                    "--title-mode",
                    "vector_flat",
                    "--font",
                    str(test_font),
                    "--base-text-free",
                ],
                root,
            )
            if rejected_final.returncode == 0:
                errors.append("宽高比误差超过 0.5% 的图片未被收尾脚本拒绝")

        textbook_root = temp / "textbook"
        textbook = run(
            [
                sys.executable,
                "scripts/init_project.py",
                "--name",
                "ReleaseSmokeCourse",
                "--root",
                str(textbook_root),
                "--cover",
                str(portrait),
                "--project-id",
                "release-smoke-course",
            ],
            root,
        )
        if textbook.returncode != 0:
            errors.append(f"教材项目初始化失败：{textbook.stderr or textbook.stdout}")
        else:
            try:
                manifest = load_json(textbook_root / "release-smoke-course/configs/project_manifest.json")
                if manifest.get("selected_mode") != "textbook_cover":
                    raise ValueError("selected_mode 未锁定为 textbook_cover")
            except Exception as exc:
                errors.append(f"教材项目初始化结果无效：{exc}")

        for label, image, expected in (
            ("landscape", landscape, "landscape"),
            ("portrait", portrait, "portrait"),
        ):
            project_root = temp / f"template-{label}"
            result = run(
                [
                    sys.executable,
                    "scripts/init_template_project.py",
                    "--name",
                    f"Template{label.title()}",
                    "--root",
                    str(project_root),
                    "--template",
                    str(image),
                    "--project-id",
                    f"template-{label}",
                ],
                root,
            )
            if result.returncode != 0:
                errors.append(f"{label} 模板初始化失败：{result.stderr or result.stdout}")
                continue
            try:
                manifest = load_json(
                    project_root / f"template-{label}/configs/template_project_manifest.json"
                )
                if manifest.get("selected_mode") != "template_bidirectional":
                    raise ValueError("selected_mode 未锁定为 template_bidirectional")
                if manifest.get("source_orientation") != expected:
                    raise ValueError(f"方向识别结果不是 {expected}")
            except Exception as exc:
                errors.append(f"{label} 模板初始化结果无效：{exc}")

        if test_font:
            approval_project = temp / "template-landscape" / "template-landscape"
            if approval_project.is_dir():
                dna_source = root / "examples/TemplateBidirectional/template_dna.json"
                dna_target = approval_project / "analysis/template_dna.json"
                dna_target.write_text(dna_source.read_text(encoding="utf-8"), encoding="utf-8")
                title_result = run(
                    [
                        sys.executable,
                        "scripts/update_template_manifest.py",
                        str(approval_project),
                        "--set-title",
                        "CERTIFICATE",
                    ],
                    root,
                )
                master_relative = "selected/master_landscape.png"
                report_relative = "selected/master_landscape.finalization.json"
                approval_finalization = run(
                    [
                        sys.executable,
                        "scripts/finalize_certificate.py",
                        "--input",
                        str(landscape),
                        "--output",
                        str(approval_project / master_relative),
                        "--report",
                        str(approval_project / report_relative),
                        "--project-root",
                        str(approval_project),
                        "--orientation",
                        "landscape",
                        "--title",
                        "CERTIFICATE",
                        "--title-mode",
                        "vector_flat",
                        "--font",
                        str(test_font),
                        "--base-text-free",
                    ],
                    root,
                )
                if title_result.returncode != 0 or approval_finalization.returncode != 0:
                    errors.append(
                        "模板批准门槛准备失败："
                        f"{title_result.stderr or approval_finalization.stderr}"
                    )
                else:
                    missing_report = run(
                        [
                            sys.executable,
                            "scripts/update_template_manifest.py",
                            str(approval_project),
                            "--approve-orientation",
                            "landscape",
                            "--artifact",
                            master_relative,
                            "--user-confirmation",
                            "确认横版定稿",
                        ],
                        root,
                    )
                    if missing_report.returncode == 0:
                        errors.append("新版模板项目在没有收尾报告时仍可批准")
                    approved = run(
                        [
                            sys.executable,
                            "scripts/update_template_manifest.py",
                            str(approval_project),
                            "--approve-orientation",
                            "landscape",
                            "--artifact",
                            master_relative,
                            "--finalization-report",
                            report_relative,
                            "--user-confirmation",
                            "确认横版定稿",
                        ],
                        root,
                    )
                    if approved.returncode != 0:
                        errors.append(f"带有效收尾报告的模板批准失败：{approved.stderr}")
                    else:
                        approved_manifest = load_json(
                            approval_project / "configs/template_project_manifest.json"
                        )
                        if (
                            approved_manifest["landscape"].get("finalization_report")
                            != report_relative
                            or approved_manifest["approvals"][-1].get("finalization_report")
                            != report_relative
                        ):
                            errors.append("模板批准没有把收尾报告锁入 manifest")

        square_root = temp / "template-square"
        rejected = run(
            [
                sys.executable,
                "scripts/init_template_project.py",
                "--name",
                "TemplateSquare",
                "--root",
                str(square_root),
                "--template",
                str(square),
                "--project-id",
                "template-square",
            ],
            root,
        )
        if rejected.returncode == 0:
            errors.append("近方形模板未要求显式指定方向")

        override_root = temp / "template-square-override"
        accepted = run(
            [
                sys.executable,
                "scripts/init_template_project.py",
                "--name",
                "TemplateSquareOverride",
                "--root",
                str(override_root),
                "--template",
                str(square),
                "--project-id",
                "template-square-override",
                "--source-orientation",
                "portrait",
            ],
            root,
        )
        if accepted.returncode != 0:
            errors.append(f"近方形模板显式方向初始化失败：{accepted.stderr or accepted.stdout}")


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 certificate-template-studio 公开发布包。")
    parser.add_argument("skill", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.skill.expanduser().resolve()
    errors: list[str] = []

    validate_structure(root, errors)
    validate_text_safety(root, errors)
    validate_formats(root, errors)
    validate_examples(root, errors)
    validate_control_assets(root, errors)
    validate_smoke_tests(root, errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: 公开发布校验通过（结构、隐私、格式、Schema、控制图与初始化冒烟测试）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
