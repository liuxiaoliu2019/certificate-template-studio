# LEVEL3 重做 Prompt

## 输入

- 教材封面：`{cover_path}`
- 对应控制图：`{control_path}`
- Style DNA：`{style_dna}`
- 角色身份档案与可用裁切：`{character_identity_and_refs}`
- 唯一标题：`{certificate_title}`
- 被放弃方向：`{rejected_direction}`
- 用户反馈：`{feedback}`
- 新方向策略：`{new_direction}`
- 新 Style Profile：`{new_style_profile}`

## Prompt

解除当前风格锁，放弃当前方案“{rejected_direction}”的构图与装饰组织，使用已重新评分且不低于 70 分的新 Style Profile，从零生成新方向：“{new_direction}”。用户反馈为：{feedback}。

继续保留同一教材的 Style DNA、用户标题与对应控制图。教材封面负责画风、核心元素、色彩和气质；控制图只负责 Z80/Z50/Z20/Z12/Z08 的软性区域秩序，不复制灰阶、纹理、轮廓或形状。

新方向应与被放弃方案在至少三个设计维度上实质不同，同时保持中央正文安全区、右下偏内侧落款功能区和证书感。右下最外沿继续按控制图形成视觉收边；禁止用大块纯空白代替低密度过渡。

LEVEL3 只解除风格家族和构图锁，不解除人物身份锁。若新方向使用教材角色，必须对照完整封面、对应原图裁切与身份档案，保持全部不可改变项；若选择 `frame_led`，必须建立四边连续的 `full_frame`，允许不使用角色。

只生成唯一标题“{certificate_title}”，逐字准确、与画面融合；完整标题外接框中心必须锁定在画布水平中轴 x=50%，竖版标题相对原 V3 基准向上 1.5 cm；禁止其他任何可读或疑似文字，也禁止教材 Logo、标题、出版社与版次信息。
