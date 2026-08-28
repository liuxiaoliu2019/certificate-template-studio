# Changelog

All notable changes to this project are documented here.

## [1.7.0] - 2026-08-28

### Added

- Quality-managed landscape exploration: three internal concepts are scored, with only the best qualified result shown by default.
- Six structured title families and a mandatory two-line or arc/double-ribbon layout for `CERTIFICATE OF COMPLETION`.
- Deterministic title planning, rendering, validation, and one targeted title repair.
- Bundled OFL fonts with an immutable font manifest and glyph-aware fallback.
- Character identity evidence reports as a hard gate before visual scoring.
- Stage-scoped active-context packs, dependency-aware source caches, and execution metrics.
- Dual-orientation title derivatives from approved landscape and portrait Masters.
- Non-destructive migration for legacy textbook and bidirectional-template projects.
- A complete public-release validator covering tests, packaging, and isolated installation.

### Changed

- New textbook manifests use version 1.5, template manifests use version 1.3, and generation configs use version 1.4.
- Each orientation permits at most one automatic repair before the workflow pauses.
- Title ribbons, arcs, and illustrated bases are allowed only for the unique main title; variable-information containers remain forbidden.
- The normal workflow asks only for mode, a missing title, and explicit approval of each orientation.
- CI delegates to the complete public-release validator to avoid duplicated validation work.

### Compatibility

- Legacy schema versions remain readable.
- Migration creates an in-project backup before writing and marks Masters without current verification evidence as `legacy_unverified`.

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
