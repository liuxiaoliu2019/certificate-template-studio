# 构建证书 Style Profile Prompt

## 输入

- Style DNA：`{style_dna}`
- 角色身份档案：`{character_identity}`
- 风格家族：`{style_family}`
- 设计角色：`{concept_role}`
- 兼容性评分：`{compatibility_score}`
- 适配说明：`{adaptation_notes}`
- 输出 schema：`schemas/certificate_style_profile.schema.json`

## Prompt

根据指定风格家族和教材 Style DNA，创建一份可用于横版、修改和竖版继承的 Style Profile。

只从 `references/style-parameter-rules.md` 的有限枚举中取值，并优先使用风格库为当前家族列出的常用参数。若偏离常用子集，必须在 `adaptation_notes` 中说明教材证据和必要性。

`style_strategy` 要明确说明：教材核心元素如何转译、边框或外围如何组织、左右下角如何形成可见锚点、两侧如何以由大到小的元素弱连接、中央和落款功能区如何退让。若使用角色，列出 `used_character_ids`，并锁定对应身份档案与原图裁切。

`concept_role=frame_led` 时固定使用 `frame_structure=full_frame`、`textbook_fusion=conservative`；完整边框沿四边连续，以角部强化，不得退化成零散角花。角色可以为 `none`。其他设计角色按内容选择 `corner_connected`、`open_frame` 或 `illustrated_perimeter`。

`locked_invariants` 至少包括唯一标题、标题水平居中、中央变量安全区、控制图不进入成品、当前风格身份；含角色时另包含人物身份锁。只返回符合 schema 的 JSON。
