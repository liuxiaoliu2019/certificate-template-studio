# Certificate Template Studio

[中文](README.md)

Certificate Template Studio is a Codex skill for building certificate and award-template workflows that are reviewable, reversible, and reusable.

It supports two modes: creating a certificate system from a textbook cover, or faithfully rebuilding an existing landscape or portrait certificate template into approved masters for both orientations. The workflow includes a mandatory mode menu, Style DNA and Template DNA, character identity locking, three concept directions, explicit approval gates, revision history, rollback, and multi-title reuse.

## Highlights

- Two explicit modes: textbook-cover creation and bidirectional template rebuilding.
- Character identity locks for facial features, hair, clothing, accessories, species, and proportions.
- Three genuinely different landscape concepts in textbook mode, including a full-frame option.
- Fresh composition for each orientation—never rotate, stretch, crop, or mechanically extend an image.
- Exact mini-program PNG output: `2172 × 1536 px` landscape and `1536 × 2172 px` portrait.
- Three title modes: deterministic flat color, deterministic styled effects, or validated AI-integrated lettering.
- A finalization report gate covering dimensions, ratio handling, title centering, artifact hash, and title validation.
- Separate user approval for landscape and portrait masters.
- LEVEL1/2/3 revisions with non-destructive history and rollback.
- Structured Style DNA, Template DNA, manifests, revision logs, and JSON Schemas.
- Reuse of approved landscape and portrait masters for new titles.

## Start

Install the repository, restart Codex or open a new task, then enter:

```text
Use $certificate-template-studio to start a new job.
```

The skill always begins with this mode menu:

```text
请选择工作模式：
1｜教材封面生成证书
2｜现成模板双向转换

请回复 1 或 2。
```

The Chinese menu is intentionally fixed because the current workflow is designed for Chinese-language interaction.

## Install

macOS / Linux:

```bash
git clone https://github.com/liuxiaoliu2019/certificate-template-studio.git \
  ~/.codex/skills/certificate-template-studio
```

Windows PowerShell:

```powershell
git clone https://github.com/liuxiaoliu2019/certificate-template-studio.git `
  "$env:USERPROFILE\.codex\skills\certificate-template-studio"
```

Alternatively, clone or download the repository and run `install.ps1` on Windows or `install.sh` on macOS/Linux. Existing non-empty installations are never overwritten silently. With `-Force` or `--force`, the installer first moves the old installation to a timestamped backup.

Release archives are available from [GitHub Releases](https://github.com/liuxiaoliu2019/certificate-template-studio/releases).

## Requirements

- Codex Desktop or another Codex environment that supports local skills.
- Python 3.10+.
- Pillow for image dimensions, orientation detection, character reference crops, exact-size finalization, and deterministic title rendering.
- A host with image-input and image-generation capability for final artwork.

Install development dependencies with:

```bash
python -m pip install -r requirements-dev.txt
```

## Validate

```bash
python scripts/quick_validate.py .
python scripts/public_release_validate.py .
```

The public validator also checks the exact output dimensions, title modes, finalization reports, example schemas, control-map hashes, and release-safety rules.

## Licensing

- Code, prompts, schemas, and documentation: [MIT License](LICENSE), copyright © 刘小刘.
- `assets/controls/landscape_v3.png` and `assets/controls/portrait_v3.png`: [CC BY 4.0](LICENSE-ASSETS.md), created by 刘小刘.
- See [NOTICE.md](NOTICE.md) for attribution and asset hashes.

## Content boundary

This repository contains no textbook covers, publisher logos, downloaded certificate references, or generated certificate artwork. All example course and project names are fictional. Users are responsible for having the right to process their own input images and for reviewing generated outputs.

This project is not affiliated with, endorsed by, or sponsored by any textbook publisher, examination body, or certificate institution.

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request, and follow [SECURITY.md](SECURITY.md) when reporting a vulnerability.
