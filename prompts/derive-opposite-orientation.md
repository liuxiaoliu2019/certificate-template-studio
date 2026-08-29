# 另一方向衍生 Prompt

## 输入

- Image A：用户源模板 `{source_template}`
- Image B：已批准同方向 Master `{approved_source_master}`
- Image C：目标方向隐藏控制图 `{target_control_path}`
- Template DNA：`{template_dna}`
- 源方向：`{source_orientation}`
- 目标方向：`{target_orientation}`
- 用户标题：`{certificate_title}`
- 标题处理：`{title_treatment}`
- 可选角色身份档案与裁切：`{character_identity_and_refs}`

## Prompt

以 Image A 和 Template DNA 为源设计依据，以 Image B 为已批准系列身份，按 Image C 的隐藏区域秩序重新构图另一方向的证书原始图。横版保持接近 2172:1536，竖版保持接近 1536:2172，并优先使用服务可提供的最高原生分辨率。

保持已批准 Master 的主辅色比例、边框层级、纹样身份、线条粗细关系、角部强化、材质、正式度和非文字装饰身份。为目标方向重新计算四边长度、纹样重复次数与间距、角花尺度、非文字装饰位置和标题/正文/姓名/落款纵横节奏。

禁止旋转、拉伸、横向或纵向压缩、机械裁切、只取中间区域、直接扩边或复制源方向布局。边框必须四边闭合，纹样无明显接缝、压扁或比例突变。

彻底清除源模板中的全部文字。`Template DNA.title_system` 的标题承载物、弧线和材质必须按新方向重新构图：保留结构身份，不复制源文字；`container=source_native` 时重建同身份的无字弧形飘带/底座，不得退化为直排文字或通用横幅。`ai_integrated` 只生成“{certificate_title}”并锁定 x=50%；`vector_flat` 或 `vector_effect` 全图不生成文字，标题由收尾脚本以 `--template-dna` 绘制。目标为竖版时使用 x 24%–76%、y 9%–18%，正式输出上移约 110 px。最终成品禁止其他文字或伪文字。

中央和下部功能区必须可后期排版。模板含角色时继续执行身份锁。Image C 不得出现在成品。只输出一套目标方向成品。
