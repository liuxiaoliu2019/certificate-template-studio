# Changelog

All notable changes to this project are documented here.

## [1.6.0] - 2026-08-28

### Added

- Exact mini-program PNG output contracts: `2172 × 1536 px` landscape and `1536 × 2172 px` portrait.
- Three title-rendering modes: `vector_flat`, `vector_effect`, and `ai_integrated`.
- Deterministic finalization script for minimal center crop, Lanczos resizing, and vector title rendering.
- Machine-readable finalization reports with dimension, ratio, title-position, validation, and SHA-256 checks.
- Title-free base-generation prompt and output/title-rendering reference rules.

### Changed

- New textbook manifests use version 1.4; new bidirectional-template manifests use version 1.2.
- New project approvals require a passing finalization report that matches the exact artifact on disk.
- Portrait titles remain horizontally centered and use a fixed upward shift of about 110 px at final output size.
- Flat titles prohibit gradients, shadows, random texture, and noise; styled vector titles use deterministic effects.

### Compatibility

- Existing legacy manifests and style profiles remain readable.
- The new approval hard gate applies to newly initialized manifest versions only.

## [1.5.1] - 2026-08-27

### Added

- Mandatory two-option mode menu before any image analysis or project initialization.
- Explicit `selected_mode` records in new textbook and bidirectional-template manifests.
- Bidirectional rebuilding for a user-supplied landscape or portrait certificate template.
- Public-release validation, cross-platform installers, dual licensing, and fictional examples.

### Changed

- Public examples no longer refer to real textbook brands or publishers.
- Control maps are attributed to 刘小刘 and released under CC BY 4.0.

### Compatibility

- Existing manifests from earlier versions remain readable and valid.
