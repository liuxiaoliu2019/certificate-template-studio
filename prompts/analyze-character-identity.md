# 角色身份分析 Prompt

## 输入

- 教材封面：`{cover_path}`
- Style DNA：`{style_dna}`
- 输出 schema：`schemas/character_identity.schema.json`

## Prompt

分析教材封面中全部可识别的人类与动物角色，为跨插画媒介的证书生成建立身份锁。此阶段不生成图片、不推荐风格、不改造角色。

为每个角色记录稳定 `character_id`、类别、原图归一化矩形区域，以及实际可见的头部/发型、脸部、肤色或毛羽色、身体比例、服装款式与分区配色、标志性配件、动物物种与斑纹。把最决定身份的内容写入 `immutable_traits`。

允许的变化仅包括姿势、动作、视线、方向、在边缘的探入方式和绘制媒介。禁止改变身份、混合角色、无依据补全遮挡部分或把角色替换为通用人物/动物。每个角色的 `reference_crop` 使用 `analysis/character_refs/<character_id>.png`。

`source_region` 使用 0–1 归一化坐标，完整包含角色可见部分并尽量排除教材文字。看不清的特征写入 `unverified_traits`，不得猜测。

只返回符合 schema 的 JSON。若封面没有可识别角色，返回空 `characters`，仍保留全局身份策略。
