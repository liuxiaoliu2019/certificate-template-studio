# 内置标题字体

本目录提供四个可公开再分发的字体角色，并统一采用 SIL Open Font License 1.1：

- `formal_serif`：Noto Serif SC，适合正式、典礼与中文证书标题。
- `modern_sans`：Noto Sans SC，适合现代、学术与中英混排标题。
- `ceremonial_display`：Cinzel，适合英文典礼展示标题；遇到中文自动改用 Noto Serif SC。
- `children_round`：Baloo 2，适合英文儿童圆体标题；遇到中文自动改用 Noto Sans SC。

运行时按“用户项目字体 → 内置角色候选”的顺序选择，并在绘制前检查标题全部字符。用户指定字体缺字时会明确停止，不会静默替换。商业字体只能保留在用户自己的项目中，不得提交到本仓库或公开发行包。

每个字体子目录均保留 Google Fonts 上游的 `OFL.txt` 与 `METADATA.pb`。具体文件版本、来源和 SHA-256 见 `font_manifest.json`。
