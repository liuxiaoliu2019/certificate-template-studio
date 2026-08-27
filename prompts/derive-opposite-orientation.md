# 另一方向衍生 Prompt

## 输入

- Image A：用户源模板 `{source_template}`
- Image B：已批准同方向 Master `{approved_source_master}`
- Image C：目标方向隐藏控制图 `{target_control_path}`
- Template DNA：`{template_dna}`
- 源方向：`{source_orientation}`
- 目标方向：`{target_orientation}`
- 用户标题：`{certificate_title}`
- 可选角色身份档案与裁切：`{character_identity_and_refs}`

## Prompt

以 Image A 和 Template DNA 为源设计依据，以 Image B 为已批准系列身份，按 Image C 的隐藏区域秩序重新构图另一方向的 A4 证书模板。目标为横版 3508 × 2480 px或竖版 2480 × 3508 px，呈现 300 DPI 版式感。

保持已批准 Master 的主辅色比例、边框层级、纹样身份、线条粗细关系、角部强化、材质、正式度和非文字装饰身份。为目标方向重新计算四边长度、纹样重复次数与间距、角花尺度、非文字装饰位置和标题/正文/姓名/落款纵横节奏。

禁止旋转、拉伸、横向或纵向压缩、机械裁切、只取中间区域、直接扩边或复制源方向布局。边框必须四边闭合，纹样无明显接缝、压扁或比例突变。

彻底清除源模板中的全部文字。唯一可读文字为“{certificate_title}”，必须逐字准确。目标为横版时，标题外接框中心固定 x=50%，使用横版 V3 标题核心区；目标为竖版时，中心固定 x=50%，并相对原 V3 基准向上 1.5 cm，放在 x 24%–76%、y 9%–18%。禁止其他文字或伪文字。

中央和下部功能区必须可后期排版。模板含角色时继续执行身份锁。Image C 不得出现在成品。只输出一套目标方向成品。
