# 风格参数规则

参数用于在清晰风格骨架内产生变化，不能自由混搭成风格拼盘。

## 核心参数

| 参数 | 允许值 |
|---|---|
| `density` | `light`、`medium`、`rich` |
| `symmetry` | `symmetric`、`balanced_asymmetric` |
| `illustration_medium` | `flat`、`hand_drawn`、`watercolor`、`paper_texture`、`line_art` |
| `ceremony_level` | `light`、`standard`、`grand` |
| `textbook_fusion` | `conservative`、`balanced`、`prominent` |
| `character_usage` | `none`、`corner_character`、`edge_scene` |
| `background_material` | `clean_paper`、`textured_paper`、`dark_full_bleed`、`soft_wash`、`geometric_field` |
| `corner_connection` | `tapered_continuous`、`line_bridge`、`environment_bridge` |
| `title_position` | 固定为 `canvas_center` |
| `concept_role` | `cover_character_led`、`balanced_translation`、`frame_led` |
| `frame_structure` | `full_frame`、`corner_connected`、`open_frame`、`illustrated_perimeter` |
| `frame_language` | `classic_double_line`、`european_ornamental`、`modern_geometric`、`botanical_vine`、`storybook_sculpted` |

## 配置原则

- 只使用风格库为当前家族列出的常用子集；偏离时必须说明适配理由。
- `textbook_fusion=conservative` 保留教材色彩和少量线索；`balanced` 同时体现教材与证书家族；`prominent` 强化教材核心元素但仍服从证书结构。
- `balanced_asymmetric` 不等于单侧堆叠。左右视觉重量必须稳定，两个下角都要有可见锚点。
- `rich` 只增加外围信息，不能侵入标题、正文和落款功能区。
- 竖版继承已批准 Profile 的风格家族和核心参数；仅允许为竖向节奏改变元素位置、比例和生长方向。
- 默认三套必须各使用一个不同的 `concept_role`；`frame_led` 固定搭配 `full_frame` 和 `textbook_fusion=conservative`，`character_usage` 可以为 `none`。
- `full_frame` 是沿四边连续的证书结构，不是标题容器；它可在 Z50 侧缘连续，并在 Z80 角部增强，但不得侵入 Z08/Z12 功能区。
- `cover_character_led` 若使用角色，必须加载角色身份档案与原图裁切；不允许以更换插画媒介为由改变身份。

## 风格锁

- LEVEL1：锁定全部核心参数和人物身份，只改用户指定的局部属性。
- LEVEL2：锁定 `style_family`、标题原文和主要视觉语言；允许调整密度、角色使用、连接方式等家族内参数。
- LEVEL3：解除风格家族锁，可重新评分和创建新 Profile；旧 Profile 与图片保留。人物身份锁不解除。
